import hashlib
from pathlib import Path
import sys
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError
from workstation.rust_runtime import install, state_root, verify


class RustVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.payload = b'fixture-rustc'
        self.lock = {
            'manager': {
                'version': '1.2.3',
                'sha256': hashlib.sha256(b'fixture-rustup').hexdigest(),
                'shims': ['cargo', 'rustc'],
            },
            'toolchain': {
                'version': '1.99.0',
                'host': 'x86_64-unknown-linux-gnu',
                'files': [
                    {'path': 'bin/rustc', 'sha256': hashlib.sha256(self.payload).hexdigest(),
                     'executable': True},
                ],
            },
        }
        self.root = state_root(self.home, self.lock)
        binary = self.root / 'cargo/bin/rustup'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'fixture-rustup')
        binary.chmod(0o755)
        for name in self.lock['manager']['shims']:
            (binary.parent / name).symlink_to('rustup')
        settings = self.root / 'rustup/settings.toml'
        settings.parent.mkdir(parents=True)
        settings.write_text(
            'version = "12"\n'
            'default_toolchain = "1.99.0-x86_64-unknown-linux-gnu"\n'
            'profile = "minimal"\n\n[overrides]\n')
        rustc = self.root / 'rustup/toolchains/1.99.0-x86_64-unknown-linux-gnu/bin/rustc'
        rustc.parent.mkdir(parents=True)
        rustc.write_bytes(self.payload)
        rustc.chmod(0o755)

    def check(self, selected=('rust',)):
        with patch('workstation.rust_runtime.rust_lock', return_value=self.lock), \
                patch('workstation.rust_runtime.prerequisites_pass', return_value=True), \
                patch('subprocess.run') as execute:
            result = verify(self.home, selected)
        execute.assert_not_called()
        return result

    def test_manager_default_and_toolchain_verify_without_execution(self):
        self.assertEqual(self.check()[0]['status'], 'passed')

    def test_modified_manager_fails_without_repair(self):
        binary = self.root / 'cargo/bin/rustup'
        binary.write_bytes(b'modified')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertEqual(binary.read_bytes(), b'modified')

    def test_added_shim_fails(self):
        extra = self.root / 'cargo/bin/unreviewed-hook'
        extra.write_text('hook')
        self.assertEqual(self.check()[0]['status'], 'failed')

    def test_modified_toolchain_fails_without_repair(self):
        rustc = self.root / 'rustup/toolchains/1.99.0-x86_64-unknown-linux-gnu/bin/rustc'
        rustc.write_bytes(b'modified')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertEqual(rustc.read_bytes(), b'modified')

    def test_wrong_default_fails_without_repair(self):
        settings = self.root / 'rustup/settings.toml'
        settings.write_text(
            'version = "12"\n'
            'default_toolchain = "nightly-x86_64-unknown-linux-gnu"\n'
            'profile = "minimal"\n\n[overrides]\n')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertIn('nightly', settings.read_text())

    def test_missing_prerequisite_fails(self):
        with patch('workstation.rust_runtime.prerequisites_pass', return_value=False):
            self.assertEqual(verify(self.home, ['rust'])[0]['status'], 'failed')

    def test_unselected_rust_has_no_check(self):
        self.assertEqual(self.check([]), [])

    def test_corrupt_component_fails_before_execution_or_placement(self):
        install_home = self.home / 'fresh-install-home'
        install_home.mkdir()
        lock = {
            'manager': {'version': '1.2.3'},
            'toolchain': {
                'version': '1.99.0', 'host': 'x86_64-unknown-linux-gnu',
                'date': '2026-01-01',
                'manifest': {'url': 'https://static.rust-lang.org/dist/channel-rust-1.99.0.toml',
                             'sha256': 'a' * 64},
                'manifest_checksum': {
                    'url': 'https://static.rust-lang.org/dist/channel-rust-1.99.0.toml.sha256',
                    'sha256': 'b' * 64},
                'components': [{'id': 'rustc', 'url': 'https://static.rust-lang.org/dist/rustc',
                                'sha256': 'c' * 64}],
            },
        }

        def acquire(source, output):
            if source in lock['toolchain']['components']:
                raise InputError('rust-download-digest-mismatch')
            output.parent.mkdir(parents=True, exist_ok=True)
            if source is lock['toolchain']['manifest_checksum']:
                output.write_text('a' * 64 + '  channel-rust-1.99.0.toml\n')
            else:
                output.write_bytes(b'fixture')

        config = {'target': {'user': 'fixture-user'}}
        account = types.SimpleNamespace(pw_name='fixture-user', pw_dir=str(install_home))
        with patch('workstation.rust_runtime.rust_lock', return_value=lock), \
                patch('workstation.rust_runtime.prerequisites_pass', return_value=True), \
                patch('workstation.rust_runtime.pwd.getpwuid', return_value=account), \
                patch('workstation.rust_runtime.os.geteuid', return_value=1000), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.rust_runtime.download', side_effect=acquire), \
                patch('workstation.rust_runtime.subprocess.run') as execute:
            with self.assertRaises(InputError):
                install(config, ['rust'])
        execute.assert_not_called()
        self.assertFalse(state_root(install_home, lock).exists())
