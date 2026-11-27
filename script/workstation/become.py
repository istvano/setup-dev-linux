"""The sudo password the host stages' privileged tasks need, asked for once.

Ansible's privileged tasks run sudo. Without a become password Ansible runs
`sudo -n`, which fails on any account without passwordless sudo: Ubuntu 26.04's
sudo-rs says "interactive authentication is required" (D031). So apply asks
once, before the first write, and hands the answer to every ansible-playbook
run the way `--ask-become-pass` would.

The password is never echoed, logged, printed, written to a file, placed in an
environment variable or put on a command line. sudo reads it on standard input
to validate it; ansible-playbook reads it from a pipe on its standard input
(`--become-password-file -`), a fresh one per run, so no path on disk ever
holds it.
"""
import contextlib
import getpass
import os
import pwd
import subprocess
import sys

ATTEMPTS = 3
SUDO = '/usr/bin/sudo'


class BecomeError(Exception):
    """Privilege cannot be raised; the message is a redacted reason."""


def passwordless(run=None):
    """True when sudo needs no password (NOPASSWD, as on the VM guest)."""
    run = run or subprocess.run
    try:
        result = run([SUDO, '-n', 'true'], stdin=subprocess.DEVNULL,
                     stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    except FileNotFoundError:
        raise BecomeError('sudo-not-found') from None
    return result.returncode == 0


def valid(password, run=None):
    """Whether sudo accepts this password, read on standard input.

    -S reads it from standard input; -k ignores any cached credential, so the
    password itself is what is tested; -p '' prints no prompt. sudo-rs supports
    all three, as sudo does. Its output is discarded.
    """
    run = run or subprocess.run
    result = run([SUDO, '-S', '-k', '-p', '', 'true'], input=password + '\n', text=True,
                 stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=60)
    return result.returncode == 0


def acquire(stdin=None, ask=None, run=None, err=None):
    """None with passwordless sudo, else a password sudo accepted.

    Asks at most ATTEMPTS times. Raises BecomeError, before anything is written,
    when there is no terminal to ask on or no answer is accepted.
    """
    stdin = sys.stdin if stdin is None else stdin
    err = sys.stderr if err is None else err
    ask = ask or getpass.getpass
    if passwordless(run):
        return None
    if stdin is None or not stdin.isatty():
        raise BecomeError('sudo-password-needs-terminal')
    user = pwd.getpwuid(os.geteuid()).pw_name
    for attempt in range(ATTEMPTS):
        try:
            password = ask(f'[setup-dev-linux] sudo password for {user}: ')
        except EOFError:
            raise BecomeError('sudo-password-not-entered') from None
        if password and valid(password, run):
            return password
        if attempt + 1 < ATTEMPTS:
            print('Sorry, try again.', file=err)
    raise BecomeError('sudo-authentication-failed')


@contextlib.contextmanager
def password_pipe(password):
    """(arguments, subprocess options) that hand ansible-playbook the password.

    `--become-password-file -` makes ansible-playbook read the password from
    its standard input, which is the read end of a fresh pipe: written and its
    write end closed before ansible-playbook starts (a password is far smaller
    than the pipe buffer), and closed here once it returns. A /dev/fd/N path
    cannot be used: ansible-playbook resolves the option with realpath, which
    turns /dev/fd/N into a /proc/PID/fd/pipe:[...] name that does not exist.
    With passwordless sudo nothing changes and standard input stays inherited.
    """
    if password is None:
        yield [], {}
        return
    read_end, write_end = os.pipe()
    try:
        with os.fdopen(write_end, 'wb') as stream:
            write_end = None
            stream.write(password.encode())
        yield ['--become-password-file', '-'], {'stdin': read_end}
    finally:
        if write_end is not None:
            os.close(write_end)
        os.close(read_end)
