"""Host profiles: which parts of the host a run installs, and what verify demands.

A profile is a name the operator chooses (`--profiles desktop,gpu`); the
catalogue in profiles/host.json maps it to manifest groups and, for `firewall`,
to a stage. A headless selection (none of the desktop set) must run no desktop
playbook, snap, GNOME setting or VS Code step, and verify must not demand them.
"""
import contextlib
import getpass
import io
import json
import os
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation import profiles  # noqa: E402
from workstation.config import InputError  # noqa: E402
from workstation.cli import main  # noqa: E402

NAMES = ['desktop', 'media', 'productivity', 'ai', 'network', 'lab', 'gpu', 'dev-gui',
         'firewall']
DEFAULT = ['desktop', 'media', 'productivity', 'ai', 'network', 'dev-gui', 'firewall']
DESKTOP_PLAYBOOKS = ('desktop.yml', 'snaps.yml', 'plugins.yml')


def manifest(name):
    return json.loads((ROOT / 'manifest' / f'{name}.json').read_text())


class TempState(unittest.TestCase):
    """A per-user state directory of its own, so results never depend on what
    the developer's own account has recorded."""

    def setUp(self):
        import os
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        environment = patch.dict(os.environ, {'XDG_STATE_HOME': str(self.temp)})
        environment.start()
        self.addCleanup(environment.stop)
        self.catalogue = profiles.load()

    def record(self, payload):
        from workstation import state
        if not state.path().exists():
            state.set('profiles', ['lab'])  # creates the directory with safe modes
        state.path().write_text(payload if isinstance(payload, str) else json.dumps(payload))


class CatalogueTest(unittest.TestCase):
    def setUp(self):
        self.catalogue = profiles.load()

    def test_the_profile_names_are_exact(self):
        self.assertEqual(profiles.available(self.catalogue), NAMES)

    def test_the_default_is_exact(self):
        self.assertEqual(self.catalogue['default'], DEFAULT)

    def test_firewall_installs_no_manifest_group_and_names_its_stage(self):
        self.assertEqual(self.catalogue['profiles']['firewall'], [])
        self.assertEqual(self.catalogue['stages'], {'firewall': ['firewall']})

    def test_every_manifest_group_has_exactly_one_owner(self):
        owners = list(self.catalogue['base_groups'])
        for groups in self.catalogue['profiles'].values():
            owners.extend(groups)
        self.assertEqual(sorted(owners), sorted(manifest('packages')['groups']))

    def test_the_desktop_set_excludes_the_headless_profiles(self):
        desktop_set = set(self.catalogue['desktop_set'])
        self.assertEqual(desktop_set & {'lab', 'gpu', 'firewall'}, set())
        self.assertLessEqual({'desktop', 'dev-gui'}, desktop_set)

    def test_every_snap_belongs_to_the_desktop_set(self):
        """Snaps install only when the desktop set is selected."""
        desktop_groups = {g for p in self.catalogue['desktop_set']
                          for g in self.catalogue['profiles'][p]}
        for snap in manifest('snaps')['snaps']:
            self.assertIn(snap['group'], desktop_groups, snap['name'])

    def test_ppa_management_is_host_base_not_desktop(self):
        """RB10: software-properties-common is always installed, headless too."""
        groups = manifest('packages')['groups']
        self.assertEqual(self.catalogue['base_groups'], ['base'])
        self.assertIn('software-properties-common', {e['name'] for e in groups['base']})
        self.assertNotIn('software-properties-common',
                         {e['name'] for e in groups['desktop']})

    def test_a_duplicate_key_is_rejected(self):
        temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, temp, ignore_errors=True)
        (temp / 'profiles').mkdir()
        (temp / 'manifest').mkdir()
        shutil.copy(ROOT / 'profiles/host.schema.json', temp / 'profiles')
        for name in ('packages', 'snaps'):
            shutil.copy(ROOT / f'manifest/{name}.json', temp / 'manifest')
        text = (ROOT / 'profiles/host.json').read_text()
        (temp / 'profiles/host.json').write_text(
            text.replace('"schema_version": 1,', '"schema_version": 1, "schema_version": 1,', 1))
        with self.assertRaisesRegex(InputError, 'duplicate-json-key'):
            profiles.load(temp)


