"""Read-only storage guard. Test inventory injection is not exposed by the CLI."""
import json
import os
from pathlib import Path
import platform
import pwd
import subprocess
from .config import InputError


class InspectionError(Exception):
    pass


def capture(args):
    try:
        return json.loads(subprocess.check_output(args, text=True, stderr=subprocess.DEVNULL,
                          timeout=15, env={'PATH': '/usr/sbin:/usr/bin:/sbin:/bin', 'LC_ALL': 'C'}))
    except (OSError, subprocess.SubprocessError, ValueError):
        raise InspectionError from None


def inventory(config):
    try:
        release = {}
        for line in Path('/etc/os-release').read_text().splitlines():
            if '=' in line:
                key, value = line.split('=', 1)
                release[key] = value.strip('"')
        user = pwd.getpwnam(config['target']['user'])
        home = Path(user.pw_dir)
        user_valid = user.pw_uid > 0 and home.is_dir() and home.stat().st_uid == user.pw_uid
        user_valid = user_valid and home.is_absolute() and home.resolve() == home
        user_valid = user_valid and home.is_relative_to('/home') and home != Path('/home')
    except (OSError, KeyError):
        raise InputError('target-user-or-platform-unavailable') from None
    aliases = {}
    for d in config['storage']['disks'].values():
        try:
            aliases[d['stable_id']] = str(Path(d['stable_id']).resolve(strict=True))
        except OSError:
            aliases[d['stable_id']] = None
    return {'os': release.get('ID'), 'release': release.get('VERSION_ID'),
            'architecture': platform.machine(), 'user_valid': user_valid, 'user_home': str(home),
            'aliases': aliases,
            'devices': capture(['/usr/bin/lsblk', '--json', '--list', '--bytes', '--paths',
                                '--output', 'NAME,TYPE,SIZE,UUID,PKNAME'])['blockdevices'],
            'mounts': capture(['/usr/bin/findmnt', '--json', '--list', '--output',
                              'TARGET,SOURCE,FSTYPE,OPTIONS,UUID,FSROOT'])['filesystems']}


def assess(config, observed):
    checks = []
    def check(id, valid, reason):
        checks.append({'id': id, 'status': 'passed' if valid else 'failed', 'reason': reason})
    if (observed['os'], observed['release'], observed['architecture']) != ('ubuntu', '26.04', 'x86_64'):
        return [{'id': 'platform', 'status': 'failed', 'reason': 'unsupported-platform'}], 2
    if not observed['user_valid']:
        return [{'id': 'target-user', 'status': 'failed', 'reason': 'target-home-or-account-invalid'}], 2
    check('platform-user', True, 'supported-platform-and-nonroot-user')
    storage = config['storage']
    devices = {d['name']: d for d in observed['devices']}
    check('device-inventory', len(devices) == len(observed['devices']), 'device-inventory-must-be-unambiguous')
    roles = {}
    for role, declaration in storage['disks'].items():
        name = observed['aliases'].get(declaration['stable_id'])
        device = devices.get(name, {})
        valid = device.get('type') == 'disk' and int(device.get('size') or 0) >= declaration['minimum_bytes']
        check('disk-' + role, valid, 'whole-disk-identity-and-capacity')
        roles[role] = name if valid else None
    check('distinct-disks', len(set(roles.values())) == len(roles) and None not in roles.values(), 'physical-role-uniqueness')
    def physical(name):
        seen = set()
        while name in devices and name not in seen:
            seen.add(name)
            d = devices[name]
            if d['type'] == 'disk':
                return name
            if d['type'] != 'part':
                return None  # Unsupported mapper/RAID ancestry must not guess a disk.
            name = d.get('pkname')
        return None
    mounts = observed['mounts']
    by_target = {}
    for m in mounts:
        by_target.setdefault(m['target'], []).append(m)
    for path, declaration in storage['mounts'].items():
        nodes = [d for d in devices.values() if d.get('uuid') == declaration['filesystem_uuid']]
        exact = by_target.get(path, [])
        valid = len(nodes) == 1 and len(exact) == 1
        if valid:
            mount = exact[0]
            valid = (mount.get('uuid') == declaration['filesystem_uuid']
                     and physical(nodes[0]['name']) == roles[declaration['disk_role']]
                     and mount.get('source') == nodes[0]['name']
                     and mount.get('fsroot') == '/'
                     and 'rw' in mount.get('options', '').split(','))
        check('mount-' + path, valid, 'exact-writable-filesystem-on-declared-disk')
    def nearest(path):
        matches = [m for m in mounts if path == m['target'] or path.startswith(m['target'].rstrip('/') + '/')]
        return max(matches, key=lambda m: len(m['target'])) if matches else {}
    if not storage['separate_var_lib']:
        actual = nearest('/var/lib')
        check('var-lib-on-root', actual.get('target') == '/' and actual.get('uuid') == storage['mounts']['/']['filesystem_uuid'], 'var-lib-must-remain-on-root')
    actual = nearest(observed['user_home'])
    check('target-home-storage', actual.get('target') == '/home' and actual.get('uuid') == storage['mounts']['/home']['filesystem_uuid'], 'target-home-must-use-verified-home-filesystem')
    # Nested mounts may redirect package databases, logs or user-tool installations.
    protected = ['/var/lib', '/var/log', '/usr', '/opt', '/etc', observed['user_home']]
    unexpected = [m for m in mounts if m['target'] not in storage['mounts'] and any(
        m['target'] == p or m['target'].startswith(p.rstrip('/') + '/') or
        (m['target'] != '/' and p.startswith(m['target'].rstrip('/') + '/')) for p in protected)]
    check('managed-path-mounts', not unexpected, 'no-unreviewed-mounts-under-managed-paths')
    if any(c['status'] == 'failed' for c in checks):
        return checks, 1
        return checks, 3
    return checks, 0


def preflight(config):
    try:
        return assess(config, inventory(config))
    except InspectionError:
        return [{'id': 'inventory', 'status': 'failed', 'reason': 'required-storage-inspection-unavailable'}], 2
