"""Behavioural checks for manifest package policy and read-only drift reporting.

`manifest/packages.json` is the single source of what installs. A package is
acceptable only when the version APT offers comes from the source that file
declares, so these tests are mostly about refusing versions from the wrong
place.
"""
import copy
import json
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError  # noqa: E402
from workstation.packages import (  # noqa: E402
    allowed_version, applied_groups, approved_registry, archive_suites,
    expectations, repository_sites, verify_named_packages, verify_packages)

ARCHIVE = {'kind': 'archive', 'origin': 'Ubuntu',
           'suites': ['resolute', 'resolute-updates', 'resolute-security'], 'site': None}
REPOSITORY = {'kind': 'repository', 'origin': None, 'suites': [],
              'site': 'download.docker.com'}


def version(**overrides):
    base = {'source_package': 'curl', 'architecture': 'amd64', 'sha256': 'a' * 64,
            'origins': [{'origin': 'Ubuntu', 'trusted': True, 'suite': 'resolute-security',
                         'site': 'archive.ubuntu.com'}]}
    base.update(overrides)
    return base


class ArchivePolicyTests(unittest.TestCase):
    def test_supported_security_update_is_allowed(self):
        self.assertTrue(allowed_version(version(), ARCHIVE))

    def test_missing_version_is_rejected(self):
        self.assertFalse(allowed_version(None, ARCHIVE))

    def test_wrong_architecture_or_missing_digest_is_rejected(self):
        for key, value in [('architecture', 'arm64'), ('sha256', ''), ('origins', [])]:
            with self.subTest(key=key):
                self.assertFalse(allowed_version(version(**{key: value}), ARCHIVE))

    def test_architecture_all_is_allowed(self):
        self.assertTrue(allowed_version(version(architecture='all'), ARCHIVE))

    def test_untrusted_vendor_or_release_is_rejected(self):
        for key, value in [('origin', 'Other'), ('trusted', False), ('suite', 'noble')]:
            with self.subTest(key=key):
                bad = version()
                bad['origins'][0][key] = value
                self.assertFalse(allowed_version(bad, ARCHIVE))

    def test_mixed_origins_cannot_hide_an_undeclared_source(self):
        bad = version()
        bad['origins'].append({'origin': 'Other', 'trusted': True, 'suite': 'resolute',
                               'site': 'example.invalid'})
        self.assertFalse(allowed_version(bad, ARCHIVE))


class RepositoryPolicyTests(unittest.TestCase):
    """A third-party package must come from the host its repository declares."""

    def docker_version(self, **overrides):
        base = version(origins=[{'origin': 'Docker', 'trusted': True, 'suite': 'resolute',
                                 'site': 'download.docker.com'}])
        base.update(overrides)
        return base

    def test_package_from_its_declared_host_is_allowed(self):
        self.assertTrue(allowed_version(self.docker_version(), REPOSITORY))

    def test_package_from_another_host_is_rejected(self):
        bad = self.docker_version()
        bad['origins'][0]['site'] = 'download.example.invalid'
        self.assertFalse(allowed_version(bad, REPOSITORY))

    def test_untrusted_repository_is_rejected(self):
        bad = self.docker_version()
        bad['origins'][0]['trusted'] = False
        self.assertFalse(allowed_version(bad, REPOSITORY))

    def test_an_archive_version_cannot_satisfy_a_repository_declaration(self):
        """The same package name exists in more than one configured source; the
        declared one is the only acceptable answer."""
        self.assertFalse(allowed_version(version(), REPOSITORY))

    def test_a_repository_version_cannot_satisfy_an_archive_declaration(self):
        self.assertFalse(allowed_version(self.docker_version(), ARCHIVE))


