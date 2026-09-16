import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import destination
from workstation.go_runtime import verify


class GoVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.record = {
            'id': 'go', 'version': 'go1.2.3', 'entrypoint': 'go/bin/go',
            'files': [{'path': 'go/bin/go', 'kind': 'file',
                       'value': hashlib.sha256(b'fixture').hexdigest(),
                       'executable': True}],
        }
        target = destination(self.home, self.record) / 'go/bin/go'
        target.parent.mkdir(parents=True)
        target.write_bytes(b'fixture')
        target.chmod(0o755)

    def check(self, selected=('go',)):
        with patch('workstation.go_runtime.go_lock', return_value=self.record), \
                patch('subprocess.run') as execute:
            result = verify(self.home, selected)
        execute.assert_not_called()
        return result

    def test_full_payload_verifies_without_execution(self):
        self.assertEqual(self.check()[0]['status'], 'passed')

    def test_modified_binary_fails_without_repair(self):
        target = destination(self.home, self.record) / 'go/bin/go'
        target.write_bytes(b'modified')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertEqual(target.read_bytes(), b'modified')

    def test_added_hook_fails(self):
        target = destination(self.home, self.record) / 'go/unexpected'
        target.write_text('hook')
        self.assertEqual(self.check()[0]['status'], 'failed')

    def test_unselected_go_has_no_check(self):
        self.assertEqual(self.check([]), [])
