"""Per-user installer state, kept outside the clone.

The host profile choice must survive re-cloning the repository, `git clean -xfd`
and rebuilding the controller: losing it silently turns a headless re-run into a
desktop install. It lives at ${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/
state.json, read and written by one helper with the same safety checks.
"""
import json
import os
import shutil
import stat
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation import state  # noqa: E402
from workstation.config import InputError  # noqa: E402


class TempState(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        environment = patch.dict(os.environ, {'XDG_STATE_HOME': str(self.temp / 'xdg')})
        environment.start()
        self.addCleanup(environment.stop)
        self.file = self.temp / 'xdg/setup-dev-linux/state.json'


class LocationTest(TempState):
    def test_xdg_state_home_is_honoured(self):
        self.assertEqual(state.path(), self.file)

    def test_home_is_the_fallback(self):
        with patch.dict(os.environ, {'HOME': str(self.temp / 'home')}):
            del os.environ['XDG_STATE_HOME']
            self.assertEqual(state.path(),
                             self.temp / 'home/.local/state/setup-dev-linux/state.json')

    def test_a_relative_xdg_state_home_is_ignored(self):
        """The XDG spec says relative values are invalid and must be ignored."""
        with patch.dict(os.environ, {'XDG_STATE_HOME': 'relative', 'HOME': str(self.temp / 'h')}):
            self.assertEqual(state.path(), self.temp / 'h/.local/state/setup-dev-linux/state.json')

    def test_the_state_is_not_inside_the_clone(self):
        with patch.dict(os.environ, {'HOME': str(Path.home())}):
            del os.environ['XDG_STATE_HOME']
            self.assertFalse(state.path().is_relative_to(ROOT))


class ReadWriteTest(TempState):
    def test_missing_state_reads_as_absent(self):
        self.assertIsNone(state.get('profiles'))
        self.assertFalse(self.file.parent.exists(), 'a read creates nothing')

    def test_set_then_get(self):
        state.set('profiles', ['gpu', 'firewall'])
        self.assertEqual(state.get('profiles'), ['gpu', 'firewall'])

    def test_modes_are_private(self):
        state.set('profiles', ['gpu'])
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(self.file.parent.stat().st_mode), 0o700)

    def test_other_keys_are_preserved(self):
        """Task 5 adds firewall.allow_ssh to the same file."""
        state.set('other', {'kept': True})
        state.set('profiles', ['lab'])
        value = json.loads(self.file.read_text())
        self.assertEqual(value['other'], {'kept': True})
        self.assertEqual(value['profiles'], ['lab'])
        self.assertEqual(value['schema_version'], 1)

    def test_invalid_json_fails_closed(self):
        state.set('profiles', ['lab'])
        self.file.write_text('not json')
        with self.assertRaisesRegex(InputError, 'state-unreadable'):
            state.get('profiles')

    def test_a_group_or_world_readable_file_is_refused(self):
        state.set('profiles', ['lab'])
        self.file.chmod(0o644)
        for action in (lambda: state.get('profiles'), lambda: state.set('profiles', ['gpu'])):
            with self.assertRaisesRegex(InputError, 'state-unsafe'):
                action()

    def test_a_symlinked_file_is_refused_on_read_and_write(self):
        state.set('profiles', ['lab'])
        target = self.temp / 'elsewhere.json'
        target.write_text(self.file.read_text())
        target.chmod(0o600)
        self.file.unlink()
        self.file.symlink_to(target)
        for action in (lambda: state.get('profiles'), lambda: state.set('profiles', ['gpu'])):
            with self.assertRaisesRegex(InputError, 'state-unsafe'):
                action()
        self.assertIn('lab', target.read_text(), 'the symlink target is never written')

    def test_a_symlinked_directory_is_refused(self):
        real = self.temp / 'real'
        real.mkdir(mode=0o700)
        (self.temp / 'xdg').mkdir()
        (self.temp / 'xdg/setup-dev-linux').symlink_to(real)
        for action in (lambda: state.get('profiles'), lambda: state.set('profiles', ['gpu'])):
            with self.assertRaisesRegex(InputError, 'state-unsafe'):
                action()

    def test_a_file_owned_by_someone_else_is_refused(self):
        state.set('profiles', ['lab'])
        with patch('os.geteuid', return_value=os.geteuid() + 1):
            for action in (lambda: state.get('profiles'),
                           lambda: state.set('profiles', ['gpu'])):
                with self.assertRaisesRegex(InputError, 'state-unsafe'):
                    action()


if __name__ == '__main__':
    unittest.main()
