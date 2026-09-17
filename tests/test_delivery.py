"""Verification of manifest delivery beyond APT packages.

Verification reports drift and never repairs it, so these tests are mostly
about failing when the machine does not match rather than passing when it does.
"""
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))

from workstation import delivery  # noqa: E402
from workstation.delivery import (  # noqa: E402
    verify, verify_binaries, verify_repositories, verify_snaps)


def summary(checks, identifier):
    return [c for c in checks if c['id'] == identifier][0]


def failures(checks):
    return [c for c in checks if c['status'] == 'failed' and not c['id'].startswith('manifest-')]


class BinaryVerificationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        self.install = self.root / 'bin'
        self.install.mkdir()

    def write(self, binaries):
        (self.root / 'manifest/binaries.json').write_text(json.dumps(
            {'schema_version': 1, 'install_dir': str(self.install), 'binaries': binaries}))

    def place(self, name, content=b'x', mode=0o755):
        path = self.install / name
        path.write_bytes(content)
        path.chmod(mode)
        return path

    def raw(self, sha256, **overrides):
        record = {'id': 'yq', 'kind': 'raw', 'group': 'core', 'sha256': sha256}
        record.update(overrides)
        return record

    def test_a_present_executable_raw_binary_matching_its_pin_passes(self):
        import hashlib
        content = b'binary contents'
        self.place('yq', content)
        self.write([self.raw(hashlib.sha256(content).hexdigest())])
        checks = verify_binaries(self.root)
        self.assertEqual(failures(checks), [])
        self.assertEqual(summary(checks, 'manifest-binaries')['status'], 'passed')

    def test_a_missing_binary_fails(self):
        self.write([self.raw('a' * 64)])
        self.assertEqual(failures(verify_binaries(self.root))[0]['reason'], 'missing')

    def test_a_non_executable_binary_fails(self):
        self.place('yq', mode=0o644)
        self.write([self.raw('a' * 64)])
        self.assertEqual(failures(verify_binaries(self.root))[0]['reason'], 'not-executable')

    def test_a_raw_binary_that_no_longer_matches_its_pin_fails(self):
        """A raw asset is installed verbatim, so the pin still describes it and
        replacement is detectable."""
        self.place('yq', b'replaced')
        self.write([self.raw('a' * 64)])
        self.assertEqual(failures(verify_binaries(self.root))[0]['reason'],
                         'does-not-match-the-pinned-checksum')

    def test_an_unpacked_archive_is_checked_for_presence_only(self):
        """Archives are unpacked, so the installed file is not the asset and its
        digest cannot be compared with the pin."""
        self.place('helm', b'anything at all')
        self.write([{'id': 'helm', 'kind': 'tar', 'group': 'kubernetes', 'sha256': 'a' * 64}])
        self.assertEqual(failures(verify_binaries(self.root)), [])

    def test_a_vendor_deb_is_checked_through_dpkg(self):
        self.write([{'id': 'obsidian', 'kind': 'deb', 'group': 'productivity',
                     'sha256': 'a' * 64}])
        with patch.object(delivery, 'installed_packages', return_value={'obsidian'}):
            self.assertEqual(failures(verify_binaries(self.root)), [])
        with patch.object(delivery, 'installed_packages', return_value=set()):
            self.assertEqual(failures(verify_binaries(self.root))[0]['reason'],
                             'vendor-package-not-installed')

    def test_groups_narrow_what_is_checked(self):
        self.write([self.raw('a' * 64, group='gpu')])
        self.assertEqual(verify_binaries(self.root, groups=['core']), [])


class SnapVerificationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        (self.root / 'manifest/snaps.json').write_text(json.dumps(
            {'schema_version': 1,
             'snaps': [{'name': 'firefox', 'channel': 'latest/stable',
                        'group': 'productivity'}]}))

    def listing(self, body, returncode=0):
        return subprocess.CompletedProcess([], returncode, 'Name Version Rev Tracking\n' + body)

    def test_a_snap_on_its_declared_channel_passes(self):
        with patch.object(delivery.subprocess, 'run',
                          return_value=self.listing('firefox 1 2 latest/stable mozilla\n')):
            checks = verify_snaps(self.root)
        self.assertEqual(failures(checks), [])

    def test_a_missing_snap_fails(self):
        with patch.object(delivery.subprocess, 'run', return_value=self.listing('')):
            self.assertEqual(failures(verify_snaps(self.root))[0]['reason'], 'not-installed')

    def test_a_snap_on_another_channel_fails(self):
        with patch.object(delivery.subprocess, 'run',
                          return_value=self.listing('firefox 1 2 latest/edge mozilla\n')):
            reason = failures(verify_snaps(self.root))[0]['reason']
        self.assertIn('latest/edge', reason)

    def test_snapd_unavailable_fails_rather_than_passing_quietly(self):
        with patch.object(delivery.subprocess, 'run', return_value=self.listing('', 1)):
            checks = verify_snaps(self.root)
        self.assertEqual(checks[0]['status'], 'failed')
        self.assertEqual(checks[0]['reason'], 'snapd-unavailable')


class RepositoryVerificationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(__import__('shutil').rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        self.keyring = self.root / 'keyrings'
        self.sources = self.root / 'sources'
        self.keyring.mkdir()
        self.sources.mkdir()
        patcher = patch.multiple(delivery, KEYRING_DIR=self.keyring, SOURCES_DIR=self.sources)
        patcher.start()
        self.addCleanup(patcher.stop)

    def write(self, **overrides):
        record = {'id': 'docker', 'uri': 'https://download.docker.com/linux/ubuntu',
                  'key_fingerprint': 'A' * 40}
        record.update(overrides)
        (self.root / 'manifest/repositories.json').write_text(
            json.dumps({'schema_version': 1, 'repositories': [record]}))

    def test_a_configured_repository_with_the_recorded_key_passes(self):
        self.write()
        (self.keyring / 'docker.gpg').write_bytes(b'key')
        (self.sources / 'workstation-docker.sources').write_text('Types: deb\n')
        with patch.object(delivery, 'key_fingerprint', return_value='A' * 40):
            self.assertEqual(failures(verify_repositories(self.root)), [])

    def test_a_missing_keyring_fails(self):
        self.write()
        self.assertEqual(failures(verify_repositories(self.root))[0]['reason'],
                         'keyring-missing')

    def test_a_keyring_that_is_not_the_recorded_key_fails(self):
        self.write()
        (self.keyring / 'docker.gpg').write_bytes(b'key')
        with patch.object(delivery, 'key_fingerprint', return_value='B' * 40):
            self.assertEqual(failures(verify_repositories(self.root))[0]['reason'],
                             'keyring-is-not-the-recorded-key')

    def test_a_missing_source_file_fails(self):
        self.write()
        (self.keyring / 'docker.gpg').write_bytes(b'key')
        with patch.object(delivery, 'key_fingerprint', return_value='A' * 40):
            self.assertEqual(failures(verify_repositories(self.root))[0]['reason'],
                             'source-not-configured')

    def test_a_vendor_managed_source_needs_no_file_of_ours(self):
        """The repository was configured to obtain the package and handed back,
        so the source file is the vendor's and named as the vendor chose."""
        self.write(self_registers_source=True)
        (self.keyring / 'docker.gpg').write_bytes(b'key')
        with patch.object(delivery, 'key_fingerprint', return_value='A' * 40):
            self.assertEqual(failures(verify_repositories(self.root)), [])


class RealManifestTest(unittest.TestCase):
    """The repository's own manifest must be verifiable at all."""

    def test_verification_runs_against_the_real_manifest(self):
        checks = verify(ROOT)
        identifiers = {c['id'] for c in checks}
        for expected in ('manifest-binaries', 'manifest-snaps', 'manifest-repositories'):
            self.assertIn(expected, identifiers)

    def test_every_check_names_a_status_and_reason(self):
        for check in verify(ROOT):
            self.assertIn(check['status'], ('passed', 'failed', 'deferred'))
            self.assertTrue(check['reason'])


if __name__ == '__main__':
    unittest.main()
