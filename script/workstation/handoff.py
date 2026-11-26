"""The last apply stage: hand the command line to setup-dev-linux-wsl.

Clones or updates ~/workspace/setup-dev-linux-wsl, then runs its
`./bootstrap apply --target linux` as the operator, attached to the terminal
(it prompts for the git identity). The hardening is setup-dev-win's handoff
(script/lib/Handoff.psm1), with git run directly instead of through a bash
program:

- one fixed git program from the system path, argument lists only, no shell;
- an existing clone's origin is read with `git config --get remote.origin.url`,
  not `remote get-url`, so an insteadOf rewrite cannot hide a foreign origin;
- a directory that is not a clone, a clone of anything else and a clone with
  local changes to tracked files stop the run with a message naming the
  directory; nothing is ever overwritten;
- the ref is validated, resolved with `rev-parse --verify` (origin/<ref> for a
  branch, else <ref> for a tag or commit) before anything changes, then checked
  out once with `checkout --detach`;
- never as root, and only as the target user.

A profile list is passed only when the operator gave --cli-profiles: the
bootstrap refuses a list that disagrees with its recorded choice, so passing
one on every run would break re-runs.
"""
import os
import pwd
import re
import shutil
import subprocess
import sys
from pathlib import Path

from .host import SYSTEM_PATH

REPOSITORY = 'https://github.com/istvano/setup-dev-linux-wsl'
WORKSPACE = 'workspace'
NAME = 'setup-dev-linux-wsl'
# Where setup-dev-linux-wsl's bootstrap records its profile choice, under
# ${XDG_CONFIG_HOME:-$HOME/.config}. Read only, to decide whether to print the
# first-run hint; this repository never runs the tool that writes it.
RECORD = ('chezmoi', 'chezmoi.toml')
# The command-line set this repository installed before the host refactor, as
# setup-dev-linux-wsl profiles (controller ruling RB3).
FORMER_CLI_PROFILES = ('core,dev,security,kubernetes,backup,runtime-docker,ai-agents,'
                       'cloud,cloud-aws,cloud-azure,cloud-gcp')

_REF = re.compile(r'[A-Za-z0-9._/-]{1,200}')
_PROFILES = re.compile(r'[a-z0-9][a-z0-9-]*(,[a-z0-9][a-z0-9-]*)*')


def valid_ref(ref):
    """A branch, tag or commit name no command line can read as an option."""
    return isinstance(ref, str) and bool(_REF.fullmatch(ref)) and not ref.startswith('-')


def valid_cli_profiles(text):
    """A comma-separated list of profile names; setup-dev-linux-wsl checks the names."""
    return isinstance(text, str) and len(text) <= 1000 and bool(_PROFILES.fullmatch(text))


def home():
    """The operator's home, as setup-dev-linux-wsl's bootstrap sees it ($HOME)."""
    value = os.environ.get('HOME', '')
    if value and os.path.isabs(value):
        return Path(value)
    return Path(pwd.getpwuid(os.geteuid()).pw_dir)


def clone_directory():
    return home() / WORKSPACE / NAME


def bootstrap_command(cli_profiles=None):
    """The command the handoff runs in the clone, for plan and apply alike."""
    return ['./bootstrap', 'apply', '--target', 'linux',
            *(['--profiles', cli_profiles] if cli_profiles else [])]


def first_run_hint(cli_profiles, host_profiles):
    """One hint line when setup-dev-linux-wsl has recorded no profile choice yet.

    Its first run records the choice it makes, and it refuses a different list
    afterwards, so the hint is worth most before that first run.
    """
    if cli_profiles is not None:
        return None
    base = os.environ.get('XDG_CONFIG_HOME') or str(home() / '.config')
    record = Path(base)
    if not record.is_absolute():
        # The bootstrap runs in the clone; a relative value resolves there.
        record = clone_directory() / record
    if (record / RECORD[0] / RECORD[1]).is_file():
        return None
    wanted = FORMER_CLI_PROFILES + (',gpu-nvidia' if 'gpu' in host_profiles else '')
    return ('hint: setup-dev-linux-wsl has no recorded profile choice and will record its '
            'own default; for the command-line tools this host installed before, run apply '
            f'with --cli-profiles {wanted}')


def _refusal():
    """Why the handoff may not run as this process, or None."""
    if os.geteuid() == 0:
        return 'never runs as root'
    return None


def _say(message):
    print('handoff: ' + message, file=sys.stderr)


def _git():
    return shutil.which('git', path=SYSTEM_PATH)


def _origin(git, directory):
    """The configured origin URL, '' when none is configured."""
    result = subprocess.run([git, '-C', str(directory), 'config', '--get', 'remote.origin.url'],
                            capture_output=True, text=True)
    return result.stdout.strip() if result.returncode == 0 else ''


def _same_repository(origin):
    return origin.removesuffix('.git') == REPOSITORY


