import hashlib
import os
from pathlib import Path
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'script'))
from workstation.artifacts import destination
from workstation.jvm_tools import candidate_id, paths, verify, install


class JVMToolVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.record = dict(id='maven', version='1.0', entrypoint='tool/bin/mvn', files=[dict(
            path='tool/bin/mvn', kind='file', value=hashlib.sha256(b'fixture').hexdigest(), executable=False)])
        target = destination(self.home, self.record) / self.record['entrypoint']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'fixture')
        self.versions, payload = paths(self.home, self.record)
        self.versions.mkdir(parents=True)
        (self.versions / candidate_id(self.record)).symlink_to(payload)
        (self.versions / 'current').symlink_to(candidate_id(self.record))
        self.lock = patch('workstation.jvm_tools.tool_lock', return_value=[self.record])
        self.java = patch('workstation.jvm_tools.verify_java', return_value=[{'status': 'passed'}])
        self.lock.start()
        self.java.start()
        self.addCleanup(self.lock.stop)
        self.addCleanup(self.java.stop)

    def check(self, selected=('maven', 'sdkman', 'java')):
        with patch('subprocess.run') as execute:
            result = verify(self.home, selected)
        execute.assert_not_called()
        return result

    def test_payload_registration_and_default_pass(self):
        self.assertEqual(self.check()[0]['status'], 'passed')

    def test_default_drift_is_not_repaired(self):
        link = self.versions / 'current'
        link.unlink()
        link.symlink_to('other')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertEqual(os.readlink(link), 'other')

    def test_modified_payload_fails(self):
        (destination(self.home, self.record) / self.record['entrypoint']).write_text('changed')
        self.assertEqual(self.check()[0]['status'], 'failed')

    def test_wrong_registration_fails(self):
        link = self.versions / candidate_id(self.record)
        link.unlink()
        link.symlink_to(self.home)
        self.assertEqual(self.check()[0]['status'], 'failed')

    def test_missing_java_selection_fails(self):
        self.assertEqual(self.check(['maven', 'sdkman'])[0]['status'], 'failed')

    def test_unselected_tool_has_no_check(self):
        self.assertEqual(self.check(['java', 'sdkman']), [])

    def test_dangling_default_is_backed_up_before_native_recovery(self):
        import json
        link = self.versions / 'current'
        link.unlink()
        link.symlink_to('missing')
        def native(*args, **kwargs):
            self.assertFalse(link.is_symlink())
            backups = list((self.home / '.local/state/linux-os-setup/jvm-tool-default-backups').glob('*.json'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text())['target'], 'missing')
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
            link.symlink_to(candidate_id(self.record))
        with patch('os.geteuid', return_value=1000), \
                patch('pwd.getpwuid', return_value=SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.jvm_tools.install_artifacts', return_value=False), \
                patch('subprocess.run', side_effect=native):
            self.assertTrue(install({'target': {'user': 'fixture'}}, ['sdkman', 'java', 'maven']))
        self.assertEqual(self.check()[0]['status'], 'passed')