class ParseTest(unittest.TestCase):
    def setUp(self):
        self.catalogue = profiles.load()

    def test_an_unknown_name_is_rejected_listing_the_valid_ones(self):
        with self.assertRaises(InputError) as caught:
            profiles.parse('desktop,PRIVATE_TYPO', self.catalogue)
        message = str(caught.exception)
        self.assertIn('unknown-profile', message)
        self.assertIn(','.join(NAMES), message)
        # Error codes never echo operator input.
        self.assertNotIn('PRIVATE_TYPO', message)

    def test_an_empty_selection_is_rejected(self):
        for text in ('', ',', ' '):
            with self.assertRaisesRegex(InputError, 'no-profile-selected'):
                profiles.parse(text, self.catalogue)

    def test_a_repeated_name_is_rejected(self):
        with self.assertRaisesRegex(InputError, 'duplicate-profile'):
            profiles.parse('gpu,gpu', self.catalogue)

    def test_names_come_back_in_catalogue_order(self):
        self.assertEqual(profiles.parse('firewall, gpu', self.catalogue), ['gpu', 'firewall'])


class SelectTest(TempState):
    def test_with_nothing_given_or_recorded_the_default_is_selected(self):
        self.assertEqual(profiles.select(None, self.catalogue), (DEFAULT, 'default'))

    def test_an_explicit_list_wins(self):
        self.record({'schema_version': 1, 'profiles': ['gpu']})
        self.assertEqual(profiles.select('lab', self.catalogue), (['lab'], 'explicit'))

    def test_the_recorded_choice_holds_when_nothing_is_given(self):
        """A headless machine re-run without --profiles must stay headless."""
        self.record({'schema_version': 1, 'profiles': ['gpu', 'firewall']})
        self.assertEqual(profiles.select(None, self.catalogue),
                         (['gpu', 'firewall'], 'recorded'))

    def test_an_unreadable_record_fails_closed(self):
        for payload in ('not json', {'schema_version': 1, 'profiles': ['nope']},
                        {'schema_version': 1, 'profiles': []},
                        {'schema_version': 1, 'profiles': 'gpu'}):
            self.record(payload)
            with self.assertRaisesRegex(InputError, 'recorded-profiles-unreadable'):
                profiles.select(None, self.catalogue)

    def test_an_unsafe_record_fails_closed(self):
        from workstation import state
        self.record({'schema_version': 1, 'profiles': ['gpu']})
        state.path().chmod(0o644)
        with self.assertRaisesRegex(InputError, 'recorded-profiles-unreadable'):
            profiles.select(None, self.catalogue)

    def test_the_record_survives_losing_the_clone_state(self):
        """Deleting .workstation (rebuilding the controller) keeps the choice."""
        from workstation import controller, state
        controller.record_selection(profiles.resolve(['gpu', 'firewall'], self.catalogue))
        self.assertFalse(state.path().is_relative_to(ROOT))
        self.assertEqual(profiles.select(None, self.catalogue), (['gpu', 'firewall'], 'recorded'))

    def test_recording_keeps_other_state(self):
        from workstation import controller, state
        state.set('other', 1)
        controller.record_selection(profiles.resolve(['lab'], self.catalogue))
        self.assertEqual(state.get('other'), 1)
        self.assertEqual(state.get('profiles'), ['lab'])


class NoCloneRecordTest(unittest.TestCase):
    def test_nothing_records_the_choice_inside_the_clone(self):
        for source in ('controller.py', 'profiles.py', 'cli.py'):
            text = (ROOT / 'script/workstation' / source).read_text()
            self.assertNotIn("'profiles.json'", text, source)
            self.assertNotIn('.workstation/profiles', text, source)


class ResolveTest(unittest.TestCase):
    def setUp(self):
        self.catalogue = profiles.load()

    def test_headless_selection(self):
        selection = profiles.resolve(['gpu', 'firewall'], self.catalogue)
        self.assertEqual(selection['groups'], ['base', 'gpu'])
        self.assertEqual(selection['repositories'], [])
        self.assertEqual(selection['stages'], ['firewall'])
        self.assertTrue(selection['headless'])

    def test_default_selection(self):
        selection = profiles.resolve(DEFAULT, self.catalogue)
        self.assertEqual(selection['groups'],
                         ['base', 'desktop', 'media', 'productivity', 'ai', 'network', 'dev-gui'])
        self.assertEqual(sorted(selection['repositories']),
                         sorted(['vscode', 'google-chrome', 'slack', 'dbeaver', 'claude-desktop',
                                 'chatgpt', 'ppa-obs']))
        self.assertFalse(selection['headless'])

    def test_lab_configures_only_its_own_repository(self):
        self.assertEqual(profiles.resolve(['lab'], self.catalogue)['repositories'],
                         ['ppa-quickemu'])


