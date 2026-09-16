"""Behavioural tests for APT signing-key normalisation and verification."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'script'))

from workstation.repository_keys import (  # noqa: E402
    KeyError_, fingerprint, install_key, is_armoured, to_binary)

VENDORED = ROOT / 'manifest/keys/claude-desktop.asc'


@unittest.skipIf(shutil.which('gpg') is None, 'gpg is not installed')
class KeyNormalisationTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.armoured = VENDORED.read_bytes()
        self.binary = to_binary(self.armoured)

    def test_armoured_input_is_detected(self):
        self.assertTrue(is_armoured(self.armoured))
        self.assertFalse(is_armoured(self.binary))

    def test_binary_input_passes_through_unchanged(self):
        self.assertEqual(to_binary(self.binary), self.binary)

    def test_both_forms_yield_the_same_fingerprint(self):
        self.assertEqual(fingerprint(self.binary), fingerprint(to_binary(self.armoured)))

    def test_garbage_is_rejected_rather_than_written(self):
        source = self.dir / 'bad.key'
        source.write_bytes(b'-----BEGIN PGP PUBLIC KEY BLOCK-----\nnot a key\n')
        with self.assertRaises(KeyError_):
            install_key(source, self.dir / 'out.gpg', None)
        self.assertFalse((self.dir / 'out.gpg').exists())


@unittest.skipIf(shutil.which('gpg') is None, 'gpg is not installed')
class KeyVerificationTest(unittest.TestCase):
    def setUp(self):
        self.dir = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.dir, ignore_errors=True)
        self.source = self.dir / 'key.asc'
        self.source.write_bytes(VENDORED.read_bytes())
        self.expected = fingerprint(to_binary(VENDORED.read_bytes()))
        self.destination = self.dir / 'out.gpg'

    def test_matching_fingerprint_is_installed_as_binary(self):
        self.assertTrue(install_key(self.source, self.destination, self.expected))
        written = self.destination.read_bytes()
        self.assertFalse(is_armoured(written), 'APT ignores an armoured .gpg keyring')
        self.assertEqual(fingerprint(written), self.expected)

    def test_wrong_fingerprint_is_refused_and_nothing_is_written(self):
        wrong = 'A' * 40
        with self.assertRaises(KeyError_):
            install_key(self.source, self.destination, wrong)
        self.assertFalse(self.destination.exists())

    def test_malformed_recorded_fingerprint_is_refused(self):
        with self.assertRaises(KeyError_):
            install_key(self.source, self.destination, 'not-a-fingerprint')

    def test_reinstalling_the_same_key_reports_no_change(self):
        self.assertTrue(install_key(self.source, self.destination, self.expected))
        self.assertFalse(install_key(self.source, self.destination, self.expected))

    def test_symlinked_destination_is_refused(self):
        self.destination.symlink_to(self.dir / 'elsewhere')
        with self.assertRaises(KeyError_):
            install_key(self.source, self.destination, self.expected)


class ManifestKeyTest(unittest.TestCase):
    """Every repository the manifest declares must carry a usable pinned key."""

    @unittest.skipIf(shutil.which('gpg') is None, 'gpg is not installed')
    def test_every_vendored_key_matches_its_recorded_fingerprint(self):
        import json
        manifest = json.loads((ROOT / 'manifest/repositories.json').read_text())
        checked = 0
        for repo in manifest['repositories']:
            if not repo.get('key_file'):
                continue
            data = to_binary((ROOT / repo['key_file']).read_bytes())
            self.assertEqual(fingerprint(data), repo['key_fingerprint'],
                             f"{repo['id']} vendored key does not match its record")
            checked += 1
        self.assertGreater(checked, 0, 'expected at least one vendored key')

    def test_every_repository_records_a_fingerprint(self):
        import json
        manifest = json.loads((ROOT / 'manifest/repositories.json').read_text())
        missing = [r['id'] for r in manifest['repositories'] if not r.get('key_fingerprint')]
        self.assertEqual(missing, [], 'unpinned repository signing keys')


if __name__ == '__main__':
    unittest.main()
