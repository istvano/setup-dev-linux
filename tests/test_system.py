"""System group membership.

Installing docker is not the same as being able to use it: the package creates
the group, something has to put the operator in it, and the membership only
takes effect in a session started afterwards. These three states need different
actions, so verification must tell them apart rather than collapse them into
pass or fail.
"""
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))

from workstation import system  # noqa: E402
from workstation.system import declared_groups, manifest, verify  # noqa: E402


def summary(checks):
    return [c for c in checks if c['id'] == 'system-groups'][0]


def entry(checks, name='group:docker'):
    return [c for c in checks if c['id'] == name][0]


class ManifestTest(unittest.TestCase):
    def test_the_real_manifest_declares_the_docker_group(self):
        groups = [g['group'] for g in manifest(ROOT)['user_groups']]
        self.assertIn('docker', groups)

    def test_each_declaration_says_what_it_is_for_and_when_it_takes_effect(self):
        for record in manifest(ROOT)['user_groups']:
            self.assertTrue(record['reason'])
            self.assertTrue(record['effective_after'])
            self.assertTrue(record['requires_manifest_group'])

    def test_a_group_is_only_declared_when_its_manifest_group_is_selected(self):
        self.assertEqual(declared_groups(ROOT, groups=['core']), [])
        self.assertTrue(declared_groups(ROOT, groups=['containers']))


class VerificationTest(unittest.TestCase):
    """The three states, each reported differently."""

    def check(self, members, session, reachable=True, primary=None):
        with patch.object(system, 'group_members', return_value=members), \
             patch.object(system, 'session_groups', return_value=session), \
             patch.object(system, 'primary_group', return_value=primary), \
             patch.object(system, 'socket_reachable', return_value=reachable):
            return verify('operator', ROOT, groups=['containers'])

    def test_member_and_effective_passes(self):
        checks = self.check({'operator'}, {'docker'})
        self.assertEqual(entry(checks)['status'], 'passed')
        self.assertEqual(summary(checks)['status'], 'passed')

    def test_not_a_member_fails(self):
        """The install did not finish; this is the state a fresh machine was in."""
        checks = self.check(set(), set())
        self.assertEqual(entry(checks)['status'], 'failed')
        self.assertEqual(entry(checks)['reason'], 'user-is-not-a-member')
        self.assertEqual(summary(checks)['status'], 'failed')

    def test_a_stale_session_is_deferred_not_failed(self):
        """Granted, but this session predates it. Logging out fixes it; nothing
        about the installation is wrong."""
        checks = self.check({'operator'}, set())
        self.assertEqual(entry(checks)['status'], 'deferred')
        self.assertIn('fresh-login', entry(checks)['reason'])
        self.assertEqual(summary(checks)['status'], 'passed',
                         'a stale session is not an installation failure')

    def test_a_missing_group_fails(self):
        checks = self.check(None, set())
        self.assertEqual(entry(checks)['reason'], 'group-does-not-exist')

    def test_membership_without_a_working_socket_fails(self):
        """Being in the group but refused by the daemon is a real fault, not a
        stale session."""
        checks = self.check({'operator'}, {'docker'}, reachable=False)
        self.assertEqual(entry(checks)['status'], 'failed')
        self.assertIn('refused', entry(checks)['reason'])

    def test_docker_absent_is_deferred(self):
        checks = self.check({'operator'}, {'docker'}, reachable=None)
        self.assertEqual(entry(checks)['status'], 'deferred')
        self.assertEqual(entry(checks)['reason'], 'docker-not-installed')

    def test_a_primary_group_counts_as_membership(self):
        """getgrnam lists secondary members only; a primary group is still
        membership."""
        checks = self.check(set(), {'docker'}, primary='docker')
        self.assertEqual(entry(checks)['status'], 'passed')

    def test_nothing_is_checked_when_the_group_is_not_selected(self):
        with patch.object(system, 'group_members', return_value=set()):
            self.assertEqual(verify('operator', ROOT, groups=['core']), [])


class PlaybookTest(unittest.TestCase):
    def test_the_playbook_appends_rather_than_replaces(self):
        """Without append, the task would remove every membership the
        distribution granted at install time."""
        text = (ROOT / 'ansible/system-groups.yml').read_text()
        self.assertIn('append: true', text)

    def test_the_playbook_confirms_the_group_database(self):
        text = (ROOT / 'ansible/system-groups.yml').read_text()
        self.assertIn('getent', text)


if __name__ == '__main__':
    unittest.main()
