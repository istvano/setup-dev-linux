"""The handoff to setup-dev-linux-wsl, run against a local bare repository.

No network: a test-only global git configuration rewrites the GitHub URL to a
bare repository with url.<bare>.insteadOf, as setup-dev-win's handoff test does.
That rewrite is also what proves the origin check reads the configured URL and
not the rewritten one. The repository's ./bootstrap and script/verify are stubs
that record the commit they ran at and their arguments.
"""
import contextlib
import io
import json
import os
import pwd
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation import handoff  # noqa: E402
from workstation.cli import main  # noqa: E402

URL = 'https://github.com/istvano/setup-dev-linux-wsl'
OLD_DEFAULT = ('core,dev,security,kubernetes,backup,runtime-docker,ai-agents,'
               'cloud,cloud-aws,cloud-azure,cloud-gcp')
BOOTSTRAP = '#!/bin/sh\necho "$(git rev-parse HEAD) $*" > "$HOME/ran"\n' \
            'exit "$(cat "$HOME/bootstrap-exit" 2>/dev/null || echo 0)"\n'
VERIFY = '#!/bin/sh\necho "$(pwd) $*" > "$HOME/verified"\n' \
         'exit "$(cat "$HOME/verify-exit" 2>/dev/null || echo 0)"\n'


def me():
    return pwd.getpwuid(os.geteuid()).pw_name


