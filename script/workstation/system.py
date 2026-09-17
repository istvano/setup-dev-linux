"""System settings the manifest declares beyond packages.

Installing docker is not the same as being able to use it. The package creates
the group; something has to put the operator in it, and the membership only
takes effect in a session started afterwards. Reporting "installed" while
`docker ps` fails is the first-day confusion this exists to prevent.

Verification distinguishes three states, because they need different actions:
the user is not in the group at all (the install did not finish), the user is in
the group but this session predates it (log out and back in), or the membership
is effective and the socket answers.
"""
import grp
import json
import os
import pwd
import shutil
import subprocess
from pathlib import Path

from .config import ROOT, load_json


def manifest(root=ROOT):
    value, _ = load_json(Path(root) / 'manifest/system.json')
    return value


def declared_groups(root=ROOT, groups=None):
    """Group memberships whose owning manifest group is selected."""
    return [record for record in manifest(root)['user_groups']
            if groups is None or record['requires_manifest_group'] in groups]


def group_members(name):
    try:
        return set(grp.getgrnam(name).gr_mem)
    except KeyError:
        return None


def primary_group(user):
    try:
        account = pwd.getpwnam(user)
        return grp.getgrgid(account.pw_gid).gr_name
    except KeyError:
        return None


def session_groups():
    """Groups effective in this process, which a stale session will not include."""
    try:
        return {grp.getgrgid(gid).gr_name for gid in os.getgroups()}
    except (KeyError, OSError):
        return set()


def socket_reachable():
    """Whether the Docker socket answers as this user, without sudo."""
    if shutil.which('docker') is None:
        return None
    try:
        result = subprocess.run(['docker', 'version', '--format', '{{.Server.Version}}'],
                                capture_output=True, text=True, check=False, timeout=30)
    except (OSError, subprocess.SubprocessError):
        return False
    return result.returncode == 0


def verify(user, root=ROOT, groups=None):
    records = declared_groups(root, groups)
    if not records:
        return []
    checks = []
    failures = 0
    for record in records:
        name = record['group']
        identifier = f'group:{name}'
        members = group_members(name)
        if members is None:
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'group-does-not-exist'})
            failures += 1
            continue
        if user not in members and primary_group(user) != name:
            checks.append({'id': identifier, 'status': 'failed',
                           'reason': 'user-is-not-a-member'})
            failures += 1
            continue
        if name not in session_groups():
            # The install is correct; this session simply predates it.
            checks.append({'id': identifier, 'status': 'deferred',
                           'reason': f"granted-but-effective-after-{record['effective_after']}"
                                     .replace(' ', '-')})
            continue
        if name == 'docker':
            reachable = socket_reachable()
            if reachable is False:
                checks.append({'id': identifier, 'status': 'failed',
                               'reason': 'member-but-the-docker-socket-refused'})
                failures += 1
                continue
            if reachable is None:
                checks.append({'id': identifier, 'status': 'deferred',
                               'reason': 'docker-not-installed'})
                continue
        checks.append({'id': identifier, 'status': 'passed',
                       'reason': 'member-and-effective-in-this-session'})
    checks.append({'id': 'system-groups',
                   'status': 'failed' if failures else 'passed',
                   'reason': f'{len(records) - failures}-of-{len(records)}-granted'})
    return checks
