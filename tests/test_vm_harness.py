"""The VM harness drives apply the way the operator does (controller ruling RB11).

The guest cannot be booted here, so these tests pin what the harness asks the
guest to run: the clean cycle applies with explicit profiles and the handoff,
non-interactively on its first run and with no CLI profile list on the re-run;
the foundation suite keeps a controller-only path that never hands off. The
scripts themselves only build these commands and run them over SSH.
"""
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'vm'))
sys.path.insert(0, str(ROOT / 'script'))
import harness  # noqa: E402
from workstation import handoff, profiles  # noqa: E402


def flag(command, name):
    """The value after a flag, or None."""
    return command[command.index(name) + 1] if name in command else None


class CleanCycleTest(unittest.TestCase):
    def test_the_default_selection_is_every_host_profile_but_gpu(self):
        catalogue = profiles.load(ROOT)
        chosen = profiles.parse(harness.CLEAN_CYCLE_PROFILES, catalogue)
        self.assertEqual(set(chosen), set(profiles.available(catalogue)) - {'gpu'})

    def test_the_first_apply_hands_off_non_interactively_with_the_former_cli_set(self):
        command = harness.apply_command('/b', '/c.json', harness.CLEAN_CYCLE_PROFILES,
                                        handoff='first')
        self.assertEqual(command[:6], ['/b', 'apply', '--config', '/c.json', '--format', 'json'])
        self.assertEqual(flag(command, '--profiles'), harness.CLEAN_CYCLE_PROFILES)
        self.assertNotIn('--no-handoff', command)
        # The guest has no NVIDIA hardware, so no gpu-nvidia.
        self.assertEqual(flag(command, '--cli-profiles'), handoff.FORMER_CLI_PROFILES)
        self.assertEqual((flag(command, '--cli-git-name'), flag(command, '--cli-git-email')),
                         harness.GUEST_IDENTITY)
        self.assertTrue(handoff.valid_identity(harness.GUEST_IDENTITY))
        self.assertTrue(handoff.valid_cli_profiles(handoff.FORMER_CLI_PROFILES))

    def test_the_re_run_passes_no_cli_profiles_and_no_identity(self):
        """Review focus 1: the recorded choice holds; nothing can conflict with it."""
        command = harness.apply_command('/b', '/c.json', harness.CLEAN_CYCLE_PROFILES,
                                        handoff='again')
        self.assertNotIn('--no-handoff', command)
        for name in ('--cli-profiles', '--cli-git-name', '--cli-git-email'):
            self.assertNotIn(name, command)

    def test_a_host_only_apply_never_hands_off(self):
        command = harness.apply_command('/b', '/c.json', harness.CLEAN_CYCLE_PROFILES,
                                        handoff=None)
        self.assertIn('--no-handoff', command)
        self.assertNotIn('--cli-profiles', command)

    def test_ssh_stays_open_whenever_the_firewall_is_selected(self):
        """The harness reaches the guest over SSH; UFW must not close it."""
        with_firewall = harness.apply_command('/b', '/c.json', 'desktop,firewall', handoff=None)
        self.assertIn('--allow-ssh', with_firewall)
        without = harness.apply_command('/b', '/c.json', 'desktop', handoff=None)
        self.assertNotIn('--allow-ssh', without)

    def test_an_unknown_handoff_mode_is_refused(self):
        with self.assertRaises(ValueError):
            harness.apply_command('/b', '/c.json', 'desktop', handoff='always')


class ControllerOnlyTest(unittest.TestCase):
    def test_the_controller_path_selects_the_firewall_only_keeps_ssh_and_never_hands_off(self):
        args = harness.CONTROLLER_ONLY_ARGS
        self.assertEqual(args[0], 'apply')
        self.assertEqual(flag(args, '--profiles'), 'firewall')
        self.assertIn('--allow-ssh', args)
        self.assertIn('--no-handoff', args)

    def test_guest_foundation_uses_it(self):
        text = (ROOT / 'vm/guest-foundation.py').read_text()
        self.assertIn('harness.CONTROLLER_ONLY_ARGS', text)
        # The bare default-profile apply with the handoff is what RB11 removed.
        self.assertNotRegex(text, r"run\('install', expected=1\)\n\s+if not any")


class AptTest(unittest.TestCase):
    def test_clean_output_has_no_findings(self):
        text = ('Hit:1 http://archive.ubuntu.com/ubuntu resolute InRelease\n'
                'Get:2 https://downloads.claude.ai/claude-desktop stable InRelease\n'
                'Reading package lists...\n')
        self.assertEqual(harness.apt_findings(text), [])

    def test_warnings_errors_and_a_signed_by_conflict_are_findings(self):
        text = ('Hit:1 http://archive.ubuntu.com/ubuntu resolute InRelease\n'
                'E: Conflicting values set for option Signed-By regarding source '
                'https://example.invalid/ stable: /a.asc != /b.asc\n'
                'W: Target Packages is configured multiple times\n'
                'N: a notice is not a finding\n')
        self.assertEqual(len(harness.apt_findings(text)), 2)


class ReportTest(unittest.TestCase):
    def test_a_passed_check_is_found_by_id(self):
        report = {'checks': [{'id': 'handoff', 'status': 'passed', 'reason': 'x'}]}
        self.assertTrue(harness.check_passed(report, 'handoff'))
        self.assertFalse(harness.check_passed(report, 'cli:verify'))
        self.assertFalse(harness.check_passed(
            {'checks': [{'id': 'handoff', 'status': 'failed', 'reason': 'x'}]}, 'handoff'))


class GuestFileListTest(unittest.TestCase):
    """Both drivers copy an explicit file list into the guest; the module must be on it."""

    def test_both_drivers_copy_the_harness_module(self):
        for driver in ('script/test-manifest-vm', 'script/test-vm'):
            self.assertRegex((ROOT / driver).read_text(), r"'vm/harness\.py'", driver)

    def test_the_clean_cycle_runs_the_fixture_with_the_handoff(self):
        text = (ROOT / 'script/test-manifest-vm').read_text()
        self.assertIn('--handoff first', text)
        self.assertIn('--handoff again', text)
        self.assertTrue(re.search(r"--skip-handoff", text))


if __name__ == '__main__':
    unittest.main()
