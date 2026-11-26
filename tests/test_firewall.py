"""The firewall stage: UFW (deny incoming, allow outgoing, SSH only when chosen) and
OpenSnitch in allow mode, plus the persisted SSH choice and the read-only verifier."""
import contextlib
import io
import json
import os
import re
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation import controller, firewall, profiles, state  # noqa: E402
from workstation.cli import main  # noqa: E402
from workstation.config import InputError  # noqa: E402

PLAYBOOK = (ROOT / 'ansible/firewall.yml').read_text()

ACTIVE = """Status: active
Logging: on (low)
Default: deny (incoming), allow (outgoing), disabled (routed)
New profiles: skip
"""
SSH_RULES = """
To                         Action      From
--                         ------      ----
OpenSSH                    ALLOW IN    Anywhere
OpenSSH (v6)               ALLOW IN    Anywhere (v6)
"""
PORT_RULE = """
To                         Action      From
--                         ------      ----
22/tcp (OpenSSH)           ALLOW IN    Anywhere
"""
INACTIVE = 'Status: inactive\n'


class TempState(unittest.TestCase):
    def setUp(self):
        self.temp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.temp, ignore_errors=True)
        environment = patch.dict(os.environ, {'XDG_STATE_HOME': str(self.temp)})
        environment.start()
        self.addCleanup(environment.stop)


class PlaybookTest(unittest.TestCase):
    def test_the_ufw_defaults_are_exact(self):
        self.assertIn('[/usr/sbin/ufw, default, deny, incoming]', PLAYBOOK)
        self.assertIn('[/usr/sbin/ufw, default, allow, outgoing]', PLAYBOOK)
        self.assertNotIn('allow, incoming', PLAYBOOK)
        self.assertNotIn('deny, outgoing', PLAYBOOK)

    def test_ufw_is_enabled_without_a_prompt(self):
        self.assertIn('[/usr/sbin/ufw, --force, enable]', PLAYBOOK)

    def test_rules_are_added_before_the_firewall_is_enabled(self):
        self.assertLess(PLAYBOOK.index('allow, OpenSSH]'), PLAYBOOK.index('--force, enable'))

    def task(self, name):
        start = PLAYBOOK.index('- name: ' + name)
        end = PLAYBOOK.find('\n    - name:', start + 1)
        return PLAYBOOK[start:end if end != -1 else None]

    def test_ssh_is_allowed_only_when_chosen_and_removed_when_not(self):
        allow = self.task('Allow incoming SSH when chosen')
        self.assertIn('allow, OpenSSH]', allow)
        self.assertIn('- firewall_allow_ssh | default(false) | bool', allow)
        remove = self.task('Remove the SSH rule when it is not chosen')
        self.assertIn('delete, allow, OpenSSH]', remove)
        self.assertIn('- not (firewall_allow_ssh | default(false) | bool)', remove)

    def test_the_choice_defaults_to_no_ssh(self):
        self.assertIn('firewall_allow_ssh | default(false)', PLAYBOOK)

    def test_opensnitch_is_installed_from_the_ubuntu_archive(self):
        for package in firewall.PACKAGES:
            self.assertIn(package, PLAYBOOK)
        self.assertIn('install_recommends: false', PLAYBOOK,
                      'the recommended UI must not reach a headless host')

    def test_the_ui_belongs_to_the_desktop_set_only(self):
        self.assertEqual(firewall.UI_PACKAGE, 'python3-opensnitch-ui')
        self.assertNotIn(firewall.UI_PACKAGE, firewall.PACKAGES)
        index = PLAYBOOK.index(firewall.UI_PACKAGE)
        self.assertIn('host_desktop', PLAYBOOK[index - 300:index + 300])

    def test_opensnitch_allow_mode_is_seeded_once_not_enforced(self):
        self.assertIn('/etc/opensnitchd/default-config.json', PLAYBOOK)
        self.assertEqual(firewall.OPENSNITCH_CONFIG, '/etc/opensnitchd/default-config.json')
        seed = self.task('Seed OpenSnitch allow mode on first install')
        self.assertIn('"DefaultAction"', seed)
        self.assertIn('\\1"allow"', seed)
        self.assertIn('firewall_seed_opensnitch | default(false) | bool', seed)
        self.assertEqual(PLAYBOOK.count('ansible.builtin.replace:'), 1, 'no unconditional rewrite remains')

    def test_the_service_is_enabled_and_started(self):
        self.assertRegex(PLAYBOOK, r'name: opensnitch\n\s+enabled: true\n\s+state: started')

    def test_nothing_runs_as_root_by_default(self):
        self.assertIn('become: false', PLAYBOOK.split('tasks:')[0])


