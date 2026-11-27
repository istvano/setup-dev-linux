"""The host firewall: UFW and OpenSnitch.

UFW denies incoming and allows outgoing; SSH is allowed only when the operator
chose it (`--allow-ssh`), and that choice is recorded in per-user state so a
later run without the flag does not silently remove the rule from a machine
the operator reaches over SSH. Over SSH, apply refuses until a choice exists
(a flag or a record). The UFW `OpenSSH` profile comes from openssh-server and
covers port 22 only, so `--allow-ssh` needs that package.

OpenSnitch is installed and running in allow mode: Ubuntu's package ships
`"DefaultAction": "allow"` and the daemon's system-wide configuration is never
written here, so an operator's later deny is never undone. With the desktop
set the UI, which decides while connected, gets its own allow default once,
only where the operator has set none. The setup, and the handoff to
setup-dev-linux-wsl that follows it, must never be blocked by a prompt nobody
is there to answer. Switching to deny is the operator's later decision, made
with the rules they have built up.

Docker's published ports bypass UFW: Docker writes its own packet-filter rules
ahead of UFW's. Docker is not installed here, so the notice is raised only when
it is present.

Everything in verify is read-only. `ufw status` needs root, so it goes through
`sudo -n`; where that is unavailable the check is deferred, never passed.
"""
import os
import re
import shutil
import subprocess
import time
from pathlib import Path

from . import state
from .config import InputError, load_json

PACKAGES = ['ufw', 'opensnitch', 'opensnitch-ebpf-modules']
UI_PACKAGE = 'python3-opensnitch-ui'
OPENSNITCH_CONFIG = '/etc/opensnitchd/default-config.json'
# The UI is a QSettings("opensnitch", "settings") INI file; key "global/default_action"
# is section [global], key default_action. 1 is ACTION_ALLOW_IDX, 0 is deny (the UI's
# own default when the key is absent, verified against python3-opensnitch-ui 1.6.9
# opensnitch/config.py). While the UI is connected it, not the daemon, decides.
# QSettings puts it under $XDG_CONFIG_HOME when that is set (ui_settings_path).
UI_SETTINGS = '.config/opensnitch/settings.conf'
UI_ALLOW = 1
STATE_KEY = 'firewall'
UNREADABLE = 'recorded-firewall-unreadable; pass --allow-ssh or --no-allow-ssh'
# The UFW application profile `ufw allow OpenSSH` needs; openssh-server ships it.
OPENSSH_PROFILE = '/etc/ufw/applications.d/openssh-server'
NEEDS_CHOICE = 'ssh-session-needs-an-explicit-choice; pass --allow-ssh or --no-allow-ssh'
NEEDS_OPENSSH = 'allow-ssh-needs-openssh-server; install openssh-server or pass --no-allow-ssh'


def recorded_allow_ssh():
    """The recorded choice, or None when none was recorded.

    A record that exists but is malformed or unsafe is an error: defaulting to
    "no SSH" would remove the rule from a machine reached over SSH.
    """
    try:
        value = state.get(STATE_KEY)
    except InputError:
        raise InputError(UNREADABLE) from None
    if value is None:
        return None
    if not isinstance(value, dict):
        raise InputError(UNREADABLE)
    if 'allow_ssh' not in value:
        return None  # only the seeding flags are recorded
    if not isinstance(value['allow_ssh'], bool):
        raise InputError(UNREADABLE)
    return value['allow_ssh']


def resolve_allow_ssh(flag):
    """(allow_ssh, source): the flag, else the recorded choice, else False."""
    if flag is not None:
        return flag, 'explicit'
    recorded = recorded_allow_ssh()
    if recorded is not None:
        return recorded, 'recorded'
    return False, 'default'


def require_ssh_choice(allow_ssh, source, environ=None, profile=None):
    """Refuse an apply that would decide about SSH by default, or could not open it.

    Over SSH (SSH_CONNECTION set) with no flag and no record, the default closes
    SSH to new logins on the machine the operator is using, so the operator
    decides first. An explicit --no-allow-ssh, or a recorded choice, proceeds.
    An effective allow needs openssh-server's UFW profile, or the stage would
    fail after the packages stage. Checked before anything changes.
    """
    environ = os.environ if environ is None else environ
    if source == 'default' and environ.get('SSH_CONNECTION'):
        raise InputError(NEEDS_CHOICE)
    if allow_ssh and not Path(OPENSSH_PROFILE if profile is None else profile).is_file():
        raise InputError(NEEDS_OPENSSH)