class ScopeTest(unittest.TestCase):
    """D035: the report covers the workstation, not this repository's tooling."""

    def setUp(self):
        self.catalogue = profiles.load()
        self.selection = profiles.resolve(list(self.catalogue['default']), self.catalogue)

    def test_controller_and_test_vm_tooling_belong_to_no_selection(self):
        for boundary in ('controller', 'test-vm'):
            entry = {'boundary': boundary, 'profile': 'foundation'}
            self.assertFalse(profiles.in_scope('pytest', entry, self.selection, self.catalogue),
                             boundary)

    def test_a_workstation_role_is_still_in_scope(self):
        entry = {'boundary': 'host', 'profile': 'operations'}
        self.assertTrue(profiles.in_scope('host-security', entry, self.selection, self.catalogue))


class ProfilesLineTest(unittest.TestCase):
    def setUp(self):
        self.catalogue = profiles.load()

    def test_the_default_line_is_exact(self):
        self.assertEqual(
            profiles.line(DEFAULT, self.catalogue),
            'Profiles: desktop,media,productivity,ai,network,dev-gui,firewall '
            '(default desktop,media,productivity,ai,network,dev-gui,firewall; '
            'available desktop,media,productivity,ai,network,lab,gpu,dev-gui,firewall; '
            'change with ./bootstrap apply --config <file> --profiles <list>)')

    def test_a_headless_line_is_exact(self):
        self.assertEqual(
            profiles.line(['gpu', 'firewall'], self.catalogue),
            'Profiles: gpu,firewall '
            '(default desktop,media,productivity,ai,network,dev-gui,firewall; '
            'available desktop,media,productivity,ai,network,lab,gpu,dev-gui,firewall; '
            'change with ./bootstrap apply --config <file> --profiles <list>)')


class StagesTest(unittest.TestCase):
    def setUp(self):
        from workstation.controller import host_stages
        self.host_stages = host_stages
        self.catalogue = profiles.load()

    def playbooks(self, names):
        stages = self.host_stages(profiles.resolve(names, self.catalogue))
        return [p for _, books, _ in stages for p in books], [s for s, _, _ in stages]

    def test_headless_runs_no_desktop_snap_or_vscode_playbook(self):
        books, stages = self.playbooks(['gpu', 'firewall'])
        for name in DESKTOP_PLAYBOOKS + ('binaries.yml',):
            self.assertNotIn(name, books)
        self.assertIn('manifest-packages.yml', books)
        self.assertEqual(stages[-1], 'firewall')

    def test_the_default_runs_every_host_stage(self):
        books, stages = self.playbooks(DEFAULT)
        for name in ('foundation.yml', 'repositories.yml', 'manifest-packages.yml',
                     'snaps.yml', 'binaries.yml', 'system-groups.yml', 'plugins.yml',
                     'desktop.yml'):
            self.assertIn(name, books)
        self.assertIn('firewall', stages)

    def test_firewall_runs_only_when_selected(self):
        _, stages = self.playbooks(['desktop'])
        self.assertNotIn('firewall', stages)

    def test_the_controller_runs_the_stage_list_and_calls_the_firewall_hook(self):
        from workstation import controller
        ran = []
        selection = profiles.resolve(['gpu', 'firewall'], self.catalogue)
        with patch.object(controller, 'apply_firewall_stage') as hook:
            controller.run_host_stages(selection, lambda books, timeout: ran.extend(books),
                                       record=lambda: ran.append('<record>'), config={})
        hook.assert_called_once()
        for name in DESKTOP_PLAYBOOKS:
            self.assertNotIn(name, ran)
        self.assertIn('<record>', ran)
        self.assertLess(ran.index('<record>'), ran.index('repositories.yml'),
                        'the choice is recorded before anything is installed')