class ParseTest(unittest.TestCase):
    def test_active_with_defaults_and_ssh(self):
        parsed = firewall.parse_ufw(ACTIVE + SSH_RULES)
        self.assertEqual(parsed, {'active': True, 'incoming': 'deny', 'outgoing': 'allow',
                                  'ssh': True})

    def test_active_without_ssh(self):
        self.assertFalse(firewall.parse_ufw(ACTIVE)['ssh'])

    def test_port_rule_with_the_profile_name_counts_as_the_openssh_rule(self):
        self.assertTrue(firewall.parse_ufw(ACTIVE + PORT_RULE)['ssh'])

    def test_inactive(self):
        parsed = firewall.parse_ufw(INACTIVE)
        self.assertFalse(parsed['active'])
        self.assertIsNone(parsed['incoming'])
        self.assertIsNone(parsed['outgoing'])

    def test_permissive_defaults(self):
        parsed = firewall.parse_ufw(ACTIVE.replace('deny (incoming), allow (outgoing)',
                                                   'allow (incoming), deny (outgoing)'))
        self.assertEqual((parsed['incoming'], parsed['outgoing']), ('allow', 'deny'))


def runner(ufw=ACTIVE, config=None, installed=('ufw', 'opensnitch'), active=True,
           ufw_rc=0, ui=False):
    """A fake command runner keyed on the program being asked."""
    def run(argv):
        if argv[0] == 'dpkg-query':
            name = argv[-1]
            ok = name in installed or (name == firewall.UI_PACKAGE and ui)
            return (0, 'install ok installed') if ok else (1, '')
        if argv[:2] == ['sudo', '-n'] and 'ufw' in argv[2]:
            return ufw_rc, ufw
        if argv[:2] == ['systemctl', 'is-active']:
            return (0, 'active\n') if active else (3, 'inactive\n')
        raise AssertionError(argv)
    return run


def by_id(checks):
    return {c['id']: c for c in checks}


