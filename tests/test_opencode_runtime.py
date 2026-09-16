import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import destination
from workstation.opencode_runtime import verify


class OpenCodeVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.record = {
            'id': 'opencode', 'version': 'fixture', 'entrypoint': 'opencode',
            'files': [{'path': 'opencode', 'kind': 'file',
                       'value': hashlib.sha256(b'fixture').hexdigest(),
                       'executable': True}],
        }
        binary = destination(self.home, self.record) / 'opencode'
        binary.parent.mkdir(parents=True)
        binary.write_bytes(b'fixture')
        binary.chmod(0o755)

    def check(self, selected=('opencode',)):
        with patch('workstation.opencode_runtime.opencode_lock', return_value=self.record), \
                patch('subprocess.run') as execute:
            result = verify(self.home, selected)
        execute.assert_not_called()
        return result

    def test_complete_binary_payload_without_launch(self):
        self.assertEqual(self.check()[0]['status'], 'passed')

    def test_changed_binary_fails_without_repair(self):
        binary = destination(self.home, self.record) / 'opencode'
        binary.write_bytes(b'modified')
        self.assertEqual(self.check()[0]['status'], 'failed')
        self.assertEqual(binary.read_bytes(), b'modified')

    def test_added_hook_fails(self):
        (destination(self.home, self.record) / 'startup-hook').write_text('unexpected')
        self.assertEqual(self.check()[0]['status'], 'failed')

    def test_unselected_agent_has_no_check(self):
        self.assertEqual(self.check([]), [])
