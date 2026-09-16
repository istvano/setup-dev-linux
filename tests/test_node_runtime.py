import hashlib
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.node_runtime import verify


class NodeVerification(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.home = Path(self.temporary.name)
        self.nvm = self.home / '.local/share/linux-os-setup/nvm'
        self.target = self.nvm / 'versions/node/v1.0.0'
        self.target.mkdir(parents=True)
        (self.target / 'node').write_bytes(b'fixture')
        self.record = {'version': 'v1.0.0', 'files': [{'path': 'node', 'kind': 'file', 'value': hashlib.sha256(b'fixture').hexdigest(), 'executable': False}]}
        (self.nvm / 'alias').mkdir()
        (self.nvm / 'alias/default').write_text('v1.0.0\n')
        self.tools = {'nvm': {'id': 'nvm', 'version': 'v1', 'entrypoint': 'source/nvm.sh'}}
        manager = self.home / '.local/share/linux-os-setup/tools/nvm/v1/source'
        for name in ['nvm.sh', 'nvm-exec']:
            (self.nvm / name).symlink_to(manager / name)

    def check(self):
        with patch('workstation.node_runtime.node_lock', return_value=self.record), patch('subprocess.run') as command:
            result = verify(self.home, self.tools, ['node', 'nvm'])
        command.assert_not_called()
        return result[0]['status']

    def test_read_only_verification(self):
        self.assertEqual(self.check(), 'passed')

    def test_wrong_default_not_repaired(self):
        alias = self.nvm / 'alias/default'
        alias.write_text('wrong\n')
        self.assertEqual(self.check(), 'failed')
        self.assertEqual(alias.read_text(), 'wrong\n')

    def test_modified_runtime_fails(self):
        (self.target / 'node').write_bytes(b'changed')
        self.assertEqual(self.check(), 'failed')

    def test_missing_manager_selection_fails(self):
        self.assertEqual(verify(self.home, self.tools, ['node'])[0]['status'], 'failed')
