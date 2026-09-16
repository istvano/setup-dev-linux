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
from workstation.java_runtime import candidate_id, candidates, payload_home, verify, install


class JavaVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.versions = candidates(self.home)
        self.versions.mkdir(parents=True)
        self.records = []
        for ident in ('temurin-25', 'temurin-21', 'microsoft-25', 'microsoft-21'):
            record = dict(id=ident, version=ident.rsplit('-', 1)[1] + '.0.1-1', entrypoint='jdk/bin/java',
                          files=[dict(path='jdk/bin/java', kind='file', value=hashlib.sha256(b'fixture').hexdigest(), executable=False)])
            target = destination(self.home, record) / record['entrypoint']
            target.parent.mkdir(parents=True)
            target.write_bytes(b'fixture')
            (self.versions / candidate_id(record)).symlink_to(payload_home(self.home, record))
            self.records.append(record)
        (self.versions / 'current').symlink_to(self.versions / candidate_id(self.records[0]))
        self.lock = patch('workstation.java_runtime.java_lock', return_value=self.records)
        self.manager = patch('workstation.java_runtime.verify_sdkman', return_value=[{'status': 'passed'}])
        self.lock.start()
        self.manager.start()
        self.addCleanup(self.lock.stop)
        self.addCleanup(self.manager.stop)

    def check(self):
        with patch('subprocess.run') as execute:
            result = verify(self.home, ['java', 'sdkman'])
        execute.assert_not_called()
        return result[0]['status']

    def test_four_payloads_and_default_verify_without_commands(self):
        self.assertEqual(self.check(), 'passed')

    def test_wrong_default_is_not_repaired(self):
        link = self.versions / 'current'
        link.unlink()
        link.symlink_to(self.versions / candidate_id(self.records[1]))
        original = os.readlink(link)
        self.assertEqual(self.check(), 'failed')
        self.assertEqual(os.readlink(link), original)

    def test_changed_jdk_fails(self):
        (destination(self.home, self.records[2]) / self.records[2]['entrypoint']).write_text('modified')
        self.assertEqual(self.check(), 'failed')

    def test_swapped_vendor_registration_fails(self):
        link = self.versions / candidate_id(self.records[0])
        link.unlink()
        link.symlink_to(payload_home(self.home, self.records[2]))
        self.assertEqual(self.check(), 'failed')

    def test_missing_required_variant_fails(self):
        (self.versions / candidate_id(self.records[3])).unlink()
        self.assertEqual(self.check(), 'failed')

    def test_missing_sdkman_selection_fails(self):
        self.assertEqual(verify(self.home, ['java'])[0]['status'], 'failed')

    def test_unselected_java_has_no_check(self):
        self.assertEqual(verify(self.home, []), [])

    def test_dangling_default_recovery_keeps_private_backup(self):
        import json
        link = self.versions / 'current'
        link.unlink()
        link.symlink_to('missing')
        def native(*args, **kwargs):
            self.assertFalse(link.is_symlink())
            backups = list((self.home / '.local/state/linux-os-setup/java-default-backups').glob('*.json'))
            self.assertEqual(len(backups), 1)
            self.assertEqual(json.loads(backups[0].read_text())['target'], 'missing')
            self.assertEqual(backups[0].stat().st_mode & 0o777, 0o600)
            link.symlink_to(candidate_id(self.records[0]))
        with patch('os.geteuid', return_value=1000), \
                patch('pwd.getpwuid', return_value=SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.java_runtime.install_artifacts', return_value=False), \
                patch('subprocess.run', side_effect=native):
            self.assertTrue(install({'target': {'user': 'fixture'}}, ['sdkman', 'java']))
        self.assertEqual(self.check(), 'passed')