def record_allow_ssh(value):
    current = state.get(STATE_KEY)
    merged = dict(current) if isinstance(current, dict) else {}
    merged['allow_ssh'] = bool(value)
    state.set(STATE_KEY, merged)


def _flag(key):
    value = state.get(STATE_KEY)
    if value is None:
        return False
    if not isinstance(value, dict):
        raise InputError(UNREADABLE)
    return value.get(key) is True


def opensnitch_ui_seeded():
    """Whether the UI's allow default was already seeded for this user."""
    return _flag('opensnitch_ui_seeded')


def ui_settings_path(home, environ=None):
    """The OpenSnitch UI's settings file, where QSettings looks for it.

    $XDG_CONFIG_HOME/opensnitch/settings.conf when that is set to an absolute
    path (the XDG specification ignores a relative one), else
    <home>/.config/opensnitch/settings.conf.
    """
    environ = os.environ if environ is None else environ
    base = environ.get('XDG_CONFIG_HOME', '')
    if base and os.path.isabs(base):
        return Path(base) / 'opensnitch' / 'settings.conf'
    return Path(home) / UI_SETTINGS


def record_flag(key):
    current = state.get(STATE_KEY)
    merged = dict(current) if isinstance(current, dict) else {}
    merged[key] = True
    state.set(STATE_KEY, merged)


_SECTION = re.compile(r'^\[(.*)\]\s*$')
_KEY = re.compile(r'^default_action\s*=')


def seed_ui_settings(path, now=time.time):
    """Make the OpenSnitch UI default to allow, once, without touching a value.

    The file belongs to the operator. It is created when absent; an existing
    default_action under [global] is never rewritten; anything else is
    backed up (settings.conf.bak-<epoch>) before the key is added. Returns
    'created', 'added' or 'kept'.
    """
    path = Path(path)
    if not path.exists():
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f'[global]\ndefault_action={UI_ALLOW}\n')
        return 'created'
    text = path.read_text()
    lines = text.splitlines()
    section = None
    insert_at = None
    for index, line in enumerate(lines):
        match = _SECTION.match(line.strip())
        if match:
            section = match.group(1)
            if section == 'global' and insert_at is None:
                insert_at = index + 1
        elif section == 'global' and _KEY.match(line.strip()):
            return 'kept'
    backup = path.with_name(path.name + f'.bak-{int(now())}')
    shutil.copy2(path, backup)
    if insert_at is None:
        lines += ['[global]'] if not lines or lines[-1] == '' else ['', '[global]']
        lines.append(f'default_action={UI_ALLOW}')
    else:
        lines.insert(insert_at, f'default_action={UI_ALLOW}')
    path.write_text('\n'.join(lines) + '\n')
    return 'added'


def ui_mode(path):
    """'allow', 'deny' or 'unset' from the UI settings file, read-only."""
    try:
        section = None
        for line in Path(path).read_text().splitlines():
            match = _SECTION.match(line.strip())
            if match:
                section = match.group(1)
            elif section == 'global' and _KEY.match(line.strip()):
                value = line.split('=', 1)[1].strip()
                return {'1': 'allow', '0': 'deny', '2': 'reject'}.get(value, 'unknown')
    except OSError:
        pass
    return 'unset'


def ssh_notice(allow_ssh, environ=None):
    """A notice when SSH is about to be (or is) closed under an SSH session."""
    environ = os.environ if environ is None else environ
    if allow_ssh or not environ.get('SSH_CONNECTION'):
        return None
    return {'id': 'firewall:ssh-closing', 'status': 'notice',
            'reason': 'connected-over-ssh-and-ssh-is-not-allowed-the-current-session-survives-'
                      'new-logins-are-refused-pass---allow-ssh-to-keep-them'}


# A rule line: the To column, then the action and its direction (absent in plain
# `ufw status`), then From. ALLOW and LIMIT both let a connection in.
_RULE = re.compile(r'^(?P<to>\S.*?)\s+(?P<action>ALLOW|LIMIT|DENY|REJECT)'
                   r'(?:\s+(?P<direction>IN|OUT|FWD))?(?:\s|$)')
# The To column of a rule for SSH: the OpenSSH profile, the ssh service or port 22
# (any v6 or interface suffix after it), or a port shown with the profile name.
_SSH_TO = re.compile(r'^(?:OpenSSH|ssh|22|22/tcp)(?:\s|$)|\(OpenSSH\b')


def _lets_ssh_in(line):
    match = _RULE.match(line)
    return bool(match and match.group('action') in ('ALLOW', 'LIMIT')
                and match.group('direction') in (None, 'IN')
                and _SSH_TO.search(match.group('to')))