class PlaybookFilterTest(unittest.TestCase):
    """The playbooks install only what the selected groups declare."""

    def read(self, name):
        return (ROOT / 'ansible' / name).read_text()

    def test_snaps_are_filtered_by_group(self):
        self.assertIn("selectattr('group', 'in', manifest_groups)", self.read('snaps.yml'))

    def test_our_source_is_removed_only_when_the_vendor_wrote_its_own(self):
        # claude-desktop's postinst steps aside while ours exists and Chrome's
        # registers only once per machine; removing ours unconditionally left
        # each with no source at all.
        text = (ROOT / 'ansible' / 'tasks' / 'install-vendor-package.yml').read_text()
        install = text.index('packages"')
        look = text.index('Look for a source')
        hand_back = text.index('back to the vendor package')
        refresh = text.index('Refresh metadata after')
        self.assertLess(install, look)
        self.assertLess(look, hand_back)
        self.assertLess(hand_back, refresh)
        task = text[hand_back:refresh]
        self.assertIn('when: >-', task)
        self.assertIn("reject('search', '/workstation-' ~ vendor.id", task)
        self.assertNotIn('dpkg-reconfigure', text)

    def test_preinstalled_snaps_are_switched_to_the_declared_channel(self):
        # Ubuntu seeds firefox and thunderbird on a release branch; `snap install`
        # leaves them there, so verify reported them tracking the wrong channel.
        text = self.read('snaps.yml')
        switch = text[text.index('Move a preinstalled snap'):]
        self.assertIn('/usr/bin/snap, switch, --channel', switch)
        self.assertIn('snap_list.stdout is not search', switch)
        self.assertIn("selectattr('group', 'in', manifest_groups)", switch)

    def test_binaries_are_filtered_by_group(self):
        text = self.read('binaries.yml')
        install = text[text.index('Install each pinned artifact'):]
        self.assertIn("selectattr('group', 'in', manifest_groups)", install)

    def test_sources_name_only_the_native_architecture(self):
        # Ubuntu Desktop enables i386; without Architectures every apt update
        # printed a notice for each repository that does not publish it.
        text = self.read('repositories.yml')
        self.assertIn('argv: [/usr/bin/dpkg, --print-architecture]', text)
        declare = text[text.index('Declare each third-party source'):]
        self.assertIn('architectures: ["{{ dpkg_architecture.stdout }}"]', declare)

    def test_only_selected_repositories_are_configured(self):
        text = self.read('repositories.yml')
        self.assertIn("selectattr('id', 'in', selected_repositories)", text)
        self.assertNotIn('loop: "{{ manifest.repositories }}"', text)

    def test_only_selected_vendor_repositories_are_handed_back(self):
        text = self.read('manifest-packages.yml')
        vendor = text[text.index('Install each vendor-managed'):]
        self.assertIn("selectattr('id', 'in', selected_repositories)", vendor)


class RepositoryVerifyTest(unittest.TestCase):
    def test_verify_checks_only_selected_repositories(self):
        from workstation import delivery
        with patch.object(delivery, 'key_fingerprint', return_value=None):
            checks = delivery.verify_repositories(ROOT, repositories=['ppa-quickemu'])
        ids = {c['id'] for c in checks}
        self.assertEqual(ids, {'repository:ppa-quickemu', 'manifest-repositories'})

    def test_no_selected_repository_means_no_check(self):
        from workstation import delivery
        self.assertEqual(delivery.verify_repositories(ROOT, repositories=[]), [])


class PrerequisiteTest(unittest.TestCase):
    """RB10: gpg verifies repository keys; git clones setup-dev-linux-wsl."""

    def test_both_present_passes(self):
        from workstation.host import check_prerequisites
        checks, code = check_prerequisites(which=lambda name, path=None: '/usr/bin/' + name)
        self.assertEqual(code, 0)
        self.assertEqual([c['status'] for c in checks], ['passed'])

    def test_each_missing_tool_is_named_with_its_package(self):
        from workstation.host import check_prerequisites
        checks, code = check_prerequisites(which=lambda name, path=None: None)
        self.assertEqual(code, 1)
        reasons = {c['id']: c['reason'] for c in checks}
        self.assertEqual(reasons['prerequisite:gpg'], 'missing-install-package-gnupg')
        self.assertEqual(reasons['prerequisite:git'], 'missing-install-package-git')


def context(selected=(), entries=None):
    return {'config': {'example_only': False, 'target': {'user': getpass.getuser()}},
            'provenance': {}, 'selected': list(selected), 'entries': entries or {},
            'approved': {}}


