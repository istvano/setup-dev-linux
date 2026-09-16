import hashlib
from pathlib import Path
from types import SimpleNamespace
import shutil
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'script'))
from workstation.artifacts import destination
from workstation.config import InputError
from workstation.sdkman_runtime import directory, install, metadata, verify


class SDKMANVerification(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.home = Path(temporary.name)
        self.manager = directory(self.home)
        self.manager.mkdir(parents=True)
        self.records = []
        for ident, paths in [('sdkman-cli', ['bin/sdkman-init.sh', 'src/sdkman-use.sh', 'contrib/completion']),
                             ('sdkman-native', ['libexec/version'])]:
            record = dict(id=ident, version='1', entrypoint='source/' + paths[0], files=[])
            for path in paths:
                record['files'].append(dict(path='source/' + path, kind='file',
                                           value=hashlib.sha256(b'fixture').hexdigest(), executable=False))
                target = destination(self.home, record) / 'source' / path
                target.parent.mkdir(parents=True, exist_ok=True)
                target.write_bytes(b'fixture')
                managed = self.manager / path
                managed.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(target, managed)
            self.records.append(record)
        for name in ('etc', 'var', 'ext', 'tmp', 'candidates'):
            (self.manager / name).mkdir()
        for path, content in metadata(self.records).items():
            target = self.manager / path
            target.write_text(content)
            target.chmod(0o600)
        self.lock_patch = patch('workstation.sdkman_runtime.manager_lock', return_value=self.records)
        self.lock_patch.start()
        self.addCleanup(self.lock_patch.stop)

    def check(self):
        with patch('subprocess.run') as execute:
            result = verify(self.home, ['sdkman'])
        execute.assert_not_called()
        return result[0]['status']

    def test_read_only_manager_verification(self):
        self.assertEqual(self.check(), 'passed')

    def test_changed_module_is_not_repaired(self):
        target = self.manager / 'src/sdkman-use.sh'
        target.write_text('changed')
        self.assertEqual(self.check(), 'failed')
        self.assertEqual(target.read_text(), 'changed')

    def test_modified_policy_fails(self):
        (self.manager / 'etc/config').write_text('sdkman_selfupdate_feature=true\n')
        self.assertEqual(self.check(), 'failed')

    def test_unreviewed_extension_fails(self):
        (self.manager / 'ext/sdkman-hook.sh').write_text('unexpected')
        self.assertEqual(self.check(), 'failed')

    def test_manager_code_symlink_fails(self):
        target = self.manager / 'src/sdkman-use.sh'
        target.unlink()
        target.symlink_to(destination(self.home, self.records[0]) / 'source/src/sdkman-use.sh')
        self.assertEqual(self.check(), 'failed')

    def test_candidate_state_does_not_change_manager_payload(self):
        (self.manager / 'candidates/local').mkdir()
        self.assertEqual(self.check(), 'passed')

    def test_changed_manager_install_refuses_before_download(self):
        (self.manager / 'src/sdkman-use.sh').write_text('changed')
        account = SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))
        with patch('os.geteuid', return_value=1000), patch('pwd.getpwuid', return_value=account), \
                patch('workstation.storage.preflight', return_value=([], 0)), \
                patch('workstation.sdkman_runtime.install_artifacts') as acquire:
            with self.assertRaises(InputError):
                install({'target': {'user': 'fixture'}})
        acquire.assert_not_called()

    def test_unselected_manager_has_no_check(self):
        self.assertEqual(verify(self.home, []), [])
