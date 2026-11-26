"""The host firewall: UFW and OpenSnitch.

UFW denies incoming and allows outgoing; SSH is allowed only when the operator
chose it (`--allow-ssh`), and that choice is recorded in per-user state so a
later run without the flag does not silently remove the rule from a machine
the operator reaches over SSH. OpenSnitch is installed and running in allow
mode (`"DefaultAction": "allow"`): the setup, and the handoff to
setup-dev-linux-wsl that follows it, must never be blocked by a prompt nobody
is there to answer. Switching to deny is the operator's later decision, made
with the rules they have built up.

Docker's published ports bypass UFW: Docker writes its own packet-filter rules
ahead of UFW's. Docker is not installed here, so the notice is raised only when
it is present.

Everything in verify is read-only. `ufw status` needs root, so it goes through
`sudo -n`; where that is unavailable the check is deferred, never passed.
"""
import json
import re
import shutil
import subprocess

from . import state
from .config import InputError, load_json

PACKAGES = ['ufw', 'opensnitch', 'opensnitch-ebpf-modules']
UI_PACKAGE = 'python3-opensnitch-ui'
OPENSNITCH_CONFIG = '/etc/opensnitchd/default-config.json'
STATE_KEY = 'firewall'
UNREADABLE = 'recorded-firewall-unreadable; pass --allow-ssh or --no-allow-ssh'


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
    if not (isinstance(value, dict) and isinstance(value.get('allow_ssh'), bool)):
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


def record_allow_ssh(value):
    current = state.get(STATE_KEY)
    merged = dict(current) if isinstance(current, dict) else {}
    merged['allow_ssh'] = bool(value)
    state.set(STATE_KEY, merged)


def parse_ufw(text):
    """What `ufw status verbose` says: active, default policies, the OpenSSH rule."""
    active = re.search(r'^Status:\s*active\s*$', text, re.M) is not None
    defaults = re.search(r'^Default:\s*(.+)$', text, re.M)
    policies = {}
    if defaults:
        for policy, direction in re.findall(r'(\w+)\s*\((\w+)\)', defaults.group(1)):
            policies[direction] = policy
    ssh = any(re.match(r'(OpenSSH\b|\S+\s+\(OpenSSH\))', line) and 'ALLOW' in line
              for line in text.splitlines())
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
           config_path=OPENSNITCH_CONFIG):
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
                                     'ssh-chosen-but-no-openssh-rule'))
            else:
                checks.append(_check('ufw-ssh', not ufw['ssh'], 'ssh-not-allowed-as-chosen',
                                     'openssh-rule-present-but-ssh-not-chosen'))
    packages = [('opensnitch', 'opensnitch')] + ([('opensnitch-ui', UI_PACKAGE)] if desktop else [])
    for name, package in packages:
        ok = _installed(run, package)
        checks.append(_check(name + ('-installed' if name == 'opensnitch' else ''), ok,
                             package + '-installed', package + '-not-installed'))
    code, _ = run(['systemctl', 'is-active', 'opensnitch'])
    checks.append(_check('opensnitch-running', code == 0, 'opensnitch-active',
                         'opensnitch-service-not-active'))
    try:
        action = load_json(config_path)[0].get('DefaultAction')
    except (OSError, InputError, ValueError, AttributeError):
        action = None
    checks.append(_check('opensnitch-default-action', action == 'allow',
                         'default-action-allow',
                         'default-action-is-' + (str(action) if isinstance(action, str)
                                                 else 'unreadable')))
    if which('docker'):
        checks.append({'id': 'firewall:docker-bypass', 'status': 'notice',
                       'reason': 'docker-published-ports-bypass-ufw-filter-them-in-the-docker-user-chain'})
    return checks