class CliTest(unittest.TestCase):
    def run_cli(self, args, ctx=None, recorded=None):
        """Run the CLI with every machine-touching step stubbed; self.mocks
        names each stub by its target."""
        stdout, stderr = io.StringIO(), io.StringIO()
        targets = {
            'workstation.cli.load_context': ctx or context(),
            'workstation.profiles.recorded': recorded,
            'workstation.storage.preflight': ([], 0),
            'workstation.host.check_prerequisites': ([], 0),
            'workstation.packages.verify_packages': [],
            'workstation.system.verify': [],
            'workstation.delivery.verify': [],
            'workstation.desktop.verify': [],
            'workstation.firewall.verify': [],
            'workstation.firewall.recorded_allow_ssh': None,
            'workstation.plugins.verify': [],
            'workstation.controller.apply_foundation': {
                'id': 'controller-foundation', 'status': 'passed', 'reason': 'fixture'},
            # The handoff has its own tests (tests/test_handoff.py).
            'workstation.handoff.run_handoff': 0,
            'workstation.handoff.verify_cli': [],
            'workstation.handoff.first_run_hint': None,
        }
        with contextlib.ExitStack() as stack:
            self.mocks = {target: stack.enter_context(patch(target, return_value=value))
                          for target, value in targets.items()}
            stack.enter_context(patch('os.geteuid', return_value=1000))
            stack.enter_context(patch.dict(os.environ))
            os.environ.pop('SSH_CONNECTION', None)  # apply would refuse over SSH (RB18)
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def test_install_is_an_alias_of_apply(self):
        code, out, err = self.run_cli(['install', '--config', 'x.json', '--format', 'json'])
        self.assertIn('install is now apply', err)
        report = json.loads(out)
        self.assertEqual(report['command'], 'apply')
        self.mocks['workstation.controller.apply_foundation'].assert_called_once()
        selection = self.mocks['workstation.controller.apply_foundation'].call_args.kwargs['selection']
        self.assertEqual(selection['profiles'], DEFAULT)

    def test_manifest_groups_is_an_alias_of_profiles(self):
        _, _, err = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                  '--manifest-groups', 'gpu'])
        self.assertIn('--manifest-groups is now --profiles', err)
        selection = self.mocks['workstation.controller.apply_foundation'].call_args.kwargs['selection']
        self.assertEqual(selection['profiles'], ['gpu'])

    def test_both_profile_options_together_are_invalid(self):
        code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                     '--profiles', 'gpu', '--manifest-groups', 'lab'])
        self.assertEqual(code, 2)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_an_unknown_profile_is_invalid_and_lists_the_valid_ones(self):
        code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                     '--profiles', 'gpu,desktp'])
        self.assertEqual(code, 2)
        self.assertIn(','.join(NAMES), out)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_the_profiles_line_is_the_first_line_of_text_output(self):
        for command in ('plan', 'apply', 'verify'):
            _, out, _ = self.run_cli([command, '--config', 'x.json', '--profiles', 'gpu,firewall'])
            self.assertEqual(out.splitlines()[0], profiles.line(['gpu', 'firewall'],
                                                                profiles.load()), command)
            self.assertEqual(out.splitlines()[1], 'Profiles source: explicit', command)

    def test_text_output_says_where_the_selection_came_from(self):
        _, out, _ = self.run_cli(['verify', '--config', 'x.json'])
        self.assertEqual(out.splitlines()[1], 'Profiles source: default')
        _, out, _ = self.run_cli(['verify', '--config', 'x.json'], recorded=['gpu'])
        self.assertEqual(out.splitlines()[1], 'Profiles source: recorded')

    def test_json_output_carries_the_profiles_and_stays_one_document(self):
        _, out, _ = self.run_cli(['plan', '--config', 'x.json', '--format', 'json'])
        report = json.loads(out)
        self.assertEqual(report['profiles']['selected'], DEFAULT)
        self.assertEqual(report['profiles']['source'], 'default')
        self.assertTrue(report['profiles']['line'].startswith('Profiles: '))

    def test_headless_verify_demands_no_desktop_snap_gnome_or_vscode(self):
        entries = {
            'baobab': {'profile': 'desktop', 'delivery': {'status': 'unverified'}},
            'extension-ms-python.python': {'profile': 'editor',
                                           'delivery': {'status': 'unverified'}},
            'gnome-settings': {'profile': 'operations', 'delivery': {'status': 'verified'}},
            'ansible-core': {'profile': 'foundation', 'delivery': {'status': 'unverified'}},
        }
        code, out, _ = self.run_cli(['verify', '--config', 'x.json', '--format', 'json',
                                     '--profiles', 'firewall,gpu'],
                                    ctx=context(entries, entries))
        report = json.loads(out)
        ids = {c['id'] for c in report['checks']}
        self.assertNotIn('baobab', ids)
        self.assertNotIn('extension-ms-python.python', ids)
        self.assertNotIn('gnome-settings', ids)
        self.assertIn('ansible-core', ids, 'host-layer gaps are still reported')
        self.assertIn('firewall:ssh-choice', ids)

    def test_headless_verify_calls_no_desktop_or_vscode_verifier(self):
        self.run_cli(['verify', '--config', 'x.json', '--format', 'json',
                      '--profiles', 'firewall,gpu'])
        self.mocks['workstation.desktop.verify'].assert_not_called()
        self.mocks['workstation.plugins.verify'].assert_not_called()
        packages = self.mocks['workstation.packages.verify_packages']
        self.assertEqual(packages.call_args.kwargs['groups'], ['base', 'gpu'])
        delivery = self.mocks['workstation.delivery.verify']
        self.assertEqual(delivery.call_args.kwargs['groups'], ['base', 'gpu'])
        self.assertEqual(delivery.call_args.kwargs['repositories'], [])

    def test_default_verify_checks_the_desktop_and_vscode(self):
        self.run_cli(['verify', '--config', 'x.json', '--format', 'json'])
        self.mocks['workstation.desktop.verify'].assert_called_once()
        self.mocks['workstation.plugins.verify'].assert_called_once()

    def test_verify_uses_the_recorded_selection(self):
        _, out, _ = self.run_cli(['verify', '--config', 'x.json', '--format', 'json'],
                                 recorded=['lab'])
        report = json.loads(out)
        self.assertEqual(report['profiles']['selected'], ['lab'])
        self.assertEqual(report['profiles']['source'], 'recorded')

    def test_a_missing_prerequisite_stops_apply(self):
        stdout = io.StringIO()
        missing = ([{'id': 'prerequisite:git', 'status': 'failed',
                     'reason': 'missing-install-package-git'}], 1)
        with patch('workstation.cli.load_context', return_value=context()), \
             patch('workstation.profiles.recorded', return_value=None), \
             patch('os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.host.check_prerequisites', return_value=missing), \
             patch('workstation.controller.apply_foundation') as apply, \
             contextlib.redirect_stdout(stdout):
            code = main(['apply', '--config', 'x.json', '--format', 'json'])
        self.assertEqual(code, 1)
        apply.assert_not_called()
        self.assertIn('missing-install-package-git', stdout.getvalue())

    def test_preflight_runs_the_prerequisite_check(self):
        self.run_cli(['preflight', '--config', 'x.json', '--format', 'json'])
        self.mocks['workstation.host.check_prerequisites'].assert_called_once()


