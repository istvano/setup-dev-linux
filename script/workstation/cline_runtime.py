"""Pinned Cline CLI-only npm payload; verification never launches Node or Cline."""
import hashlib
import os
from pathlib import Path
import pwd
import shutil
import tarfile
import tempfile
import urllib.request

from .artifacts import destination, digest, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema
from .node_runtime import node_lock, verify as verify_node

VERSION = '3.0.62'
MAX_ARCHIVE = {'cline': 1024 * 1024,
               '@cline/cli-linux-x64': 64 * 1024 * 1024}
MAX_UNPACKED = {'cline': 1024 * 1024,
                '@cline/cli-linux-x64': 180 * 1024 * 1024}


def launcher_text(node_version):
    return ('#!/bin/sh\nset -eu\n'
            'CLINE_NO_AUTO_UPDATE=1; export CLINE_NO_AUTO_UPDATE\n'
            'base=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd -P)\n'
            'exec "$HOME/.local/share/linux-os-setup/nvm/versions/node/' + node_version +
            '/bin/node" "$base/node_modules/cline/bin/cline" "$@"\n')


def sha512(path):
    with path.open('rb') as source:
        return hashlib.file_digest(source, 'sha512').hexdigest()


def nvm_record():
    value, _ = load_json(ROOT / 'locks/user-tools.json')
    return next(record for record in value['artifacts'] if record['id'] == 'nvm')


def cline_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/cline.json')
    schema, _ = load_json(ROOT / 'locks/cline.schema.json')
    validate_schema(lock, schema)
    require(lock['version'] == VERSION and lock['node_version'] == node_lock()['version'] and
            lock['id'] == 'cline' and len(lock['packages']) == 2,
            'invalid-cline-lock')
    expected = {
        'cline': ('https://registry.npmjs.org/cline/-/cline-' + VERSION + '.tgz',
                  'node_modules/cline'),
        '@cline/cli-linux-x64':
            ('https://registry.npmjs.org/@cline/cli-linux-x64/-/cli-linux-x64-' + VERSION + '.tgz',
             'node_modules/@cline/cli-linux-x64'),
    }
    require({p['name'] for p in lock['packages']} == set(expected),
            'invalid-cline-package-set')
    files = [{'path': 'bin/cline', 'kind': 'file', 'value': lock['launcher_sha256'],
              'executable': True}]
    for package in lock['packages']:
        require((package['url'], package['destination']) == expected[package['name']] and
                package['version'] == VERSION and package['members'],
                'unapproved-cline-source-or-layout')
        names = [m['path'] for m in package['members']]
        require(len(names) == len(set(names)) and all(name.startswith('package/') and
                '..' not in Path(name).parts and not Path(name).is_absolute() and
                '\\' not in name for name in names), 'unsafe-cline-lock-member')
        require('package/package.json' in names and 'package/bin/cline' in names,
                'incomplete-cline-package')
        for member in package['members']:
            files.append({'path': package['destination'] + '/' + member['path'][len('package/'):],
                          'kind': 'file', 'value': member['sha256'],
                          'executable': member['executable']})
    require(len({m['path'] for m in files}) == len(files) and
            lock['launcher_sha256'] == hashlib.sha256(
                launcher_text(lock['node_version']).encode()).hexdigest(),
            'invalid-cline-payload-manifest')
    if entries:
        entry = entries['cline']
        require(entry['owner'] == 'ansible' and
                entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'isolated-npm' and
                entry['delivery']['version'] == VERSION and
                entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == lock['licence'],
                'cline-approval-mismatch')
    return lock, {'id': 'cline', 'version': VERSION, 'files': files,
                  'entrypoint': 'bin/cline'}


def verify(home, selected):
    if 'cline' not in selected:
        return []
    try:
        require({'node', 'nvm'} <= set(selected), 'cline-requires-selected-node')
        lock, record = cline_lock()
        require(verify_node(home, {'nvm': nvm_record()}, selected)[0]['status'] == 'passed',
                'cline-node-prerequisite-drift')
        validate_payload(destination(home, record), record)
        return [{'id': 'cline', 'status': 'passed',
                 'reason': 'cline-cli-complete-payload-and-pinned-node-match'}]
    except (InputError, OSError, KeyError):
        return [{'id': 'cline', 'status': 'failed',
                 'reason': 'cline-cli-or-node-missing-modified'}]


def extract_exact(archive, payload, package):
    """Reject a whole hostile member list before writing any destination file."""
    with tarfile.open(archive, mode='r:gz') as source:
        members = source.getmembers()
        locked = {m['path']: m for m in package['members']}
        names = [m.name for m in members]
        require(len(names) == len(locked) and len(names) == len(set(names)) and
                set(names) == set(locked), 'unexpected-cline-archive-layout')
        require(all(m.isfile() and m.size == locked[m.name]['size'] for m in members) and
                sum(m.size for m in members) <= MAX_UNPACKED[package['name']],
                'unsafe-cline-archive-member')
        for member in members:
            target = payload / package['destination'] / member.name[len('package/'):]
            target.parent.mkdir(parents=True, exist_ok=True, mode=0o700)
            stream = source.extractfile(member)
            require(stream is not None, 'unreadable-cline-archive-member')
            with stream, target.open('xb') as output:
                shutil.copyfileobj(stream, output)
            target.chmod(0o755 if locked[member.name]['executable'] else 0o644)
            require(digest(target) == locked[member.name]['sha256'],
                    'cline-extracted-member-digest-mismatch')


def download_exact(package, path):
    require(package['url'].startswith('https://registry.npmjs.org/'),
            'unapproved-cline-download-url')
    with urllib.request.urlopen(package['url'], timeout=60) as response, path.open('xb') as output:
        copied = 0
        while chunk := response.read(1024 * 1024):
            copied += len(chunk)
            require(copied <= MAX_ARCHIVE[package['name']],
                    'cline-download-too-large')
            output.write(chunk)
    require(digest(path) == package['sha256'] and sha512(path) == package['sha512'],
            'cline-download-digest-mismatch')


def install(config, selected):
    from .storage import preflight
    require({'cline', 'node', 'nvm'} <= set(selected),
            'cline-requires-selected-node')
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'cline-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-cline')
    home = Path(account.pw_dir)
    lock, record = cline_lock()
    require(verify_node(home, {'nvm': nvm_record()}, selected)[0]['status'] == 'passed',
            'cline-node-prerequisite-drift')
    target = destination(home, record)
    if target.exists() or target.is_symlink():
        validate_payload(target, record)
        return False
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=target.parent) as temporary:
        staging = Path(temporary)
        payload = staging / 'payload'
        payload.mkdir(mode=0o700)
        for index, package in enumerate(lock['packages']):
            archive = staging / ('source-' + str(index) + '.tgz')
            download_exact(package, archive)
            extract_exact(archive, payload, package)
        launcher = payload / 'bin/cline'
        launcher.parent.mkdir(mode=0o700)
        launcher.write_text(launcher_text(lock['node_version']))
        launcher.chmod(0o755)
        validate_payload(payload, record)
        require(preflight(config)[1] == 0, 'storage-changed-before-cline-placement')
        payload.rename(target)
    require(verify(home, selected)[0]['status'] == 'passed',
            'cline-post-install-verification-failed')
    return True