class GitFixture(unittest.TestCase):
    """A bare upstream, a seed clone that pushes to it and a fake home."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        work = Path(temp.name).resolve()
        self.home = work / 'home'
        self.home.mkdir()
        self.bare = work / 'upstream.git'
        self.seed = work / 'seed'
        self.clone = self.home / 'workspace' / 'setup-dev-linux-wsl'
        gitconfig = work / 'gitconfig'
        gitconfig.write_text(
            '[user]\n    name = Test\n    email = test@example.invalid\n'
            '[init]\n    defaultBranch = main\n'
            '[advice]\n    detachedHead = false\n'
            f'[url "{self.bare}"]\n    insteadOf = {URL}\n')
        environment = patch.dict(os.environ, {'HOME': str(self.home),
                                              'GIT_CONFIG_GLOBAL': str(gitconfig),
                                              'GIT_CONFIG_NOSYSTEM': '1'})
        environment.start()
        self.addCleanup(environment.stop)
        for name in ('XDG_CONFIG_HOME', 'XDG_STATE_HOME'):
            os.environ.pop(name, None)
        self.git('init', '--quiet', '--bare', str(self.bare))
        self.git('clone', '--quiet', str(self.bare), str(self.seed))
        (self.seed / 'bootstrap').write_text(BOOTSTRAP)
        (self.seed / 'bootstrap').chmod(0o755)
        (self.seed / 'script').mkdir()
        (self.seed / 'script' / 'verify').write_text(VERIFY)
        (self.seed / 'script' / 'verify').chmod(0o755)
        (self.seed / 'README').write_text('first\n')
        self.git('-C', str(self.seed), 'add', 'bootstrap', 'README', 'script/verify')
        self.git('-C', str(self.seed), 'commit', '--quiet', '-m', 'first')
        self.git('-C', str(self.seed), 'tag', 'v1')
        self.git('-C', str(self.seed), 'push', '--quiet', '--tags', 'origin', 'HEAD:main')
        self.first = self.tip()

    def git(self, *args):
        subprocess.run(['git', *args], check=True, capture_output=True)

    def tip(self):
        return subprocess.run(['git', '-C', str(self.seed), 'rev-parse', 'HEAD'], check=True,
                              capture_output=True, text=True).stdout.strip()

    def commit_upstream(self, text):
        (self.seed / 'README').write_text(text + '\n')
        self.git('-C', str(self.seed), 'commit', '--quiet', '-am', text)
        self.git('-C', str(self.seed), 'push', '--quiet', 'origin', 'HEAD:main')
        return self.tip()

    def ran(self):
        path = self.home / 'ran'
        return path.read_text().strip() if path.exists() else None

    def handoff(self, **kwargs):
        """(exit code, what the handoff printed on stderr)."""
        (self.home / 'ran').unlink(missing_ok=True)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = handoff.run_handoff(me(), stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL, **kwargs)
        return code, stderr.getvalue()


class HandoffTest(GitFixture):
    def test_first_run_clones_and_runs_bootstrap_for_linux_without_profiles(self):
        code, out = self.handoff()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{self.first} apply --target linux')
        result = subprocess.run(['git', '-C', str(self.clone), 'config', '--get',
                                 'remote.origin.url'], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), URL)

    def test_cli_profiles_are_passed_as_profiles(self):
        code, out = self.handoff(cli_profiles='core,dev')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{self.first} apply --target linux --profiles core,dev')

    def test_second_run_fetches_and_checks_out_the_new_tip_without_a_profile_list(self):
        """Review focus 1: the re-run updates the clone and passes no list."""
        self.assertEqual(self.handoff()[0], 0)
        tip = self.commit_upstream('second')
        code, out = self.handoff()
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{tip} apply --target linux')

    def test_a_tag_resolves_through_the_fallback(self):
        self.commit_upstream('after-tag')
        code, out = self.handoff(ref='v1')
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{self.first} apply --target linux')

    def test_a_commit_resolves_through_the_fallback(self):
        self.commit_upstream('after')
        code, out = self.handoff(ref=self.first)
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{self.first} apply --target linux')

    def test_an_unknown_ref_stops_with_unknown_ref(self):
        code, out = self.handoff(ref='no-such-ref')
        self.assertNotEqual(code, 0)
        self.assertIn('unknown ref no-such-ref', out)
        self.assertIsNone(self.ran())

    def test_a_clone_with_another_origin_stops_naming_the_directory(self):
        """Review focus 4: never overwrite a clone of something else."""
        self.git('clone', '--quiet', str(self.bare), str(self.clone))
        self.git('-C', str(self.clone), 'config', 'remote.origin.url',
                 'https://github.com/someone/else')
        code, out = self.handoff()
        self.assertNotEqual(code, 0)
        self.assertIn(str(self.clone), out)
        self.assertIn('https://github.com/someone/else', out)
        self.assertIsNone(self.ran())
        result = subprocess.run(['git', '-C', str(self.clone), 'config', '--get',
                                 'remote.origin.url'], capture_output=True, text=True)
        self.assertEqual(result.stdout.strip(), 'https://github.com/someone/else')

    def test_a_dirty_tree_stops_naming_the_directory_and_keeps_the_change(self):
        """Review focus 4: local changes are never overwritten."""
        self.assertEqual(self.handoff()[0], 0)
        (self.clone / 'README').write_text('local edit\n')
        self.commit_upstream('upstream edit')
        code, out = self.handoff()
        self.assertNotEqual(code, 0)
        self.assertIn(str(self.clone), out)
        self.assertIn('local changes', out)
        self.assertIsNone(self.ran())
        self.assertEqual((self.clone / 'README').read_text(), 'local edit\n')

    def test_a_staged_change_is_a_local_change(self):
        self.assertEqual(self.handoff()[0], 0)
        (self.clone / 'new-file').write_text('x\n')
        self.git('-C', str(self.clone), 'add', 'new-file')
        code, out = self.handoff()
        self.assertNotEqual(code, 0)
        self.assertIn('local changes', out)

    def test_a_directory_that_is_not_a_clone_stops_naming_it(self):
        self.clone.mkdir(parents=True)
        (self.clone / 'notes').write_text('mine\n')
        code, out = self.handoff()
        self.assertNotEqual(code, 0)
        self.assertIn(str(self.clone), out)
        self.assertIn('not a git clone', out)
        self.assertEqual(sorted(p.name for p in self.clone.iterdir()), ['notes'])

    def test_the_bootstrap_exit_code_is_returned(self):
        (self.home / 'bootstrap-exit').write_text('7\n')
        code, _ = self.handoff()
        self.assertEqual(code, 7)

    def test_a_bootstrap_killed_by_a_signal_returns_128_plus_the_signal(self):
        (self.seed / 'bootstrap').write_text('#!/bin/sh\nkill -TERM $$\n')
        self.git('-C', str(self.seed), 'commit', '--quiet', '-am', 'killed')
        self.git('-C', str(self.seed), 'push', '--quiet', 'origin', 'HEAD:main')
        code, _ = self.handoff()
        self.assertEqual(code, 128 + 15)

    def test_never_runs_as_root(self):
        with patch('os.geteuid', return_value=0):
            code, out = self.handoff()
        self.assertNotEqual(code, 0)
        self.assertIn('root', out)
        self.assertFalse(self.clone.exists())
        self.assertIsNone(self.ran())

    def test_runs_only_as_the_target_user(self):
        (self.home / 'ran').unlink(missing_ok=True)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code = handoff.run_handoff('someone-else', stdout=subprocess.DEVNULL,
                                       stderr=subprocess.DEVNULL)
        self.assertNotEqual(code, 0)
        self.assertFalse(self.clone.exists())

    def test_a_git_identity_runs_the_bootstrap_non_interactively(self):
        """RB11: an unattended first run (the VM cycle) has no terminal to prompt on."""
        code, out = self.handoff(cli_profiles='core,dev',
                                 identity=('VM Test', 'ws-test@example.invalid'))
        self.assertEqual(code, 0, out)
        self.assertEqual(self.ran(), f'{self.first} apply --target linux --profiles core,dev '
                                     '--non-interactive --git-name VM Test '
                                     '--git-email ws-test@example.invalid')

    def test_the_running_line_does_not_echo_the_identity(self):
        code, out = self.handoff(identity=('VM Test', 'ws-test@example.invalid'))
        self.assertEqual(code, 0, out)
        self.assertIn('--non-interactive', out)
        self.assertNotIn('VM Test', out)
        self.assertNotIn('ws-test@example.invalid', out)

    def test_an_invalid_identity_is_refused_before_anything_runs(self):
        for identity in (('', 'a@b'), ('Name', ''), ('-n', 'a@b'), ('Doe, Jane', 'a@b'),
                         ('Name', 'a=b@c'), ('Na"me', 'a@b'), ('Na\nme', 'a@b'),
                         ('x' * 201, 'a@b'), ('Name',)):
            code, _ = self.handoff(identity=identity)
            self.assertNotEqual(code, 0, identity)
        self.assertFalse(self.clone.exists())

    def test_an_invalid_ref_or_profile_list_is_refused_before_anything_runs(self):
        for kwargs in ({'ref': '--upload-pack=x'}, {'ref': 'a b'}, {'ref': '$(id)'},
                       {'ref': ''}, {'cli_profiles': '--x'}, {'cli_profiles': 'core;id'},
                       {'cli_profiles': ''}):
            code, _ = self.handoff(**kwargs)
            self.assertNotEqual(code, 0, kwargs)
        self.assertFalse(self.clone.exists())


class HintTest(GitFixture):
    """RB3: one hint line on a run where setup-dev-linux-wsl has recorded nothing."""

    def record(self):
        path = self.home / '.config' / handoff.RECORD[0] / handoff.RECORD[1]
        path.parent.mkdir(parents=True)
        path.write_text('[data]\n')

    def hint_lines(self, out):
        return [line for line in out.splitlines() if line.startswith('hint:')]

    def test_no_record_and_no_cli_profiles_prints_one_hint_line(self):
        code, out = self.handoff()
        self.assertEqual(code, 0, out)
        lines = self.hint_lines(out)
        self.assertEqual(len(lines), 1, out)
        self.assertIn('--cli-profiles ' + OLD_DEFAULT, lines[0])
        self.assertNotIn('gpu-nvidia', lines[0])

    def test_the_hint_says_how_to_act_now_and_how_to_recover_later(self):
        """RB15: interrupt now to choose; once recorded, edit the record."""
        _, out = self.handoff()
        line = self.hint_lines(out)[0]
        self.assertIn('interrupt now', line)
        self.assertIn('re-run apply with --cli-profiles', line)
        record = self.home / '.config' / handoff.RECORD[0] / handoff.RECORD[1]
        self.assertIn(f'change [data] profiles in {record}', line)

    def test_the_hint_names_the_record_under_xdg_config_home(self):
        config = self.home / 'elsewhere'
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(config)}):
            _, out = self.handoff()
        self.assertIn(str(config / handoff.RECORD[0] / handoff.RECORD[1]),
                      self.hint_lines(out)[0])

    def test_the_hint_comes_just_before_the_bootstrap(self):
        _, out = self.handoff()
        lines = out.splitlines()
        hint = next(i for i, line in enumerate(lines) if line.startswith('hint:'))
        running = next(i for i, line in enumerate(lines) if line.startswith('handoff: running'))
        self.assertEqual(running, hint + 1, out)

    def test_the_gpu_host_profile_adds_gpu_nvidia(self):
        _, out = self.handoff(host_profiles=['desktop', 'gpu'])
        self.assertIn('--cli-profiles ' + OLD_DEFAULT + ',gpu-nvidia', self.hint_lines(out)[0])

    def test_a_recorded_choice_prints_no_hint(self):
        self.record()
        _, out = self.handoff()
        self.assertEqual(self.hint_lines(out), [])

    def test_given_cli_profiles_print_no_hint(self):
        _, out = self.handoff(cli_profiles='core,dev')
        self.assertEqual(self.hint_lines(out), [])

    def test_the_hint_follows_xdg_config_home(self):
        config = self.home / 'elsewhere'
        path = config / handoff.RECORD[0] / handoff.RECORD[1]
        path.parent.mkdir(parents=True)
        path.write_text('[data]\n')
        with patch.dict(os.environ, {'XDG_CONFIG_HOME': str(config)}):
            _, out = self.handoff()
        self.assertEqual(self.hint_lines(out), [])


class VerifyCliTest(GitFixture):
    def verify(self):
        return handoff.verify_cli(me(), stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    def test_runs_script_verify_for_linux_in_the_clone(self):
        self.assertEqual(self.handoff()[0], 0)
        checks = self.verify()
        self.assertEqual([c['status'] for c in checks], ['passed'], checks)
        self.assertEqual((self.home / 'verified').read_text().strip(),
                         f'{self.clone} --target linux')

    def test_fails_when_script_verify_fails(self):
        self.assertEqual(self.handoff()[0], 0)
        (self.home / 'verify-exit').write_text('1\n')
        checks = self.verify()
        self.assertEqual([c['status'] for c in checks], ['failed'])

    def test_fails_without_a_clone(self):
        checks = self.verify()
        self.assertEqual([c['status'] for c in checks], ['failed'])
        self.assertIn('not-cloned', checks[0]['reason'])

    def test_fails_without_running_a_clone_of_another_origin(self):
        self.assertEqual(self.handoff()[0], 0)
        self.git('-C', str(self.clone), 'config', 'remote.origin.url',
                 'https://github.com/someone/else')
        checks = self.verify()
        self.assertEqual([c['status'] for c in checks], ['failed'])
        self.assertFalse((self.home / 'verified').exists())

    def test_never_runs_as_root(self):
        self.assertEqual(self.handoff()[0], 0)
        with patch('os.geteuid', return_value=0):
            checks = self.verify()
        self.assertEqual([c['status'] for c in checks], ['failed'])
        self.assertFalse((self.home / 'verified').exists())


HOST_INCOMPLETE = 3


def context():
    return {'config': {'example_only': False, 'target': {'user': me()}},
            'provenance': {}, 'selected': [], 'entries': {}, 'approved': {}}


class StartHintTest(unittest.TestCase):
    """RB15: apply prints the hint before the first host stage."""

    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.home = Path(temp.name).resolve()
        environment = patch.dict(os.environ, {'HOME': str(self.home)})
        environment.start()
        self.addCleanup(environment.stop)
        os.environ.pop('XDG_CONFIG_HOME', None)

    def run_apply(self, *extra):
        """(exit code, stderr at the moment the host stages started, whole stderr)."""
        stderr = io.StringIO()
        seen = []

        def foundation(*args, **kwargs):
            seen.append(stderr.getvalue())
            return {'id': 'controller-foundation', 'status': 'passed', 'reason': 'fixture'}

        targets = {
            'workstation.cli.load_context': context(),
            'workstation.profiles.recorded': None,
            'workstation.storage.preflight': ([], 0),
            'workstation.host.check_prerequisites': ([], 0),
            'workstation.packages.verify_packages': [],
            'workstation.system.verify': [],
            'workstation.delivery.verify': [],
            'workstation.desktop.verify': [],
            'workstation.firewall.verify': [],
            'workstation.firewall.recorded_allow_ssh': None,
            'workstation.plugins.verify': [],
            'workstation.handoff.run_handoff': 0,
        }
        with contextlib.ExitStack() as stack:
            for target, value in targets.items():
                stack.enter_context(patch(target, return_value=value))
            stack.enter_context(patch('workstation.controller.apply_foundation',
                                      side_effect=foundation))
            stack.enter_context(patch('os.geteuid', return_value=1000))
            stack.enter_context(contextlib.redirect_stdout(io.StringIO()))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = main(['apply', '--config', 'x.json', '--format', 'json', *extra])
        return code, seen[0] if seen else '', stderr.getvalue()

    def hints(self, text):
        return [line for line in text.splitlines() if line.startswith('hint:')]

    def test_unrecorded_prints_the_hint_before_the_host_stages(self):
        _, before, _ = self.run_apply()
        self.assertEqual(len(self.hints(before)), 1, before)
        self.assertIn(str(self.home / '.config' / handoff.RECORD[0] / handoff.RECORD[1]),
                      self.hints(before)[0])

    def test_a_recorded_choice_prints_no_hint(self):
        record = self.home / '.config' / handoff.RECORD[0] / handoff.RECORD[1]
        record.parent.mkdir(parents=True)
        record.write_text('[data]\n')
        _, _, everything = self.run_apply()
        self.assertEqual(self.hints(everything), [])

    def test_given_cli_profiles_print_no_hint(self):
        _, _, everything = self.run_apply('--cli-profiles', 'core,dev')
        self.assertEqual(self.hints(everything), [])

    def test_no_handoff_prints_no_hint(self):
        _, _, everything = self.run_apply('--no-handoff')
        self.assertEqual(self.hints(everything), [])


class CliWiringTest(unittest.TestCase):
    """apply ends with the handoff; verify appends the CLI verify.

    The fixture selects no capability, so the host part alone reports
    incomplete (3); a passing handoff leaves that outcome as it is.
    """

    def run_cli(self, args, handoff_code=0, cli_checks=None, foundation=None,
                handoff_effect=None):
        stdout, stderr = io.StringIO(), io.StringIO()
        targets = {
            'workstation.cli.load_context': context(),
            'workstation.profiles.recorded': None,
            'workstation.storage.preflight': ([], 0),
            'workstation.host.check_prerequisites': ([], 0),
            'workstation.packages.verify_packages': [],
            'workstation.system.verify': [],
            'workstation.delivery.verify': [],
            'workstation.desktop.verify': [],
            'workstation.firewall.verify': [],
            'workstation.firewall.recorded_allow_ssh': None,
            'workstation.plugins.verify': [],
            'workstation.controller.apply_foundation': {
                'id': 'controller-foundation', 'status': 'passed', 'reason': 'fixture'},
            'workstation.handoff.run_handoff': handoff_code,
            'workstation.handoff.verify_cli': cli_checks if cli_checks is not None else [
                {'id': 'cli:verify', 'status': 'passed', 'reason': 'fixture'}],
            'workstation.handoff.first_run_hint': None,
        }
        with contextlib.ExitStack() as stack:
            self.mocks = {t: stack.enter_context(patch(t, return_value=v))
                          for t, v in targets.items()}
            if foundation is not None:
                self.mocks['workstation.controller.apply_foundation'].side_effect = foundation
            if handoff_effect is not None:
                self.mocks['workstation.handoff.run_handoff'].side_effect = handoff_effect
            stack.enter_context(patch('os.geteuid', return_value=1000))
            stack.enter_context(contextlib.redirect_stdout(stdout))
            stack.enter_context(contextlib.redirect_stderr(stderr))
            code = main(args)
        return code, stdout.getvalue(), stderr.getvalue()

    def handoff_mock(self):
        return self.mocks['workstation.handoff.run_handoff']

    def test_apply_ends_with_the_handoff_on_main_without_cli_profiles(self):
        code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                     '--profiles', 'firewall,gpu'])
        self.assertEqual(code, HOST_INCOMPLETE, out)
        self.handoff_mock().assert_called_once()
        call = self.handoff_mock().call_args
        self.assertEqual(call.args[:3], (me(), 'main', None))
        self.assertEqual(call.kwargs['host_profiles'], ['gpu', 'firewall'])
        checks = {c['id']: c for c in json.loads(out)['checks']}
        self.assertEqual(checks['handoff']['status'], 'passed')

    def test_cli_profiles_and_linux_ref_are_passed_through(self):
        self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                      '--cli-profiles', 'core,dev', '--linux-ref', 'v1'])
        self.assertEqual(self.handoff_mock().call_args.args[:3], (me(), 'v1', 'core,dev'))

    def test_no_handoff_skips_it(self):
        code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                     '--no-handoff'])
        self.assertEqual(code, HOST_INCOMPLETE, out)
        self.handoff_mock().assert_not_called()

    def test_a_failed_handoff_fails_the_run_with_its_exit_code(self):
        code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json'],
                                    handoff_code=5)
        self.assertEqual(code, 5)
        report = json.loads(out)
        self.assertEqual(report['outcome'], 'failed')
        self.assertEqual({c['id']: c for c in report['checks']}['handoff']['status'], 'failed')

    def test_a_handoff_that_cannot_start_keeps_the_host_report(self):
        code, out, err = self.run_cli(['apply', '--config', 'x.json', '--format', 'json'],
                                      handoff_effect=PermissionError('fixture'))
        self.assertEqual(code, 1)
        report = json.loads(out)
        ids = {c['id']: c['status'] for c in report['checks']}
        self.assertEqual(ids['controller-foundation'], 'passed')
        self.assertEqual(ids['handoff'], 'failed')
        self.assertIn('handoff:', err)

    def test_an_interrupted_host_stage_exits_130_without_a_traceback(self):
        code, out, err = self.run_cli(['apply', '--config', 'x.json', '--format', 'json'],
                                      foundation=KeyboardInterrupt())
        self.assertEqual(code, 130)
        self.assertNotIn('Traceback', err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertIn('interrupted', err)
        report = json.loads(out)
        self.assertEqual(report['outcome'], 'failed')
        self.handoff_mock().assert_not_called()

    def test_an_interrupted_bootstrap_exits_130_without_a_traceback(self):
        code, out, err = self.run_cli(['apply', '--config', 'x.json', '--format', 'json'],
                                      handoff_effect=KeyboardInterrupt())
        self.assertEqual(code, 130)
        self.assertNotIn('Traceback', err)
        self.assertEqual(len(err.strip().splitlines()), 1, err)
        self.assertEqual(json.loads(out)['outcome'], 'failed')

    def test_an_interrupt_in_text_mode_exits_130(self):
        code, out, err = self.run_cli(['apply', '--config', 'x.json'],
                                      foundation=KeyboardInterrupt())
        self.assertEqual(code, 130)
        self.assertNotIn('Traceback', err + out)

    def test_a_failed_host_stage_never_hands_off(self):
        code, _, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json'],
                                  foundation=subprocess.CalledProcessError(2, 'ansible'))
        self.assertEqual(code, 1)
        self.handoff_mock().assert_not_called()

    def test_an_invalid_linux_ref_stops_before_anything_changes(self):
        code, _, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                   '--linux-ref', '--upload-pack=x'])
        self.assertEqual(code, 2)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_invalid_cli_profiles_stop_before_anything_changes(self):
        code, _, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                   '--cli-profiles', 'core;id'])
        self.assertEqual(code, 2)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_a_git_identity_is_passed_through(self):
        self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                      '--cli-git-name', 'VM Test', '--cli-git-email', 'ws@example.invalid'])
        self.assertEqual(self.handoff_mock().call_args.kwargs['identity'],
                         ('VM Test', 'ws@example.invalid'))

    def test_without_an_identity_none_is_passed(self):
        self.run_cli(['apply', '--config', 'x.json', '--format', 'json'])
        self.assertIsNone(self.handoff_mock().call_args.kwargs['identity'])

    def test_a_git_identity_needs_both_halves_and_the_handoff(self):
        for extra in (['--cli-git-name', 'VM Test'],
                      ['--cli-git-email', 'ws@example.invalid'],
                      ['--cli-git-name', 'VM Test', '--cli-git-email', 'ws@example.invalid',
                       '--no-handoff'],
                      ['--cli-git-name', 'Doe, Jane', '--cli-git-email', 'ws@example.invalid']):
            code, out, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                         *extra])
            self.assertEqual(code, 2, extra)
            self.assertEqual(json.loads(out)['outcome'], 'invalid')
            self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_plan_shows_the_non_interactive_handoff_without_the_identity(self):
        _, out, _ = self.run_cli(['plan', '--config', 'x.json', '--format', 'json',
                                  '--cli-git-name', 'VM Test',
                                  '--cli-git-email', 'ws@example.invalid'])
        reason = {c['id']: c for c in json.loads(out)['checks']}['stage:handoff']['reason']
        self.assertIn('--non-interactive --git-name <given> --git-email <given>', reason)
        self.assertNotIn('VM Test', out)
        self.assertNotIn('ws@example.invalid', out)

    def test_cli_profiles_with_no_handoff_is_invalid(self):
        code, _, _ = self.run_cli(['apply', '--config', 'x.json', '--format', 'json',
                                   '--no-handoff', '--cli-profiles', 'core'])
        self.assertEqual(code, 2)
        self.mocks['workstation.controller.apply_foundation'].assert_not_called()

    def test_verify_appends_the_cli_verify(self):
        code, out, _ = self.run_cli(['verify', '--config', 'x.json', '--format', 'json'])
        self.mocks['workstation.handoff.verify_cli'].assert_called_once()
        self.assertEqual(self.mocks['workstation.handoff.verify_cli'].call_args.args[0], me())
        self.assertIn('cli:verify', {c['id'] for c in json.loads(out)['checks']})
        self.handoff_mock().assert_not_called()
        self.assertEqual(code, HOST_INCOMPLETE, out)

    def test_verify_fails_when_the_cli_verify_fails(self):
        code, out, _ = self.run_cli(['verify', '--config', 'x.json', '--format', 'json'],
                                    cli_checks=[{'id': 'cli:verify', 'status': 'failed',
                                                 'reason': 'fixture'}])
        self.assertEqual(code, 1)
        self.assertEqual(json.loads(out)['outcome'], 'failed')

    def test_verify_with_no_handoff_skips_the_cli_verify(self):
        self.run_cli(['verify', '--config', 'x.json', '--format', 'json', '--no-handoff'])
        self.mocks['workstation.handoff.verify_cli'].assert_not_called()

    def test_apply_does_not_run_the_cli_verify_itself(self):
        """setup-dev-linux-wsl's bootstrap ends with its own verify."""
        self.run_cli(['apply', '--config', 'x.json', '--format', 'json'])
        self.mocks['workstation.handoff.verify_cli'].assert_not_called()

    def test_plan_names_the_handoff_stage(self):
        _, out, _ = self.run_cli(['plan', '--config', 'x.json', '--format', 'json',
                                  '--cli-profiles', 'core,dev'])
        checks = {c['id']: c for c in json.loads(out)['checks']}
        self.assertEqual(checks['stage:handoff']['status'], 'planned')
        self.assertIn('--target linux --profiles core,dev', checks['stage:handoff']['reason'])
        self.handoff_mock().assert_not_called()
        _, out, _ = self.run_cli(['plan', '--config', 'x.json', '--format', 'json',
                                  '--no-handoff'])
        self.assertNotIn('stage:handoff', {c['id'] for c in json.loads(out)['checks']})

    def test_plan_prints_the_first_run_hint(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch('workstation.cli.load_context', return_value=context()), \
             patch('workstation.profiles.recorded', return_value=None), \
             patch('workstation.handoff.first_run_hint', return_value='hint: fixture'), \
             contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            main(['plan', '--config', 'x.json', '--format', 'json'])
        self.assertIn('hint: fixture', stderr.getvalue())
        json.loads(stdout.getvalue())


if __name__ == '__main__':
    unittest.main()