def run_handoff(user, ref='main', cli_profiles=None, *, host_profiles=(), stdout=None,
                stderr=None):
    """Clone or update setup-dev-linux-wsl and run its bootstrap; its exit code.

    stdout and stderr say where git's and the bootstrap's output go (None: this
    process's); the bootstrap's standard input is always this process's, so it
    can prompt. Refusals print one line naming the cause and return 1.
    """
    if not valid_ref(ref):
        _say('invalid ref; use a branch, tag or commit name')
        return 1
    if cli_profiles is not None and not valid_cli_profiles(cli_profiles):
        _say('invalid --cli-profiles; use a comma-separated list of profile names')
        return 1
    refusal = _refusal()
    if refusal:
        _say(refusal)
        return 1
    if pwd.getpwuid(os.geteuid()).pw_name != user:
        _say(f'runs only as the target user {user}')
        return 1
    git = _git()
    if git is None:
        _say('git missing; install the git package')
        return 1
    directory = clone_directory()
    output = {'stdout': stdout, 'stderr': stderr}
    if os.path.lexists(directory):
        if not (directory / '.git').exists():
            _say(f'{directory} exists but is not a git clone; move it aside, then re-run')
            return 1
        origin = _origin(git, directory)
        if not _same_repository(origin):
            _say(f'{directory} is a clone of {origin or "no origin"}, expected {REPOSITORY}; '
                 'move it aside, then re-run')
            return 1
        status = subprocess.run([git, '-C', str(directory), 'status', '--porcelain',
                                 '--untracked-files=no'], capture_output=True, text=True)
        if status.returncode != 0:
            _say(f'cannot read the state of {directory}; repair or move it aside, then re-run')
            return status.returncode
        if status.stdout.strip():
            _say(f'{directory} has local changes; commit, stash or discard them, then re-run '
                 '(the handoff never overwrites them)')
            return 1
    else:
        directory.parent.mkdir(parents=True, exist_ok=True)
        result = subprocess.run([git, 'clone', '--quiet', '--', REPOSITORY, str(directory)],
                                **output)
        if result.returncode != 0:
            _say(f'cloning {REPOSITORY} into {directory} failed')
            return result.returncode
    result = subprocess.run([git, '-C', str(directory), 'fetch', '--quiet', '--tags', 'origin'],
                            **output)
    if result.returncode != 0:
        _say(f'fetching {REPOSITORY} into {directory} failed')
        return result.returncode
    target = None
    for candidate in (f'origin/{ref}^{{commit}}', f'{ref}^{{commit}}'):
        result = subprocess.run([git, '-C', str(directory), 'rev-parse', '--verify', '--quiet',
                                 candidate], capture_output=True, text=True)
        if result.returncode == 0:
            target = result.stdout.strip()
            break
    if not target:
        _say(f'unknown ref {ref}')
        return 1
    result = subprocess.run([git, '-C', str(directory), 'checkout', '--quiet', '--detach',
                             target], **output)
    if result.returncode != 0:
        _say(f'checking out {ref} in {directory} failed')
        return result.returncode
    hint = first_run_hint(cli_profiles, host_profiles)
    if hint:
        print(hint, file=sys.stderr)
    command = bootstrap_command(cli_profiles)
    print(f'handoff: running {" ".join(command)} in {directory}', file=sys.stderr)
    # Absolute, so the program never depends on how the platform searches cwd.
    code = subprocess.run([str(directory / 'bootstrap'), *command[1:]], cwd=directory,
                          **output).returncode
    # A signal death (-N) becomes the shell's 128+N, never a negative exit status.
    return 128 - code if code < 0 else code


def verify_cli(user, *, stdout=None, stderr=None):
    """setup-dev-linux-wsl's `script/verify --target linux`, as one check.

    Read-only: nothing is fetched or checked out, and a clone of anything else
    is reported rather than run.
    """
    def check(status, reason):
        return [{'id': 'cli:verify', 'status': status, 'reason': reason}]

    refusal = _refusal()
    if refusal:
        return check('failed', 'cli-verify-' + refusal.replace(' ', '-'))
    if pwd.getpwuid(os.geteuid()).pw_name != user:
        return check('failed', 'cli-verify-must-run-as-target-user')
    git = _git()
    if git is None:
        return check('failed', 'missing-install-package-git')
    directory = clone_directory()
    if not (directory / '.git').exists():
        return check('failed', 'setup-dev-linux-wsl-not-cloned-run-apply')
    if not _same_repository(_origin(git, directory)):
        return check('failed', 'setup-dev-linux-wsl-clone-has-another-origin')
    result = subprocess.run([str(directory / 'script' / 'verify'), '--target', 'linux'],
                            cwd=directory, stdout=stdout, stderr=stderr)
    if result.returncode == 0:
        return check('passed', 'setup-dev-linux-wsl-script-verify-passed')
    return check('failed', f'setup-dev-linux-wsl-script-verify-exit-{result.returncode}')
