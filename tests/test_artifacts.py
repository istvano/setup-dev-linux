import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
import stat
import zipfile
import io
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'script'))
from workstation.artifacts import destination, validate_payload, extract_zip, install
from workstation.config import InputError


class ImmutableTools(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = Path(self.tmp.name)
        self.record = {'id': 'fixture', 'version': 'v1', 'files': [
            {'path': 'tool', 'kind': 'file', 'value': hashlib.sha256(b'payload').hexdigest(), 'executable': True}]}
        self.path = destination(self.home, self.record)
        self.path.mkdir(parents=True)
        (self.path / 'tool').write_bytes(b'payload')
        (self.path / 'tool').chmod(0o755)

    def test_reviewed_payload_passes(self):
        validate_payload(self.path, self.record)

    def test_hardlinked_payload_is_verified_by_content(self):
        import os
        os.link(self.path / 'tool', self.path / 'linked-tool')
        self.record['files'].append(dict(self.record['files'][0], path='linked-tool'))
        validate_payload(self.path, self.record)

    def test_modified_payload_fails(self):
        (self.path / 'tool').write_bytes(b'modified')
        with self.assertRaises(InputError):
            validate_payload(self.path, self.record)

    def test_added_hook_fails(self):
        (self.path / 'hook').write_text('unexpected')
        with self.assertRaises(InputError):
            validate_payload(self.path, self.record)

    def test_missing_executable_permission_fails(self):
        (self.path / 'tool').chmod(0o644)
        with self.assertRaises(InputError):
            validate_payload(self.path, self.record)

    def test_symlink_parent_fails(self):
        (self.home / 'linked').symlink_to(self.home / '.local', target_is_directory=True)
        from workstation.artifacts import safe_path
        with self.assertRaises(InputError):
            safe_path(self.home, self.home / 'linked/share/elsewhere')


class ZipPayloads(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        self.archive = self.root / 'archive.zip'
        self.payload = self.root / 'payload'
        self.payload.mkdir()

    def archive_with(self, name, mode=stat.S_IFREG | 0o644):
        with zipfile.ZipFile(self.archive, 'w') as archive:
            archive.writestr('safe', b'first')
            info = zipfile.ZipInfo(name)
            info.external_attr = mode << 16
            archive.writestr(info, b'payload')

    def test_executable_mode_and_contents(self):
        self.archive_with('nested/tool', stat.S_IFREG | 0o4755)
        extract_zip(self.archive, self.payload)
        self.assertEqual((self.payload / 'nested/tool').read_bytes(), b'payload')
        self.assertEqual(stat.S_IMODE((self.payload / 'nested/tool').stat().st_mode), 0o755)
        self.assertEqual(stat.S_IMODE((self.payload / 'safe').stat().st_mode), 0o644)

    def test_unsafe_names_fail_before_writes(self):
        for name in ('../escape', '/absolute', 'a/../../escape', 'a//b', './a', 'a\\b'):
            with self.subTest(name=name):
                self.archive_with(name)
                with self.assertRaises(InputError):
                    extract_zip(self.archive, self.payload)
                self.assertEqual(list(self.payload.iterdir()), [])

    def test_links_and_special_files_fail_before_writes(self):
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFCHR, stat.S_IFSOCK):
            with self.subTest(kind=kind):
                self.archive_with('unsafe', kind | 0o755)
                with self.assertRaises(InputError):
                    extract_zip(self.archive, self.payload)
                self.assertEqual(list(self.payload.iterdir()), [])

    def test_duplicate_names_fail_before_writes(self):
        self.archive_with('safe/', stat.S_IFDIR | 0o755)
        with self.assertRaises(InputError):
            extract_zip(self.archive, self.payload)
        self.assertEqual(list(self.payload.iterdir()), [])


class AcquisitionBoundary(unittest.TestCase):
    def test_corrupt_download_never_places_or_executes_payload(self):
        with tempfile.TemporaryDirectory() as temporary:
            home = Path(temporary)
            record = dict(id='fixture', version='1', url='https://github.com/example/fixture',
                          format='binary', entrypoint='tool', sha256=hashlib.sha256(b'expected').hexdigest(), files=[])
            with patch('os.geteuid', return_value=1000), \
                    patch('pwd.getpwuid', return_value=SimpleNamespace(pw_name='fixture', pw_dir=str(home))), \
                    patch('workstation.storage.preflight', return_value=([], 0)), \
                    patch('urllib.request.urlopen', return_value=io.BytesIO(b'corrupt')), \
                    patch('subprocess.run') as execute:
                with self.assertRaisesRegex(InputError, 'download-digest-mismatch'):
                    install([record], {'target': {'user': 'fixture'}})
            execute.assert_not_called()
            self.assertFalse(destination(home, record).exists())
            self.assertEqual(list(destination(home, record).parent.glob('.staging-*')), [])