class ManifestExpectationTests(unittest.TestCase):
    def test_archive_packages_expect_ubuntu_in_a_release_pocket(self):
        record = expectations(ROOT)['bat']
        self.assertEqual(record['kind'], 'archive')
        self.assertEqual(record['origin'], 'Ubuntu')
        self.assertIn('resolute', record['suites'])

    def test_third_party_packages_expect_their_repository_host(self):
        record = expectations(ROOT)['docker-ce']
        self.assertEqual(record['kind'], 'repository')
        self.assertEqual(record['site'], 'download.docker.com')

    def test_group_selection_narrows_the_expectation_set(self):
        core = expectations(ROOT, groups=['core'])
        self.assertIn('bat', core)
        self.assertNotIn('docker-ce', core)

    def test_every_repository_resolves_to_a_host(self):
        for name, site in repository_sites(ROOT).items():
            self.assertTrue(site and '/' not in site, f'{name} has no usable host')

    def test_release_pockets_are_derived_not_hardcoded(self):
        suites = archive_suites()
        self.assertTrue(all(s.startswith(suites[0]) for s in suites[1:]))


class VerificationTests(unittest.TestCase):
    def test_a_package_not_from_its_declared_source_is_failed_without_repair(self):
        observations = [{'id': 'bat', 'installed_allowed': False}]
        with patch('workstation.packages.expectations',
                   return_value={'bat': {'id': 'bat', 'package': 'bat', 'source': 'archive'}}), \
             patch('workstation.packages.inspect_packages', return_value=observations) as probe:
            checks = verify_packages(ROOT)
        probe.assert_called_once()
        self.assertEqual(checks[0]['id'], 'package:bat')
        self.assertEqual(checks[0]['status'], 'failed')
        self.assertIn('archive', checks[0]['reason'])
        self.assertEqual(checks[-1]['status'], 'failed')

    def test_all_installed_reports_one_summary(self):
        observations = [{'id': 'bat', 'installed_allowed': True}]
        with patch('workstation.packages.expectations',
                   return_value={'bat': {'id': 'bat', 'package': 'bat', 'source': 'archive'}}), \
             patch('workstation.packages.inspect_packages', return_value=observations):
            checks = verify_packages(ROOT)
        self.assertEqual(len(checks), 1)
        self.assertEqual(checks[0]['status'], 'passed')
        self.assertIn('1-of-1', checks[0]['reason'])

    def test_an_empty_selection_never_probes(self):
        with patch('workstation.packages.expectations', return_value={}), \
             patch('workstation.packages.inspect_packages') as probe:
            self.assertEqual(verify_packages(ROOT), [])
        probe.assert_not_called()


class ApprovalRegistryTests(unittest.TestCase):
    """Retained as licence and copyright provenance; not an installation input."""

    def setUp(self):
        self.entries = {e['id']: e for e in
                        json.loads((ROOT / 'catalogue/capabilities.json').read_text())['capabilities']}

    def test_catalogue_approvals_match_the_registry(self):
        self.assertEqual(set(approved_registry(self.entries)),
                         {'curl', 'git', 'git-lfs', 'jq', 'ripgrep', 'shellcheck', 'zsh',
                          'zsh-autosuggestions', 'zsh-syntax-highlighting'})

    def test_unreviewed_delivery_or_licence_is_rejected(self):
        for field, value, message in [
                (('delivery', 'status'), 'unverified', 'delivery-approval-mismatch'),
                (('licence', 'status'), 'unverified', 'package-licence-mismatch'),
                (('delivery', 'identifier'), 'other', 'package-identifier-mismatch')]:
            with self.subTest(field=field):
                entries = copy.deepcopy(self.entries)
                entries['git'][field[0]][field[1]] = value
                with self.assertRaisesRegex(InputError, message):
                    approved_registry(entries)

    def test_wrong_owner_is_rejected(self):
        self.entries['git']['owner'] = 'chezmoi'
        with self.assertRaisesRegex(InputError, 'wrong-package-owner'):
            approved_registry(self.entries)