class HeadlessPlanTest(unittest.TestCase):
    """End to end through ./bootstrap, no stubs: the plan a headless operator sees."""

    def plan(self, *extra):
        import subprocess
        result = subprocess.run(
            ['/usr/bin/python3', '-I', '-S', '-B', str(ROOT / 'bootstrap'), 'plan', '--config',
             str(ROOT / 'config/standard-single.example.json'), '--format', 'json', *extra],
            capture_output=True, text=True)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return {c['id']: c for c in json.loads(result.stdout)['checks']}

    def test_headless_plan_names_no_desktop_snap_gnome_or_vscode_step(self):
        checks = self.plan('--profiles', 'firewall,gpu')
        self.assertNotIn('stage:desktop', checks)
        self.assertNotIn('stage:plugins', checks)
        self.assertNotIn('snaps.yml', checks['stage:packages']['reason'])
        self.assertNotIn('binaries.yml', checks['stage:packages']['reason'])
        for capability in ('dbeaver', 'ghostty', 'gnome-settings', 'baobab', 'bitwarden'):
            self.assertNotIn(capability, checks)
        self.assertFalse([i for i in checks if i.startswith('extension-')])
        self.assertEqual(checks['stage:firewall']['status'], 'planned')

    def test_the_default_plan_names_every_desktop_step(self):
        checks = self.plan('--profiles', ','.join(DEFAULT))
        self.assertIn('stage:desktop', checks)
        self.assertIn('stage:plugins', checks)
        self.assertIn('snaps.yml', checks['stage:packages']['reason'])
        self.assertIn('dbeaver', checks)


if __name__ == '__main__':
    unittest.main()
