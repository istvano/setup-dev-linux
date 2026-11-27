"""The sudo password apply asks for once and hands to every ansible-playbook run.

sudo and ansible-playbook are mocked here; the real sudo-rs and ansible-core
behaviour is the manual check in docs/TESTING.md. The pipe is real: the mocked
ansible-playbook reads the standard input it is given, as the real one does.
"""
import contextlib
import io
import json
import os
from pathlib import Path
import pwd
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation import become  # noqa: E402
from workstation.become import BecomeError  # noqa: E402
from workstation.cli import main  # noqa: E402
from workstation.controller import apply_foundation  # noqa: E402

PASSWORD = 'PRIVATE-SENTINEL-sudo-pw'


class Terminal:
    def __init__(self, tty):
        self.tty = tty

    def isatty(self):
        return self.tty


class FakeSudo:
    """sudo -n fails unless passwordless; sudo -S accepts only `accepted`."""

    def __init__(self, passwordless=False, accepted=PASSWORD):
        self.passwordless, self.accepted, self.calls = passwordless, accepted, []

    def __call__(self, argv, **kwargs):
        self.calls.append((argv, kwargs))
        if '-n' in argv:
            code = 0 if self.passwordless else 1
        else:
            code = 0 if kwargs.get('input') == self.accepted + '\n' else 1
        return subprocess.CompletedProcess(argv, code)


class Acquire(unittest.TestCase):
    def acquire(self, sudo, answers=(), tty=True):
        answers = list(answers)
        self.asked = []

        def ask(prompt):
            self.asked.append(prompt)
            if not answers:
                raise EOFError
            return answers.pop(0)
        self.err = io.StringIO()
        return become.acquire(stdin=Terminal(tty), ask=ask, run=sudo, err=self.err)

    def test_passwordless_sudo_asks_nothing(self):
        sudo = FakeSudo(passwordless=True)
        self.assertIsNone(self.acquire(sudo, tty=False))
        self.assertEqual(self.asked, [])
        self.assertEqual([c[0] for c in sudo.calls], [[become.SUDO, '-n', 'true']])

    def test_without_a_terminal_it_fails_closed_and_asks_nothing(self):
        sudo = FakeSudo()
        with self.assertRaisesRegex(BecomeError, '^sudo-password-needs-terminal$'):
            self.acquire(sudo, answers=[PASSWORD], tty=False)
        self.assertEqual(self.asked, [])
        self.assertEqual(len(sudo.calls), 1)  # only the sudo -n probe

    def test_a_correct_password_is_validated_on_standard_input(self):
        sudo = FakeSudo()
        self.assertEqual(self.acquire(sudo, answers=[PASSWORD]), PASSWORD)
        user = pwd.getpwuid(os.geteuid()).pw_name
        self.assertEqual(self.asked, [f'[setup-dev-linux] sudo password for {user}: '])
        argv, kwargs = sudo.calls[-1]
        self.assertEqual(argv, [become.SUDO, '-S', '-k', '-p', '', 'true'])
        self.assertNotIn(PASSWORD, ' '.join(argv))
        self.assertNotIn('env', kwargs)

    def test_a_wrong_password_is_retried(self):
        sudo = FakeSudo()
        self.assertEqual(self.acquire(sudo, answers=['wrong', PASSWORD]), PASSWORD)
        self.assertEqual(len(self.asked), 2)
        self.assertIn('try again', self.err.getvalue())

    def test_three_wrong_passwords_fail(self):
        sudo = FakeSudo()
        with self.assertRaisesRegex(BecomeError, '^sudo-authentication-failed$'):
            self.acquire(sudo, answers=['wrong1', 'wrong2', 'wrong3', PASSWORD])
        self.assertEqual(len(self.asked), become.ATTEMPTS)
        self.assertEqual(len(sudo.calls), 1 + become.ATTEMPTS)

    def test_an_empty_answer_is_a_failed_attempt_without_running_sudo(self):
        sudo = FakeSudo()
        self.assertEqual(self.acquire(sudo, answers=['', PASSWORD]), PASSWORD)
        self.assertEqual(len(sudo.calls), 2)  # the probe and one validation

    def test_end_of_input_stops_asking(self):
        with self.assertRaisesRegex(BecomeError, '^sudo-password-not-entered$'):
            self.acquire(FakeSudo(), answers=[])

    def test_missing_sudo_is_a_clear_failure(self):
        def missing(argv, **kwargs):
            raise FileNotFoundError(argv[0])
        with self.assertRaisesRegex(BecomeError, '^sudo-not-found$'):
            become.acquire(stdin=Terminal(True), ask=lambda p: PASSWORD, run=missing)


