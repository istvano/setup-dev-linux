"""Pinned Node through offline NVM installation; no controller dependency in verify."""
import os
from pathlib import Path
import pwd
import subprocess
import urllib.request
import shutil
import uuid
from .artifacts import digest, destination, safe_path, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema


def node_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/node.json')
    schema, _ = load_json(ROOT / 'locks/user-tools.schema.json')
    validate_schema(lock, schema)
    require(len(lock['artifacts']) == 1 and lock['artifacts'][0]['id'] == 'node', 'invalid-node-lock')
    record = lock['artifacts'][0]
    require(record['url'] == 'https://nodejs.org/dist/' + record['version'] + '/node-' + record['version'] + '-linux-x64.tar.xz', 'unapproved-node-url')
    if entries:
        entry = entries['node']
        require(entry['owner'] == 'nvm' and entry['licence']['status'] == 'reviewed' and entry['delivery']['status'] == 'verified' and entry['delivery']['channel'] == 'nvm' and entry['delivery']['version'] == record['version'] and entry['licence']['identifier'] == record['licence'], 'node-lock-approval-mismatch')
    return record


def nvm_directory(home):
    path = home / '.local/share/linux-os-setup/nvm'
    safe_path(home, path)
    return path


def verify(home, tools, selected):
    if 'node' not in selected:
        return []
    try:
        require('nvm' in selected, 'node-requires-selected-nvm')
        record = node_lock()
        nvm = nvm_directory(home)
        target = nvm / 'versions/node' / record['version']
        safe_path(home, target)
        validate_payload(target, record)
        alias = nvm / 'alias/default'
        safe_path(home, alias)
        require(alias.read_text().strip() == record['version'], 'node-default-drift')
        manager = destination(home, tools['nvm']) / Path(tools['nvm']['entrypoint']).parent
        for name in ['nvm.sh', 'nvm-exec']:
            require((nvm / name).is_symlink() and os.readlink(nvm / name) == str(manager / name), 'nvm-link-drift')
        return [{'id': 'node', 'status': 'passed', 'reason': 'pinned-node-payload-and-nvm-default-match'}]
    except (InputError, OSError):
        return [{'id': 'node', 'status': 'failed', 'reason': 'node-runtime-or-default-missing-modified'}]


def install(config, selected, tools):
    from .storage import preflight
    require('nvm' in selected, 'node-requires-selected-nvm')
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'node-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-node')
    home = Path(account.pw_dir)
    record = node_lock()
    nvm = nvm_directory(home)
    target = nvm / 'versions/node' / record['version']
    safe_path(home, target)
    manager = destination(home, tools['nvm'])
    validate_payload(manager, tools['nvm'])
    manager = manager / Path(tools['nvm']['entrypoint']).parent
    changed = False
    nvm.mkdir(parents=True, mode=0o700, exist_ok=True)
    for name in ['nvm.sh', 'nvm-exec']:
        link = nvm / name
        if link.is_symlink():
            require(os.readlink(link) == str(manager / name), 'nvm-link-drift')
        else:
            require(not link.exists(), 'nvm-manager-file-conflict')
            link.symlink_to(manager / name)
            changed = True
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('NVM_', 'NPM_CONFIG_', 'npm_config_')) and k not in ('BASH_ENV', 'ENV')}
    environment.update(NVM_DIR=str(nvm), NVM_NO_COLORS='1', NVM_NO_PROGRESS='1')
    if target.exists():
        validate_payload(target, record)
    else:
        slug = 'node-' + record['version'] + '-linux-x64'
        archive = nvm / '.cache/bin' / slug / (slug + '.tar.xz')
        safe_path(home, archive)
        archive.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        if not archive.exists():
            partial = archive.with_suffix('.partial')
            safe_path(home, partial)
            with urllib.request.urlopen(record['url'], timeout=60) as response, partial.open('wb') as output:
                shutil.copyfileobj(response, output)
            require(digest(partial) == record['sha256'], 'node-download-digest-mismatch')
            partial.rename(archive)
        require(digest(archive) == record['sha256'], 'node-cache-digest-mismatch')
        require(preflight(config)[1] == 0, 'storage-changed-before-nvm-install')
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', '. "$NVM_DIR/nvm.sh" --no-use && nvm install --offline -b "$1"', '--', record['version']],
                       env=environment, check=True, capture_output=True, timeout=180)
        validate_payload(target, record)
        changed = True
    alias = nvm / 'alias/default'
    safe_path(home, alias)
    if not alias.exists() or alias.read_text().strip() != record['version']:
        if alias.exists():
            backup = home / '.local/state/linux-os-setup/node-default-backups' / uuid.uuid4().hex
            safe_path(home, backup)
            backup.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            backup.write_bytes(alias.read_bytes())
            backup.chmod(0o600)
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c', '. "$NVM_DIR/nvm.sh" --no-use && nvm alias default "$1"', '--', record['version']],
                       env=environment, check=True, capture_output=True, timeout=30)
        changed = True
    return changed