class InstalledStateTests(unittest.TestCase):
    """dpkg status alone must not be taken as evidence a package is usable."""

    def test_half_configured_package_cannot_pass_from_version_metadata(self):
        import contextlib
        import io
        import runpy
        import subprocess
        import types

        record = {'id': 'curl', 'package': 'curl', 'source': 'archive', **ARCHIVE}
        apt_version = types.SimpleNamespace(
            source_name='curl', architecture='amd64', record={'SHA256': 'a' * 64},
            version='1.0',
            origins=[types.SimpleNamespace(origin='Ubuntu', archive='resolute',
                                           site='archive.ubuntu.com', trusted=True)])
        package = types.SimpleNamespace(candidate=apt_version, installed=apt_version,
                                        versions=[apt_version])
        adapter = runpy.run_path(str(ROOT / 'script/workstation/apt_probe.py'))
        for state, expected in [('installed', True), ('half-configured', False),
                                ('unpacked', False)]:
            with self.subTest(state=state):
                output = io.StringIO()
                dpkg = subprocess.CompletedProcess([], 0, f'curl\t{state}\t1.0\n')
                with patch.dict(sys.modules, {'apt': types.SimpleNamespace(
                            Cache=lambda **kwargs: {'curl': package})}), \
                        patch('sys.stdin', io.StringIO(json.dumps([record]))), \
                        patch('subprocess.run', return_value=dpkg), \
                        contextlib.redirect_stdout(output):
                    adapter['main']()
                self.assertEqual(json.loads(output.getvalue())[0]['installed_allowed'], expected)


class DeclaredSourceWinsTests(unittest.TestCase):
    """APT's own candidate is the highest version across every configured
    repository, which is not necessarily the declared one.

    google-cloud-cli ships a kubectl with epoch 1: that outranks the upstream
    Kubernetes build, so adding that repository silently takes kubectl over.
    The declared source has to decide the version, or declaring it means
    nothing.
    """

    def apt_probe(self):
        import runpy
        return runpy.run_path(str(ROOT / 'script/workstation/apt_probe.py'))

    def run_probe(self, record, versions, installed=None, state='installed'):
        import contextlib
        import io
        import runpy
        import subprocess
        import types

        def make(version, site, origin, archive):
            return types.SimpleNamespace(
                source_name=record['package'], architecture='amd64',
                record={'SHA256': 'a' * 64}, version=version,
                origins=[types.SimpleNamespace(origin=origin, archive=archive,
                                               site=site, trusted=True)])

        built = [make(*v) for v in versions]
        chosen = next((v for v in built if v.version == installed), None)
        package = types.SimpleNamespace(candidate=built[0], installed=chosen, versions=built)
        adapter = self.apt_probe()
        output = io.StringIO()
        line = f"{record['package']}\t{state}\t{installed}\n" if installed else ''
        dpkg = subprocess.CompletedProcess([], 0 if installed else 1, line)
        with patch.dict(sys.modules, {
                    'apt': types.SimpleNamespace(Cache=lambda **kw: {record['package']: package}),
                }), \
                patch('sys.stdin', io.StringIO(json.dumps([record]))), \
                patch('subprocess.run', return_value=dpkg), \
                contextlib.redirect_stdout(output):
            adapter['main']()
        return json.loads(output.getvalue())[0]

    def test_a_higher_version_from_another_repository_does_not_win(self):
        record = {'id': 'kubectl', 'package': 'kubectl', 'source': 'kubernetes',
                  'kind': 'repository', 'origin': None, 'suites': [], 'site': 'pkgs.k8s.io'}
        observation = self.run_probe(record, [
            ('1:585.0.0-0', 'packages.cloud.google.com', 'cloud-sdk', 'cloud-sdk'),
            ('1.34.11-1.1', 'pkgs.k8s.io', 'obs://', 'stable'),
        ])
        self.assertTrue(observation['install_allowed'])
        self.assertEqual(observation['candidate'], '1.34.11-1.1',
                         'the declared repository must decide the version')
        self.assertEqual(observation['install_spec'], 'kubectl=1.34.11-1.1')
        self.assertEqual(observation['apt_candidate'], '1:585.0.0-0',
                         "APT's own pick is reported, for diagnosis")

    def test_the_newest_version_from_the_declared_source_is_chosen(self):
        record = {'id': 'bat', 'package': 'bat', 'source': 'archive',
                  'kind': 'archive', 'origin': 'Ubuntu',
                  'suites': ['resolute', 'resolute-updates'], 'site': None}
        observation = self.run_probe(record, [
            ('0.25.0-5ubuntu1', 'archive.ubuntu.com', 'Ubuntu', 'resolute'),
            ('0.26.0-1ubuntu1', 'archive.ubuntu.com', 'Ubuntu', 'resolute-updates'),
        ])
        self.assertEqual(observation['candidate'], '0.26.0-1ubuntu1')

    def test_no_version_from_the_declared_source_is_refused(self):
        record = {'id': 'kubectl', 'package': 'kubectl', 'source': 'kubernetes',
                  'kind': 'repository', 'origin': None, 'suites': [], 'site': 'pkgs.k8s.io'}
        observation = self.run_probe(record, [
            ('1:585.0.0-0', 'packages.cloud.google.com', 'cloud-sdk', 'cloud-sdk'),
        ])
        self.assertFalse(observation['install_allowed'])
        self.assertIsNone(observation['install_spec'])

    def test_a_version_installed_from_the_wrong_source_is_not_accepted(self):
        record = {'id': 'kubectl', 'package': 'kubectl', 'source': 'kubernetes',
                  'kind': 'repository', 'origin': None, 'suites': [], 'site': 'pkgs.k8s.io'}
        observation = self.run_probe(record, [
            ('1:585.0.0-0', 'packages.cloud.google.com', 'cloud-sdk', 'cloud-sdk'),
            ('1.34.11-1.1', 'pkgs.k8s.io', 'obs://', 'stable'),
        ], installed='1:585.0.0-0')
        self.assertFalse(observation['installed_allowed'],
                         'an installed package from an undeclared source must not verify')