class VerifyTest(TempState):
    def setUp(self):
        super().setUp()
        self.config = self.temp / 'default-config.json'
        self.config.write_text('{"DefaultAction": "allow"}')

    def verify(self, allow_ssh=False, desktop=False, which=lambda name: None, **kwargs):
        return by_id(firewall.verify(allow_ssh, desktop=desktop, which=which,
                                     run=runner(**kwargs), config_path=self.config))

    def test_a_correct_host_passes_every_check(self):
        checks = self.verify()
        for name in ('ufw-active', 'ufw-default-incoming', 'ufw-default-outgoing', 'ufw-ssh',
                     'opensnitch-installed', 'opensnitch-running'):
            self.assertEqual(checks['firewall:' + name]['status'], 'passed', name)

    def test_inactive_ufw_fails(self):
        checks = self.verify(ufw=INACTIVE)
        self.assertEqual(checks['firewall:ufw-active']['status'], 'failed')

    def test_wrong_defaults_fail_individually(self):
        checks = self.verify(ufw=ACTIVE.replace('deny (incoming), allow (outgoing)',
                                                'allow (incoming), deny (outgoing)'))
        self.assertEqual(checks['firewall:ufw-default-incoming']['status'], 'failed')
        self.assertEqual(checks['firewall:ufw-default-outgoing']['status'], 'failed')

    def test_ssh_chosen_requires_the_rule(self):
        self.assertEqual(self.verify(allow_ssh=True)['firewall:ufw-ssh']['status'], 'failed')
        self.assertEqual(self.verify(allow_ssh=True, ufw=ACTIVE + SSH_RULES)
                         ['firewall:ufw-ssh']['status'], 'passed')

    def test_ssh_not_chosen_forbids_the_rule(self):
        checks = self.verify(allow_ssh=False, ufw=ACTIVE + SSH_RULES)
        self.assertEqual(checks['firewall:ufw-ssh']['status'], 'failed')
        self.assertIn('not-chosen', checks['firewall:ufw-ssh']['reason'])

    def test_ufw_status_needing_sudo_is_deferred_not_passed(self):
        checks = self.verify(ufw='', ufw_rc=1)
        self.assertEqual(checks['firewall:ufw-status']['status'], 'deferred')
        self.assertNotIn('firewall:ufw-active', checks)

    def test_missing_packages_fail(self):
        checks = self.verify(installed=())
        self.assertEqual(checks['firewall:ufw-installed']['status'], 'failed')
        self.assertEqual(checks['firewall:opensnitch-installed']['status'], 'failed')

    def test_stopped_opensnitch_fails(self):
        self.assertEqual(self.verify(active=False)['firewall:opensnitch-running']['status'],
                         'failed')

    def test_the_daemon_mode_is_a_notice_never_a_failure(self):
        for action in ('allow', 'deny'):
            self.config.write_text('{"DefaultAction": "%s"}' % action)
            check = self.verify()['firewall:opensnitch-daemon-mode']
            self.assertEqual(check['status'], 'notice')
            self.assertIn(action, check['reason'])

    def test_an_unreadable_config_is_a_notice_too(self):
        self.config.write_text('{')
        self.assertEqual(self.verify()['firewall:opensnitch-daemon-mode']['status'], 'notice')

    def test_the_ui_mode_is_reported_only_with_the_desktop_set(self):
        self.assertNotIn('firewall:opensnitch-ui-mode', self.verify())
        settings = self.temp / firewall.UI_SETTINGS
        settings.parent.mkdir(parents=True)
        settings.write_text('[global]\ndefault_action=0\n')
        checks = by_id(firewall.verify(False, desktop=True, which=lambda n: None,
                                       run=runner(ui=True), config_path=self.config,
                                       home=self.temp))
        self.assertEqual(checks['firewall:opensnitch-ui-mode']['status'], 'notice')
        self.assertIn('deny', checks['firewall:opensnitch-ui-mode']['reason'])

    def test_the_ui_is_demanded_only_with_the_desktop_set(self):
        self.assertNotIn('firewall:opensnitch-ui', self.verify())
        self.assertEqual(self.verify(desktop=True)['firewall:opensnitch-ui']['status'], 'failed')
        self.assertEqual(self.verify(desktop=True, ui=True)['firewall:opensnitch-ui']['status'],
                         'passed')

    def test_docker_bypass_is_noted_only_when_docker_is_installed(self):
        self.assertNotIn('firewall:docker-bypass', self.verify())
        checks = self.verify(which=lambda name: '/usr/bin/docker' if name == 'docker' else None)
        note = checks['firewall:docker-bypass']
        self.assertEqual(note['status'], 'notice')
        self.assertIn('bypass', note['reason'])
        self.assertIn('ufw', note['reason'])


class SshChoiceTest(TempState):
    def test_default_is_false(self):
        self.assertEqual(firewall.resolve_allow_ssh(None), (False, 'default'))

    def test_the_flag_wins_and_is_recorded_by_the_stage(self):
        self.assertEqual(firewall.resolve_allow_ssh(True), (True, 'explicit'))
        firewall.record_allow_ssh(True)
        self.assertEqual(state.get('firewall'), {'allow_ssh': True})

    def test_a_recorded_choice_holds_without_the_flag(self):
        firewall.record_allow_ssh(True)
        self.assertEqual(firewall.resolve_allow_ssh(None), (True, 'recorded'))

    def test_no_allow_ssh_overrides_a_recorded_true(self):
        firewall.record_allow_ssh(True)
        self.assertEqual(firewall.resolve_allow_ssh(False), (False, 'explicit'))
        firewall.record_allow_ssh(False)
        self.assertEqual(firewall.resolve_allow_ssh(None), (False, 'recorded'))

    def test_recording_keeps_the_profile_choice(self):
        state.set('profiles', ['gpu'])
        firewall.record_allow_ssh(True)
        self.assertEqual(state.get('profiles'), ['gpu'])

    def test_a_malformed_record_is_an_error_not_a_silent_default(self):
        state.set('firewall', {'allow_ssh': 'yes'})
        with self.assertRaisesRegex(InputError, 'recorded-firewall-unreadable'):
            firewall.resolve_allow_ssh(None)
        state.set('firewall', 'oops')
        with self.assertRaisesRegex(InputError, 'recorded-firewall-unreadable'):
            firewall.resolve_allow_ssh(None)

    def test_an_unsafe_state_file_is_an_error(self):
        state.set('profiles', ['gpu'])
        state.path().chmod(0o644)
        with self.assertRaisesRegex(InputError, 'recorded-firewall-unreadable'):
            firewall.resolve_allow_ssh(None)

    def test_record_selection_records_the_choice_only_when_explicit(self):
        selection = profiles.resolve(['firewall'], profiles.load())
        controller.record_selection(selection)
        self.assertIsNone(state.get('firewall'))
        controller.record_selection(selection, allow_ssh=True)
        self.assertEqual(state.get('firewall'), {'allow_ssh': True})
        self.assertEqual(state.get('profiles'), ['firewall'])

    def test_record_selection_ignores_the_choice_without_the_firewall(self):
        selection = profiles.resolve(['gpu'], profiles.load())
        controller.record_selection(selection, allow_ssh=True)
        self.assertIsNone(state.get('firewall'))