def drain(fd):
    """Everything up to end of file, as ansible-playbook reads `-`."""
    data = b''
    while chunk := os.read(fd, 4096):
        data += chunk
    return data.decode()


class PasswordPipe(unittest.TestCase):
    def test_none_changes_nothing(self):
        with become.password_pipe(None) as (args, options):
            self.assertEqual((args, options), ([], {}))

    def test_the_pipe_holds_the_password_and_is_closed_afterwards(self):
        with become.password_pipe(PASSWORD) as (args, options):
            self.assertEqual(args, ['--become-password-file', '-'])
            self.assertEqual(drain(options['stdin']), PASSWORD)
        with self.assertRaises(OSError):
            os.fstat(options['stdin'])


class RefreshTicket(unittest.TestCase):
    def test_none_runs_nothing(self):
        sudo = FakeSudo()
        self.assertFalse(become.refresh_ticket(None, run=sudo))
        self.assertEqual(sudo.calls, [])

    def test_the_password_goes_to_sudo_v_on_standard_input_only(self):
        sudo = FakeSudo()
        self.assertTrue(become.refresh_ticket(PASSWORD, run=sudo))
        [(argv, kwargs)] = sudo.calls
        self.assertEqual(argv, [become.SUDO, '-S', '-v', '-p', ''])
        self.assertEqual(kwargs['input'], PASSWORD + '\n')
        self.assertNotIn(PASSWORD, ' '.join(argv))

    def test_a_refused_or_failing_refresh_is_not_an_error(self):
        self.assertFalse(become.refresh_ticket('wrong', run=FakeSudo()))

        def broken(argv, **kwargs):
            raise subprocess.TimeoutExpired(argv, 60)
        self.assertFalse(become.refresh_ticket(PASSWORD, run=broken))