class PrerequisiteCheckTests(unittest.TestCase):
    """Runtimes ask whether a system dependency is present.

    These call into the package layer from another module, so a signature
    change there breaks them silently unless something exercises the call.
    """

    def test_named_packages_are_checked_against_the_archive(self):
        with patch('workstation.packages.inspect_packages',
                   return_value=[{'id': 'g++', 'installed_allowed': True}]) as probe:
            checks = verify_named_packages(['g++'])
        records = probe.call_args[0][0]
        self.assertEqual(records[0]['package'], 'g++')
        self.assertEqual(records[0]['kind'], 'archive')
        self.assertEqual(checks[0]['status'], 'passed')

    def test_a_missing_prerequisite_is_failed(self):
        with patch('workstation.packages.inspect_packages',
                   return_value=[{'id': 'g++', 'installed_allowed': False}]):
            self.assertEqual(verify_named_packages(['g++'])[0]['status'], 'failed')

    def test_no_names_never_probes(self):
        with patch('workstation.packages.inspect_packages') as probe:
            self.assertEqual(verify_named_packages([]), [])
        probe.assert_not_called()

    def test_runtimes_pass_package_names_not_records(self):
        """The call site must hand over strings; passing prerequisite records
        made the package layer treat a list as a filesystem path."""
        from workstation import mandrel_runtime, rust_runtime
        for module in (mandrel_runtime, rust_runtime):
            source = Path(module.__file__).read_text()
            self.assertIn("r['package'] for r in prerequisites()", source,
                          f'{module.__name__} must pass package names')
            self.assertNotIn('verify_packages(prerequisites()', source)


class AppliedGroupTests(unittest.TestCase):
    """Verification describes the machine that exists, not the one the manifest
    could describe: a machine installed without the gpu group has not failed to
    install it."""

    def setUp(self):
        import tempfile
        import shutil
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / '.workstation').mkdir()

    def write(self, payload):
        (self.root / '.workstation/applied-groups.json').write_text(json.dumps(payload))

    def test_recorded_groups_are_returned(self):
        self.write({'schema_version': 1, 'groups': ['core', 'dev']})
        self.assertEqual(applied_groups(self.root), ['core', 'dev'])

    def test_nothing_recorded_means_no_narrowing(self):
        self.assertIsNone(applied_groups(self.root))

    def test_an_unreadable_record_does_not_raise(self):
        (self.root / '.workstation/applied-groups.json').write_text('not json')
        self.assertIsNone(applied_groups(self.root))

    def test_an_empty_group_list_means_no_narrowing(self):
        self.write({'schema_version': 1, 'groups': []})
        self.assertIsNone(applied_groups(self.root))

    def test_an_excluded_group_is_not_verified(self):
        core_only = expectations(ROOT, groups=['core'])
        self.assertNotIn('nvidia-driver-595-open', core_only,
                         'a group that was never applied must not be checked')


if __name__ == '__main__':
    unittest.main()