def parse_ufw(text):
    """What `ufw status verbose` says: active, default policies, an incoming SSH rule.

    Any rule that lets SSH in counts, v4 or v6: the OpenSSH profile, the ssh
    service, port 22 or 22/tcp, with ALLOW or LIMIT. A rule added by hand under
    another name must not pass as "SSH not allowed".
    """
    active = re.search(r'^Status:\s*active\s*$', text, re.M) is not None
    defaults = re.search(r'^Default:\s*(.+)$', text, re.M)
    policies = {}
    if defaults:
        for policy, direction in re.findall(r'(\w+)\s*\((\w+)\)', defaults.group(1)):
            policies[direction] = policy
    ssh = any(_lets_ssh_in(line) for line in text.splitlines())
    return {'active': active, 'incoming': policies.get('incoming'),
            'outgoing': policies.get('outgoing'), 'ssh': ssh}


def _run(argv):
    try:
        done = subprocess.run(argv, capture_output=True, text=True, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return 127, ''
    return done.returncode, done.stdout


def _installed(run, package):
    code, out = run(['dpkg-query', '-W', '-f=${Status}', package])
    return code == 0 and out.strip().endswith('install ok installed')


def _check(name, ok, passed, failed):
    return {'id': 'firewall:' + name, 'status': 'passed' if ok else 'failed',
            'reason': passed if ok else failed}


def verify(allow_ssh, desktop=False, run=_run, which=shutil.which,
           config_path=OPENSNITCH_CONFIG, home=None):
    """Read-only checks of UFW and OpenSnitch against what the stage configures."""
    checks = []
    ufw_installed = _installed(run, 'ufw')
    checks.append(_check('ufw-installed', ufw_installed, 'ufw-installed', 'ufw-not-installed'))
    if ufw_installed:
        code, out = run(['sudo', '-n', '/usr/sbin/ufw', 'status', 'verbose'])
        if code != 0:
            checks.append({'id': 'firewall:ufw-status', 'status': 'deferred',
                           'reason': 'ufw-status-needs-sudo-run-sudo-v-first'})
        else:
            ufw = parse_ufw(out)
            checks.append(_check('ufw-active', ufw['active'], 'ufw-enabled', 'ufw-not-enabled'))
            checks.append(_check('ufw-default-incoming', ufw['incoming'] == 'deny',
                                 'default-deny-incoming',
                                 'default-incoming-is-' + str(ufw['incoming'])))
            checks.append(_check('ufw-default-outgoing', ufw['outgoing'] == 'allow',
                                 'default-allow-outgoing',
                                 'default-outgoing-is-' + str(ufw['outgoing'])))
            if allow_ssh:
                checks.append(_check('ufw-ssh', ufw['ssh'], 'ssh-allowed-as-chosen',
                                     'ssh-chosen-but-no-ssh-rule'))
            else:
                checks.append(_check('ufw-ssh', not ufw['ssh'], 'ssh-not-allowed-as-chosen',
                                     'ssh-rule-present-but-ssh-not-chosen'))
    packages = [('opensnitch', 'opensnitch')] + ([('opensnitch-ui', UI_PACKAGE)] if desktop else [])
    for name, package in packages:
        ok = _installed(run, package)
        checks.append(_check(name + ('-installed' if name == 'opensnitch' else ''), ok,
                             package + '-installed', package + '-not-installed'))
    code, _ = run(['systemctl', 'is-active', 'opensnitch'])
    checks.append(_check('opensnitch-running', code == 0, 'opensnitch-active',
                         'opensnitch-service-not-active'))
    # Allow mode is a first-install default the operator later changes, so the
    # current mode is reported, never judged.
    try:
        action = load_json(config_path)[0].get('DefaultAction')
    except (OSError, InputError, ValueError, AttributeError):
        action = None
    checks.append({'id': 'firewall:opensnitch-daemon-mode', 'status': 'notice',
                   'reason': 'daemon-default-action-' + (action if isinstance(action, str)
                                                         else 'unreadable')})
    if desktop:
        base = Path(home) if home else Path.home()
        checks.append({'id': 'firewall:opensnitch-ui-mode', 'status': 'notice',
                       'reason': 'ui-default-action-' + ui_mode(ui_settings_path(base))})
    if which('docker'):
        checks.append({'id': 'firewall:docker-bypass', 'status': 'notice',
                       'reason': 'docker-published-ports-bypass-ufw-filter-them-in-the-docker-user-chain'})
    return checks
