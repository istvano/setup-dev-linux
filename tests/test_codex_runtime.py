"""Codex source boundary and independent payload refusal cases."""
import hashlib
import io
from pathlib import Path
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import destination
from workstation.codex_runtime import extract_exact, install, verify, ARCHIVE_MEMBER
from workstation.config import InputError


def archive(path, payload=b'codex-fixture', extra=False):
    with tarfile.open(path, 'w:gz') as stream:
        member = tarfile.TarInfo(ARCHIVE_MEMBER)
        member.size = len(payload)
        member.mode = 0o755
        stream.addfile(member, io.BytesIO(payload))
        if extra:
            member = tarfile.TarInfo('unexpected-hook')
            member.size = 1
            stream.addfile(member, io.BytesIO(b'x'))


class CodexDelivery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.payload = b'codex-fixture'
        self.record = {
            'id': 'codex', 'version': 'fixture', 'entrypoint': 'codex',
            'url': 'https://github.com/openai/codex/releases/download/fixture/source.tar.gz',
            'sha256': '0' * 64,
            'files': [{'path': 'codex', 'kind': 'file',
                       'value': hashlib.sha256(self.payload).hexdigest(),
                       'executable': True}],
        }
        self.config = {'target': {'user': 'fixture'}}

    def target(self):
        return destination(self.home, self.record)

    def test_exact_archive_normalizes_binary_name_and_verifies(self):
        source = self.home / 'source.tar.gz'
        archive(source, self.payload)
        payload = self.home / 'payload'
        payload.mkdir()
        with patch('workstation.codex_runtime.EXECUTABLE_SIZE', len(self.payload)), \
             patch('workstation.codex_runtime.codex_lock', return_value=self.record):
            extract_exact(source, payload, self.record)
            self.assertEqual((payload / 'codex').read_bytes(), self.payload)
            target = self.target()
            target.parent.mkdir(parents=True)
            payload.rename(target)
            self.assertEqual(verify(self.home, ['codex'])[0]['status'], 'passed')
            (target / 'codex').write_bytes(b'changed')
            self.assertEqual(verify(self.home, ['codex'])[0]['status'], 'failed')
            self.assertEqual(verify(self.home, [])[0:] , [])

    def test_unexpected_archive_member_fails_before_extraction(self):
        source = self.home / 'source.tar.gz'
        archive(source, self.payload, extra=True)
        payload = self.home / 'payload'
        payload.mkdir()
        with patch('workstation.codex_runtime.EXECUTABLE_SIZE', len(self.payload)):
            with self.assertRaisesRegex(InputError, 'unexpected-codex-archive-layout'):
                extract_exact(source, payload, self.record)
        self.assertEqual(list(payload.iterdir()), [])

    def test_wrong_download_digest_never_places_binary(self):
        source = self.home / 'source.tar.gz'
        archive(source, self.payload)
        with patch('workstation.codex_runtime.pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
             patch('workstation.codex_runtime.os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.codex_runtime.codex_lock', return_value=self.record), \
             patch('workstation.codex_runtime.urllib.request.urlopen', return_value=io.BytesIO(source.read_bytes())):
            with self.assertRaisesRegex(InputError, 'codex-download-digest-mismatch'):
                install(self.config)
        self.assertFalse(self.target().exists())

    def test_modified_existing_binary_refuses_source_and_replacement(self):
        target = self.target()
        target.mkdir(parents=True)
        (target / 'codex').write_bytes(b'changed')
        (target / 'codex').chmod(0o755)
        with patch('workstation.codex_runtime.pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
             patch('workstation.codex_runtime.os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.codex_runtime.codex_lock', return_value=self.record), \
             patch('workstation.codex_runtime.urllib.request.urlopen', side_effect=AssertionError('must not download')):
            with self.assertRaisesRegex(InputError, 'user-tool-tree-drift'):
                install(self.config)
        self.assertEqual((target / 'codex').read_bytes(), b'changed')


if __name__ == '__main__':
    unittest.main()