class UiSeedTest(TempState):
    def setUp(self):
        super().setUp()
        self.file = self.temp / 'home/.config/opensnitch/settings.conf'

    def test_an_absent_file_is_created_with_allow(self):
        self.assertEqual(firewall.seed_ui_settings(self.file), 'created')
        self.assertEqual(self.file.read_text(), '[global]\ndefault_action=1\n')

    def test_an_existing_value_is_never_rewritten(self):
        self.file.parent.mkdir(parents=True)
        for value in ('0', '1', '2'):
            text = f'[global]\ndefault_timeout=30\ndefault_action={value}\n'
            self.file.write_text(text)
            self.assertEqual(firewall.seed_ui_settings(self.file), 'kept')
            self.assertEqual(self.file.read_text(), text)
        self.assertEqual(list(self.file.parent.glob('*.bak-*')), [])

    def test_a_missing_key_is_added_and_the_rest_kept_after_a_backup(self):
        self.file.parent.mkdir(parents=True)
        original = '[global]\ndefault_timeout=30\n\n[other]\ndefault_action=0\nx=y\n'
        self.file.write_text(original)
        self.assertEqual(firewall.seed_ui_settings(self.file, now=lambda: 7), 'added')
        self.assertEqual(self.file.read_text(),
                         '[global]\ndefault_action=1\ndefault_timeout=30\n\n'
                         '[other]\ndefault_action=0\nx=y\n')
        self.assertEqual((self.file.parent / 'settings.conf.bak-7').read_text(), original)

    def test_a_file_without_a_global_section_gets_one(self):
        self.file.parent.mkdir(parents=True)
        self.file.write_text('[other]\nx=y\n')
        firewall.seed_ui_settings(self.file)
        self.assertEqual(self.file.read_text(), '[other]\nx=y\n\n[global]\ndefault_action=1\n')

    def test_the_same_key_in_another_section_is_not_the_global_one(self):
        self.assertEqual(firewall.ui_mode(self.file), 'unset')
        self.file.parent.mkdir(parents=True)
        self.file.write_text('[other]\ndefault_action=0\n')
        self.assertEqual(firewall.ui_mode(self.file), 'unset')


class SeedOnceTest(TempState):
    """RB13: first-install default, never enforced on a re-run."""

    def setUp(self):
        super().setUp()
        self.home = self.temp / 'home'
        self.home.mkdir()
        patcher = patch('workstation.controller.pwd.getpwuid')
        patcher.start().return_value.pw_dir = str(self.home)
        self.addCleanup(patcher.stop)
        self.selection = profiles.resolve(['desktop', 'firewall'], profiles.load())
        self.ui = self.home / firewall.UI_SETTINGS

    def stage(self):
        ran = []
        controller.apply_firewall_stage(lambda b, t: ran.append(b), {}, self.selection)
        return ran

    def test_first_run_seeds_and_records(self):
        self.assertFalse(firewall.opensnitch_seeded())
        self.stage()
        self.assertEqual(self.ui.read_text(), '[global]\ndefault_action=1\n')
        self.assertTrue(firewall.opensnitch_seeded())
        self.assertTrue(firewall.opensnitch_ui_seeded())

    def test_an_operator_set_deny_survives_a_re_run(self):
        self.stage()
        self.ui.write_text('[global]\ndefault_action=0\n')  # the operator switches to deny
        self.stage()
        self.assertEqual(self.ui.read_text(), '[global]\ndefault_action=0\n')
        self.assertEqual(list(self.ui.parent.glob('*.bak-*')), [])

    def test_a_second_run_does_not_seed_the_ui_again(self):
        self.stage()
        self.ui.unlink()
        self.stage()
        self.assertFalse(self.ui.exists())

    def test_the_playbook_is_told_to_seed_only_before_the_first_run(self):
        source = (ROOT / 'script/workstation/controller.py').read_text()
        self.assertIn("'firewall_seed_opensnitch': seed_opensnitch", source)
        self.assertIn('seed_opensnitch = not firewall.opensnitch_seeded()', source)

    def test_headless_seeds_no_ui_file(self):
        self.selection = profiles.resolve(['firewall'], profiles.load())
        self.stage()
        self.assertFalse(self.ui.exists())
        self.assertTrue(firewall.opensnitch_seeded())
        self.assertFalse(firewall.opensnitch_ui_seeded())

    def test_a_later_desktop_run_seeds_the_ui_once(self):
        self.selection = profiles.resolve(['firewall'], profiles.load())
        self.stage()
        self.selection = profiles.resolve(['desktop', 'firewall'], profiles.load())
        self.stage()
        self.assertTrue(self.ui.exists())


