"""Behavioural tests for the file migration command."""
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'script'))

from workstation.migrate import (  # noqa: E402
    MigrateError, build_command, load_plan, parse_destination, pending_items)


class DestinationTest(unittest.TestCase):
    def test_host_becomes_rsync_destination(self):
        self.assertEqual(parse_destination('newbox', '/home/me'), 'newbox:/home/me/')

    def test_user_at_host_accepted(self):
        self.assertEqual(parse_destination('me@newbox', '/home/me'), 'me@newbox:/home/me/')

    def test_destination_carrying_a_path_is_rejected(self):
        with self.assertRaises(MigrateError):
            parse_destination('newbox:/srv/elsewhere', '/home/me')

    def test_option_like_destination_is_rejected(self):
        with self.assertRaises(MigrateError):
            parse_destination('--delete', '/home/me')


class PlanTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_absent_trees_are_reported_not_invented(self):
        (self.home / 'workspace').mkdir()
        plan = load_plan(ROOT, self.home)
        self.assertIn('workspace', plan['present'])
        self.assertIn('Documents', plan['absent'])

    def test_ordinary_copy_excludes_every_credential_path(self):
        (self.home / 'workspace').mkdir()
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, 'host:/home/me/')
        secrets = plan['manifest']['secrets']
        for path in list(secrets['trees']) + list(secrets['paths']):
            self.assertIn(f'--exclude={path}', command,
                          f'{path} must not travel in the ordinary copy')

    def test_ordinary_copy_excludes_regenerable_output(self):
        (self.home / 'workspace').mkdir()
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, 'host:/home/me/')
        for pattern in ('node_modules/', '.venv/', '__pycache__/'):
            self.assertIn(f'--exclude={pattern}', command)

    def test_secrets_copy_carries_only_credential_paths(self):
        (self.home / 'workspace').mkdir()
        (self.home / 'secure').mkdir()
        (self.home / '.ssh').mkdir()
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, 'host:/home/me/', secrets=True)
        self.assertTrue(any(c.endswith('/secure') for c in command))
        self.assertTrue(any(c.endswith('/.ssh') for c in command))
        self.assertFalse(any(c.endswith('/workspace') for c in command))


    def test_secrets_copy_never_overwrites_destination_authorized_keys(self):
        """Replacing authorized_keys on the destination revokes the key the
        migration is running over, locking the operator out mid-copy."""
        (self.home / '.ssh').mkdir()
        (self.home / '.ssh' / 'authorized_keys').write_text('source key\n')
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, 'host:/home/me/', secrets=True)
        self.assertIn('--exclude=.ssh/authorized_keys', command)

    def test_empty_home_refuses_rather_than_copying_nothing(self):
        plan = load_plan(ROOT, self.home)
        with self.assertRaises(MigrateError):
            build_command(plan, 'host:/home/me/')

    def test_dry_run_never_writes(self):
        (self.home / 'workspace').mkdir()
        plan = load_plan(ROOT, self.home)
        self.assertIn('--dry-run', build_command(plan, 'host:/home/me/', dry_run=True))
        self.assertNotIn('--dry-run', build_command(plan, 'host:/home/me/'))

    def test_copy_never_deletes_on_the_destination(self):
        (self.home / 'workspace').mkdir()
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, 'host:/home/me/')
        self.assertFalse([c for c in command if c.startswith('--delete')])


class PendingTest(unittest.TestCase):
    def test_outstanding_transfer_is_detected(self):
        self.assertEqual(pending_items('>f+++++++++ workspace/a.txt'), ['workspace/a.txt'])

    def test_unchanged_file_is_not_outstanding(self):
        self.assertEqual(pending_items('.f          workspace/a.txt'), [])

    def test_summary_lines_are_not_transfers(self):
        self.assertEqual(pending_items('sent 42 bytes\ntotal size is 42'), [])


@unittest.skipIf(shutil.which('rsync') is None, 'rsync is not installed')
class RoundTripTest(unittest.TestCase):
    """The copy and its completeness proof, exercised against a real rsync."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.target = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.addCleanup(shutil.rmtree, self.target, ignore_errors=True)
        workspace = self.home / 'workspace'
        (workspace / 'project' / 'node_modules' / 'left-pad').mkdir(parents=True)
        (workspace / 'project' / 'src.py').write_text('real work\n')
        (workspace / 'project' / 'node_modules' / 'left-pad' / 'index.js').write_text('x\n')
        (self.home / '.ssh').mkdir()
        (self.home / '.ssh' / 'id_ed25519').write_text('PRIVATE KEY\n')

    def copy(self, **kwargs):
        plan = load_plan(ROOT, self.home)
        command = build_command(plan, str(self.target) + '/', **kwargs)
        return subprocess.run(command, capture_output=True, text=True, check=True), plan

    def test_real_files_arrive_and_excluded_ones_do_not(self):
        self.copy()
        self.assertTrue((self.target / 'workspace/project/src.py').is_file())
        self.assertFalse((self.target / 'workspace/project/node_modules').exists(),
                         'regenerable output must not be copied')
        self.assertFalse((self.target / '.ssh').exists(),
                         'credentials must not travel in the ordinary copy')

    def test_second_pass_proves_completeness(self):
        self.copy()
        _, plan = self.copy(dry_run=True, itemize=True)
        verify = build_command(plan, str(self.target) + '/', dry_run=True, itemize=True)
        result = subprocess.run(verify, capture_output=True, text=True, check=True)
        self.assertEqual(pending_items(result.stdout), [],
                         'a complete copy must leave nothing outstanding')

    def test_incomplete_copy_is_detected(self):
        self.copy()
        (self.target / 'workspace/project/src.py').unlink()
        plan = load_plan(ROOT, self.home)
        verify = build_command(plan, str(self.target) + '/', dry_run=True, itemize=True)
        result = subprocess.run(verify, capture_output=True, text=True, check=True)
        self.assertTrue(pending_items(result.stdout),
                        'a missing file must be reported as outstanding')


if __name__ == '__main__':
    unittest.main()
