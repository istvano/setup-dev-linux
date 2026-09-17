"""F04 integrity and pre-write guarantees, with no fixture downloads."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import sys
import tarfile
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError
from workstation.controller import unpack, validate_lock, validate_tree, verify_archive
from workstation.cli import main


class ControllerIntegrity(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)

    def archive(self, name='runtime/tool', contents=b'fixture', symlink=None):
        archive = self.root / 'input.tar.gz'
        with tarfile.open(archive, 'w:gz') as target:
            info = tarfile.TarInfo(name)
            if symlink:
                info.type = tarfile.SYMTYPE
                info.linkname = symlink
                target.addfile(info)
            else:
                info.size = len(contents)
                target.addfile(info, io.BytesIO(contents))
        return archive

    def test_bad_digest_rejected_before_unpack(self):
        archive = self.archive()
        with self.assertRaisesRegex(InputError, 'digest-mismatch'):
            verify_archive(archive, '0' * 64)
        self.assertFalse((self.root / 'runtime').exists())

    def test_safe_archive_roundtrip(self):
        archive = self.archive()
        destination = self.root / 'extracted'
        unpack(archive, destination)
        validate_tree(archive, destination)
        self.assertEqual((destination / 'runtime/tool').read_bytes(), b'fixture')

    def test_changed_executable_rejected(self):
        archive = self.archive()
        destination = self.root / 'extracted'
        unpack(archive, destination)
        (destination / 'runtime/tool').write_bytes(b'changed')
        with self.assertRaisesRegex(InputError, 'controller-tree-drift'):
            validate_tree(archive, destination)

    def test_extra_python_hook_rejected(self):
        archive = self.archive()
        destination = self.root / 'extracted'
        unpack(archive, destination)
        (destination / 'runtime/sitecustomize.py').write_text('unexpected')
        with self.assertRaisesRegex(InputError, 'unexpected-controller-runtime-file'):
            validate_tree(archive, destination)

    def test_path_traversal_rejected(self):
        archive = self.archive('../escape')
        with self.assertRaises(tarfile.FilterError):
            unpack(archive, self.root / 'extracted')
        self.assertFalse((self.root / 'escape').exists())

    def test_symlink_escape_rejected(self):
        archive = self.archive(symlink='/etc/passwd')
        with self.assertRaises(tarfile.FilterError):
            unpack(archive, self.root / 'extracted')

    def test_changed_dependency_lock_rejected(self):
        (self.root / 'locks').mkdir()
        for name in ['pyproject.toml', 'uv.lock', 'locks/bootstrap.json']:
            (self.root / name).write_bytes((ROOT / name).read_bytes())
        (self.root / 'uv.lock').write_text('unreviewed graph')
        with self.assertRaisesRegex(InputError, 'dependency-lock-drift'):
            validate_lock(self.root)

    def test_failed_guard_never_calls_controller(self):
        import getpass
        context = {'config': {'example_only': False, 'target': {'user': getpass.getuser()}},
                   'provenance': {}, 'selected': [], 'entries': {}}
        with patch('workstation.cli.load_context', return_value=context), patch('os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([{'id': 'mount', 'status': 'failed', 'reason': 'fixture'}], 1)), \
             patch('workstation.controller.apply_foundation') as apply, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['install', '--config', 'fixture', '--format', 'json']), 1)
            apply.assert_not_called()

    def test_verify_never_calls_controller(self):
        import getpass
        context = {'config': {'example_only': False, 'target': {'user': getpass.getuser()}},
                   'provenance': {}, 'selected': [], 'entries': {}}
        # Delivery verification is stubbed out: this asserts that verify reports
        # rather than applies, not what the live machine currently has.
        with patch('workstation.cli.load_context', return_value=context), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.packages.verify_packages', return_value=[]), \
             patch('workstation.desktop.verify', return_value=[]), \
             patch('workstation.delivery.verify', return_value=[]), \
             patch('workstation.plugins.verify', return_value=[]), \
             patch('workstation.npm_cli.verify', return_value=[]), \
             patch('workstation.controller.apply_foundation') as apply, contextlib.redirect_stdout(io.StringIO()):
            self.assertEqual(main(['verify', '--config', 'fixture', '--format', 'json']), 3)
            apply.assert_not_called()


if __name__ == '__main__':
    unittest.main()