class ApplyFoundation(unittest.TestCase):
    """apply_foundation with the controller downloads stubbed out."""

    STAGES = [('foundation', ['foundation.yml'], 300),
              ('packages', ['repositories.yml', 'manifest-packages.yml'], 7200),
              ('system-groups', ['system-groups.yml'], 300)]

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.root = Path(temp.name)
        self.calls = []

    def fake_run(self, argv, **kwargs):
        record = {'argv': [str(a) for a in argv], 'env': dict(kwargs.get('env') or {}),
                  'stdin': kwargs.get('stdin'), 'input': kwargs.get('input'), 'secret': None}
        if isinstance(record['stdin'], int):
            record['secret'] = drain(record['stdin'])  # what ansible-playbook does
        self.calls.append(record)
        return subprocess.CompletedProcess(argv, 0)

    def apply(self, password_answers, passwordless=False, tty=True):
        lock = {'artifacts': {k: {'version': '1', 'executable': k, 'executable_sha256': 'x'}
                              for k in ('uv', 'python')}}
        answers = list(password_answers)
        selection = {'groups': ['base'], 'profiles': ['base'], 'repositories': [],
                     'desktop': False, 'stages': []}
        config = {'target': {'user': pwd.getpwuid(os.geteuid()).pw_name}}
        with patch('workstation.controller.validate_lock', return_value=lock), \
             patch('workstation.controller.download') as download, \
             patch('workstation.controller.unpack'), \
             patch('workstation.controller.file_hash', return_value='x'), \
             patch('workstation.controller.host_stages', return_value=self.STAGES), \
             patch('workstation.controller.record_selection'), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.become.passwordless', return_value=passwordless), \
             patch('workstation.become.valid', side_effect=lambda p, run=None: p == PASSWORD), \
             patch('sys.stdin', Terminal(tty)), \
             patch('getpass.getpass', side_effect=lambda prompt: answers.pop(0)), \
             patch('subprocess.run', side_effect=self.fake_run), \
             contextlib.redirect_stderr(io.StringIO()) as self.stderr:
            try:
                return apply_foundation(config, root=self.root, selection=selection)
            finally:
                self.download = download

    def playbook_calls(self):
        return [c for c in self.calls if c['argv'][0].endswith('ansible-playbook')]

    def test_passwordless_sudo_passes_no_password_file(self):
        self.apply([], passwordless=True)
        calls = self.playbook_calls()
        self.assertEqual(len(calls), len(self.STAGES))
        for call in calls:
            self.assertNotIn('--become-password-file', call['argv'])
            self.assertIsNone(call['stdin'])  # the terminal stays inherited

    def test_every_stage_gets_the_password_through_a_pipe_and_nowhere_else(self):
        self.apply(['wrong', PASSWORD])
        calls = self.playbook_calls()
        self.assertEqual(len(calls), len(self.STAGES))
        fds = set()
        for call in calls:
            option = call['argv'].index('--become-password-file')
            self.assertEqual(call['argv'][option + 1], '-')
            self.assertEqual(call['secret'], PASSWORD)
            fds.add(call['stdin'])
        for call in self.calls:  # uv sync and every ansible-playbook run
            self.assertNotIn(PASSWORD, ' '.join(call['argv']))
            self.assertFalse(any(PASSWORD in k or PASSWORD in v for k, v in call['env'].items()))
        for fd in fds:  # each pipe closed once its run returned
            with self.assertRaises(OSError):
                os.fstat(fd)
        state = self.root / '.workstation'
        for path in state.iterdir():
            if path.is_file():
                self.assertNotIn(PASSWORD.encode(), path.read_bytes(), path.name)
        self.assertNotIn(PASSWORD, json.dumps(os.environ.copy()))

    def test_the_handoff_inherits_a_fresh_sudo_credential_after_the_last_stage(self):
        self.apply([PASSWORD])
        argvs = [c['argv'] for c in self.calls]
        refresh = argvs.index([become.SUDO, '-S', '-v', '-p', ''])
        last_stage = max(i for i, a in enumerate(argvs) if a[0].endswith('ansible-playbook'))
        self.assertGreater(refresh, last_stage)
        self.assertEqual(self.calls[refresh]['input'], PASSWORD + '\n')

    def test_passwordless_sudo_refreshes_nothing(self):
        self.apply([], passwordless=True)
        self.assertFalse(any(c['argv'][0] == become.SUDO for c in self.calls))

    def test_the_silent_host_stages_are_announced_with_the_log_path(self):
        self.apply([PASSWORD])
        notice = self.stderr.getvalue()
        self.assertIn('tail -f', notice)
        self.assertIn(str(self.root / '.workstation' / 'foundation.log'), notice)
        self.assertNotIn(PASSWORD, notice)

    def test_without_a_terminal_it_fails_before_any_write_or_stage(self):
        with self.assertRaisesRegex(BecomeError, 'sudo-password-needs-terminal'):
            self.apply([PASSWORD], tty=False)
        self.assertEqual(self.calls, [])
        self.download.assert_not_called()
        self.assertFalse((self.root / '.workstation').exists())

    def test_three_wrong_passwords_fail_before_any_write_or_stage(self):
        with self.assertRaisesRegex(BecomeError, 'sudo-authentication-failed'):
            self.apply(['a', 'b', 'c'])
        self.assertEqual(self.calls, [])
        self.assertFalse((self.root / '.workstation').exists())


class ApplyReport(unittest.TestCase):
    """The refusal reaches the report as a failed sudo check; nothing follows."""

    def test_refusal_is_reported_and_the_handoff_does_not_run(self):
        context = {'config': {'example_only': False,
                              'target': {'user': pwd.getpwuid(os.geteuid()).pw_name}},
                   'provenance': {}, 'selected': [], 'entries': {}}
        out = io.StringIO()
        with patch('workstation.cli.load_context', return_value=context), \
             patch('os.geteuid', return_value=1000), \
             patch.dict(os.environ), \
             patch('workstation.profiles.recorded', return_value=None), \
             patch('workstation.firewall.recorded_allow_ssh', return_value=None), \
             patch('workstation.host.check_prerequisites', return_value=([], 0)), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.handoff.first_run_hint', return_value=None), \
             patch('workstation.handoff.run_handoff') as handoff, \
             patch('workstation.packages.verify_packages') as verify, \
             patch('workstation.controller.apply_foundation',
                   side_effect=BecomeError('sudo-password-needs-terminal')), \
             contextlib.redirect_stdout(out), contextlib.redirect_stderr(io.StringIO()):
            os.environ.pop('SSH_CONNECTION', None)
            code = main(['apply', '--config', 'x.json', '--format', 'json'])
        self.assertEqual(code, 1)
        report = json.loads(out.getvalue())
        self.assertEqual(report['outcome'], 'failed')
        self.assertIn({'id': 'sudo', 'status': 'failed',
                       'reason': 'sudo-password-needs-terminal'}, report['checks'])
        handoff.assert_not_called()
        verify.assert_not_called()


if __name__ == '__main__':
    unittest.main()