class SshWarningTest(unittest.TestCase):
    def test_notice_only_when_connected_over_ssh_and_ssh_is_closed(self):
        over_ssh = {'SSH_CONNECTION': '1.2.3.4 5 6.7.8.9 22'}
        notice = firewall.ssh_notice(False, over_ssh)
        self.assertEqual(notice['status'], 'notice')
        self.assertIn('--allow-ssh', notice['reason'])
        self.assertIsNone(firewall.ssh_notice(True, over_ssh))
        self.assertIsNone(firewall.ssh_notice(False, {}))
        self.assertIsNone(firewall.ssh_notice(False, {'SSH_CONNECTION': ''}))


def context():
    import getpass
    return {'config': {'example_only': False, 'target': {'user': getpass.getuser()}},
            'provenance': {}, 'selected': [], 'entries': {}, 'approved': {}}


class CliTest(TempState):
    def run_cli(self, args):
        stdout = io.StringIO()
        targets = {
            'workstation.cli.load_context': context(),
            'workstation.storage.preflight': ([], 0),
            'workstation.host.check_prerequisites': ([], 0),
            'workstation.packages.verify_packages': [],
            'workstation.system.verify': [],
            'workstation.delivery.verify': [],
            'workstation.desktop.verify': [],
            'workstation.plugins.verify': [],
            'workstation.firewall.verify': [{'id': 'firewall:ufw-active', 'status': 'passed',
                                             'reason': 'fixture'}],
            'workstation.controller.apply_foundation': {
                'id': 'controller-foundation', 'status': 'passed', 'reason': 'fixture'},
            # The handoff has its own tests (tests/test_handoff.py).
            'workstation.handoff.run_handoff': 0,
            'workstation.handoff.verify_cli': [],
            'workstation.handoff.first_run_hint': None,
        }
        with contextlib.ExitStack() as stack:
            self.mocks = {t: stack.enter_context(patch(t, return_value=v))
                          for t, v in targets.items()}
            # os.geteuid stays real: the state file's owner check uses it.
            stack.enter_context(contextlib.redirect_stdout(stdout))
            self.stderr = io.StringIO()
            stack.enter_context(contextlib.redirect_stderr(self.stderr))
            code = main(args)
        return code, stdout.getvalue()

    def apply_kwargs(self):
        return self.mocks['workstation.controller.apply_foundation'].call_args.kwargs

    def run_stderr(self, args, environ):
        with patch.dict(os.environ, environ):
            if not environ:
                os.environ.pop('SSH_CONNECTION', None)
            code, out = self.run_cli(args)
        return out, self.stderr.getvalue()

    def test_the_ssh_warning_appears_only_over_ssh_with_ssh_closed(self):
        args = ['apply', '--config', 'x.json', '--profiles', 'firewall', '--format', 'json']
        env = {'SSH_CONNECTION': '1.2.3.4 5 6.7.8.9 22'}
        out, err = self.run_stderr(args, env)
        self.assertIn('--allow-ssh', err)
        self.assertIn('firewall:ssh-closing', out)
        out, err = self.run_stderr(args + ['--allow-ssh'], env)
        self.assertNotIn('warning', err)
        self.assertNotIn('firewall:ssh-closing', out)
        out, err = self.run_stderr(args, {})
        self.assertNotIn('warning', err)
        self.assertNotIn('firewall:ssh-closing', out)

    def test_allow_ssh_is_passed_to_the_apply(self):
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall', '--allow-ssh'])
        self.assertTrue(self.apply_kwargs()['allow_ssh'])
        self.assertTrue(self.apply_kwargs()['allow_ssh_explicit'])

    def test_the_choice_made_once_holds_on_the_next_run(self):
        """Review focus 3: no silent SSH lock-out when the flag is omitted later."""
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall', '--allow-ssh'])
        firewall.record_allow_ssh(True)  # what the record stage does with the flag
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall'])
        self.assertTrue(self.apply_kwargs()['allow_ssh'])
        self.assertFalse(self.apply_kwargs()['allow_ssh_explicit'])

    def test_no_allow_ssh_turns_it_off(self):
        firewall.record_allow_ssh(True)
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall', '--no-allow-ssh'])
        self.assertFalse(self.apply_kwargs()['allow_ssh'])
        self.assertTrue(self.apply_kwargs()['allow_ssh_explicit'])

    def test_both_flags_together_are_invalid(self):
        code, _ = self.run_cli(['apply', '--config', 'x.json', '--allow-ssh', '--no-allow-ssh'])
        self.assertEqual(code, 2)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_the_default_is_no_ssh(self):
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall'])
        self.assertFalse(self.apply_kwargs()['allow_ssh'])

    def test_an_unreadable_record_stops_apply_before_anything_changes(self):
        state.set('firewall', {'allow_ssh': 3})
        code, out = self.run_cli(['apply', '--config', 'x.json', '--profiles', 'firewall'])
        self.assertEqual(code, 2)
        self.assertIn('recorded-firewall-unreadable', out)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_without_the_firewall_profile_the_choice_is_not_consulted(self):
        state.set('firewall', {'allow_ssh': 3})
        self.run_cli(['apply', '--config', 'x.json', '--profiles', 'gpu'])
        self.mocks['workstation.controller.apply_foundation'].assert_called_once()

    def test_verify_runs_the_firewall_checks_with_the_recorded_choice(self):
        firewall.record_allow_ssh(True)
        _, out = self.run_cli(['verify', '--config', 'x.json', '--format', 'json',
                               '--profiles', 'firewall'])
        verify = self.mocks['workstation.firewall.verify']
        self.assertEqual(verify.call_args.args[0], True)
        ids = {c['id'] for c in json.loads(out)['checks']}
        self.assertIn('firewall:ufw-active', ids)
        self.assertIn('firewall:ssh-choice', ids)

    def test_verify_passes_the_desktop_flag(self):
        self.run_cli(['verify', '--config', 'x.json', '--profiles', 'firewall,gpu'])
        self.assertFalse(self.mocks['workstation.firewall.verify'].call_args.kwargs['desktop'])
        self.run_cli(['verify', '--config', 'x.json'])
        self.assertTrue(self.mocks['workstation.firewall.verify'].call_args.kwargs['desktop'])

    def test_verify_without_the_firewall_profile_runs_no_firewall_check(self):
        self.run_cli(['verify', '--config', 'x.json', '--profiles', 'gpu'])
        self.mocks['workstation.firewall.verify'].assert_not_called()

    def test_the_plan_lists_the_firewall_stage_as_planned(self):
        _, out = self.run_cli(['plan', '--config', 'x.json', '--format', 'json',
                               '--profiles', 'firewall'])
        checks = {c['id']: c for c in json.loads(out)['checks']}
        self.assertEqual(checks['stage:firewall'], {'id': 'stage:firewall', 'status': 'planned',
                                                    'reason': 'firewall.yml'})


class StageTest(TempState):
    def test_the_hook_runs_the_playbook(self):
        ran = []
        controller.apply_firewall_stage(lambda books, timeout: ran.append((books, timeout)), {})
        self.assertEqual(ran, [(['firewall.yml'], 1800)])

    def test_seeding_flags_alone_leave_the_ssh_choice_unrecorded(self):
        firewall.record_flag('opensnitch_seeded')
        self.assertEqual(firewall.resolve_allow_ssh(None), (False, 'default'))
        firewall.record_allow_ssh(True)
        self.assertEqual(state.get('firewall'), {'allow_ssh': True, 'opensnitch_seeded': True})

    def test_the_stage_follows_the_packages(self):
        selection = profiles.resolve(['firewall'], profiles.load())
        names = [s for s, _, _ in controller.host_stages(selection)]
        self.assertEqual(names[-1], 'firewall')
        self.assertLess(names.index('packages'), names.index('firewall'))

    def test_the_playbook_receives_the_choice(self):
        source = (ROOT / 'script/workstation/controller.py').read_text()
        self.assertIn("'firewall_allow_ssh'", source)
        self.assertIn("'host_desktop'", source)


if __name__ == '__main__':
    unittest.main()
