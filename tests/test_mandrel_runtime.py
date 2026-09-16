import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'script'))
from workstation.artifacts import destination
from workstation.mandrel_runtime import paths, verify


class MandrelVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.record = dict(id='mandrel', version='25.0.4.1-Final', entrypoint='jdk/bin/native-image', files=[dict(
            path='jdk/bin/native-image', kind='file', value=hashlib.sha256(b'fixture').hexdigest(), executable=False)])
        target = destination(self.home, self.record) / self.record['entrypoint']
        target.parent.mkdir(parents=True)
        target.write_bytes(b'fixture')
        link, payload = paths(self.home, self.record)
        link.parent.mkdir(parents=True)
        link.symlink_to(payload)
        self.lock = patch('workstation.mandrel_runtime.mandrel_lock', return_value=self.record)
        self.deps = patch('workstation.mandrel_runtime.prerequisites_pass', return_value=True)
        self.lock.start()
        self.deps.start()
        self.addCleanup(self.lock.stop)
        self.addCleanup(self.deps.stop)

    def check(self):
        with patch('subprocess.run') as execute:
            result = verify(self.home, ['mandrel', 'sdkman', 'java'])
        execute.assert_not_called()
        return result[0]['status']

    def test_payload_and_registration_pass_without_commands(self):
        self.assertEqual(self.check(), 'passed')

    def test_modified_payload_fails_without_repair(self):
        target = destination(self.home, self.record) / self.record['entrypoint']
        target.write_text('modified')
        self.assertEqual(self.check(), 'failed')
        self.assertEqual(target.read_text(), 'modified')

    def test_missing_dependency_fails(self):
        with patch('workstation.mandrel_runtime.prerequisites_pass', return_value=False):
            self.assertEqual(self.check(), 'failed')

    def test_unselected_mandrel_has_no_check(self):
        self.assertEqual(verify(self.home, []), [])
