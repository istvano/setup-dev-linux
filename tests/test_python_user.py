import hashlib
import io
from pathlib import Path
import sys
import shutil
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import destination
from workstation.python_user import install, verify, seal_python_payload, PYTHON_NAME, SYSCONFIG, PREFIX_MARKER


class PythonUserVerifier(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.records = []
        for identity, relative in [('uv', 'bundle/uv'), ('python', 'runtime/bin/python')]:
            record = {'id': identity, 'version': 'fixture',
                      'entrypoint': relative,
                      'files': [{'path': relative, 'kind': 'file',
                                 'value': hashlib.sha256(identity.encode()).hexdigest(),
                                 'executable': True}]}
            executable = destination(self.home, record) / relative
            executable.parent.mkdir(parents=True)
            executable.write_bytes(identity.encode())
            executable.chmod(0o755)
            self.records.append(record)
        seal_python_payload(destination(self.home, self.records[1]))

    def check(self, selected=('uv', 'python')):
        with patch('workstation.python_user.python_lock', return_value=self.records), \
                patch('subprocess.run') as execute:
            result = verify(self.home, selected)
        execute.assert_not_called()
        return result

    def test_complete_payload_without_execution(self):
        self.assertEqual([c['status'] for c in self.check()], ['passed', 'passed'])

    def test_modified_interpreter_fails_without_repair(self):
        path = destination(self.home, self.records[1]) / 'runtime/bin/python'
        path.chmod(0o755)
        path.write_bytes(b'drift')
        path.chmod(0o555)
        self.assertEqual(self.check()[1]['status'], 'failed')
        self.assertEqual(path.read_bytes(), b'drift')

    def test_added_payload_and_missing_uv_fail_independently(self):
        target = destination(self.home, self.records[1]) / 'runtime/bin/extra'
        target.parent.chmod(0o755)
        target.write_text('unexpected')
        seal_python_payload(destination(self.home, self.records[1]))
        self.assertEqual([c['status'] for c in self.check()], ['passed', 'failed'])
        (destination(self.home, self.records[0]) / 'bundle/uv').unlink()
        self.assertEqual([c['status'] for c in self.check()], ['failed', 'failed'])

    def test_unselected_payload_is_not_checked(self):
        self.assertEqual([c['id'] for c in self.check(['uv'])], ['uv'])

    def test_generated_sysconfig_requires_exact_final_prefix(self):
        record = self.records[1]
        target = destination(self.home, record)
        (target / 'runtime/bin').chmod(0o755)
        (target / 'runtime/bin/python').unlink()
        (target / 'runtime').chmod(0o755)
        (target / 'runtime/bin').rmdir()
        target.chmod(0o755)
        (target / 'runtime').rmdir()
        prefix = str(target / PYTHON_NAME).encode()
        generated = b'PREFIX = "' + prefix + b'"\nBINDIR = "' + prefix + b'/bin"\n'
        sysconfig = target / SYSCONFIG
        sysconfig.parent.mkdir(parents=True)
        sysconfig.write_bytes(generated)
        seal_python_payload(target)
        record['files'] = [{
            'path': SYSCONFIG, 'kind': 'file',
            'value': hashlib.sha256(generated.replace(prefix, PREFIX_MARKER)).hexdigest(),
            'executable': False,
        }]
        self.assertEqual(self.check(['python'])[0]['status'], 'passed')
        sysconfig.chmod(0o644)
        sysconfig.write_bytes(generated.replace(prefix, b'/tmp/wrong-prefix'))
        sysconfig.chmod(0o444)
        self.assertEqual(self.check(['python'])[0]['status'], 'failed')
        self.assertIn(b'/tmp/wrong-prefix', sysconfig.read_bytes())


class PythonAcquisition(unittest.TestCase):
    def test_wrong_archive_hash_never_executes_uv_or_places_python(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        account = type('Account', (), {'pw_name': 'fixture', 'pw_dir': str(home)})()
        uv = {'id': 'uv', 'version': 'fixture', 'entrypoint': 'bundle/uv'}
        python = {'id': 'python', 'version': 'fixture',
                  'url': 'https://example.invalid/archive', 'sha256': '0' * 64}
        with patch('workstation.python_user.pwd.getpwuid', return_value=account), \
                patch('workstation.python_user.os.geteuid', return_value=1000), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.python_user.python_lock', return_value=(uv, python)), \
                patch('workstation.python_user.install_artifacts', return_value=False), \
                patch('workstation.python_user.urllib.request.urlopen', return_value=io.BytesIO(b'corrupt')), \
                patch('workstation.python_user.subprocess.run') as execute:
            with self.assertRaisesRegex(ValueError, 'user-python-download-digest-mismatch'):
                install({'target': {'user': 'fixture'}}, ['uv', 'python'])
            execute.assert_not_called()
        self.assertFalse(destination(home, python).exists())

    def test_uv_only_selection_does_not_fetch_python(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        home = Path(temporary.name)
        account = type('Account', (), {'pw_name': 'fixture', 'pw_dir': str(home)})()
        uv = {'id': 'uv', 'version': 'fixture', 'entrypoint': 'bundle/uv'}
        python = {'id': 'python', 'version': 'fixture'}
        with patch('workstation.python_user.pwd.getpwuid', return_value=account), \
                patch('workstation.python_user.os.geteuid', return_value=1000), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.python_user.python_lock', return_value=(uv, python)), \
                patch('workstation.python_user.install_artifacts', return_value=True), \
                patch('workstation.python_user.verify', return_value=[{'status': 'passed'}]), \
                patch('workstation.python_user.urllib.request.urlopen') as download:
            self.assertTrue(install({'target': {'user': 'fixture'}}, ['uv']))
            download.assert_not_called()
        self.assertFalse(destination(home, python).exists())

class SealedPlacementTest(unittest.TestCase):
    """A sealed payload must still be movable into its final location.

    Renaming a directory into a different parent rewrites its own ".." entry,
    which the kernel refuses unless the directory itself is writable. Sealing
    the payload before the move therefore fails with EACCES on a real
    filesystem, which no fixture-only test observes.
    """

    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(self._cleanup)
        self.stage = self.root / '.staging'
        (self.stage / 'payload' / 'lib').mkdir(parents=True)
        (self.stage / 'payload' / 'lib' / 'file').write_text('x')

    def _cleanup(self):
        for path in sorted(self.root.rglob('*'), reverse=True):
            if not path.is_symlink():
                path.chmod(0o700)
        shutil.rmtree(self.root, ignore_errors=True)

    def test_sealed_payload_moves_into_place_and_stays_sealed(self):
        payload, target = self.stage / 'payload', self.root / '3.14.7'
        seal_python_payload(payload)
        self.assertFalse(payload.stat().st_mode & 0o222, 'payload must be sealed first')

        sealed_mode = payload.stat().st_mode
        payload.chmod(sealed_mode | 0o200)
        payload.rename(target)
        target.chmod(sealed_mode)

        self.assertTrue(target.is_dir())
        self.assertFalse(target.stat().st_mode & 0o222,
                         'the installed runtime must end up read-only')
        self.assertFalse((target / 'lib').stat().st_mode & 0o222)

    def test_moving_a_sealed_directory_without_restoring_write_fails(self):
        payload, target = self.stage / 'payload', self.root / '3.14.7'
        seal_python_payload(payload)
        with self.assertRaises(PermissionError):
            payload.rename(target)

