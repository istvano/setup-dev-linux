"""Reviewed immutable user-tool payloads; Ansible owns invocation and sequencing."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import stat
import sys
import tarfile
import tempfile
import urllib.request
import zipfile
from .config import ROOT, InputError, load_json, require, validate_schema


def registry(entries, root=ROOT):
    value, _ = load_json(root / 'locks/user-tools.json')
    schema, _ = load_json(root / 'locks/user-tools.schema.json')
    validate_schema(value, schema)
    result = {r['id']: r for r in value['artifacts']}
    require(len(result) == len(value['artifacts']), 'duplicate-user-tool')
    for key, record in result.items():
        entry = entries[key]
        require(entry['kind'] == 'package' and entry['owner'] == 'ansible' and entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'upstream-release' and
                entry['delivery']['version'] == record['version'] and
                entry['licence']['status'] == 'reviewed' and entry['licence']['identifier'] == record['licence'], 'user-tool-approval-mismatch')
        require(record['version'] not in ('.', '..'), 'unsafe-user-tool-version')
        require(record['entrypoint'] in {m['path'] for m in record['files']}, 'missing-artifact-entrypoint')
        for member in record['files']:
            path = Path(member['path'])
            require(not path.is_absolute() and '..' not in path.parts and str(path) != '.', 'unsafe-artifact-member')
        require(len({m['path'] for m in record['files']}) == len(record['files']), 'duplicate-artifact-member')
    return result


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def safe_path(home, path):
    require(path.is_relative_to(home) and not home.is_symlink(), 'unsafe-user-tool-path')
    for parent in [path, *path.parents]:
        if parent == home:
            break
        require(not parent.is_symlink(), 'unsafe-user-tool-path')


def destination(home, record):
    path = home / '.local/share/linux-os-setup/tools' / record['id'] / record['version']
    safe_path(home, path)
    return path


def validate_payload(path, record):
    require(path.is_dir() and not path.is_symlink(), 'missing-user-tool')
    actual = {str(p.relative_to(path)) for p in path.rglob('*') if p.is_symlink() or not p.is_dir()}
    require(actual == {m['path'] for m in record['files']}, 'user-tool-tree-drift')
    for member in record['files']:
        target = path / member['path']
        require(target.resolve().is_relative_to(path.resolve()), 'unsafe-artifact-member')
        if member['kind'] == 'symlink':
            require(target.is_symlink() and os.readlink(target) == member['value'], 'user-tool-tree-drift')
        else:
            require(target.is_file() and not target.is_symlink() and digest(target) == member['value'] and
                    bool(target.stat().st_mode & 0o111) == member['executable'], 'user-tool-tree-drift')


def verify(records, home):
    checks = []
    for record in records:
        try:
            validate_payload(destination(home, record), record)
            status, reason = 'passed', 'reviewed-user-tool-payload-matches'
        except (InputError, OSError):
            status, reason = 'failed', 'missing-or-modified-user-tool'
        checks.append({'id': record['id'], 'status': status, 'reason': reason})
    return checks


def extract_zip(archive, payload):
    """Extract reviewed regular ZIP payloads without path normalization surprises."""
    with zipfile.ZipFile(archive) as source:
        members = source.infolist()
        names = set()
        for member in members:
            name = member.filename.rstrip('/')
            path = Path(name)
            require(name and not path.is_absolute() and '..' not in path.parts and
                    str(path) == name and '\\' not in name and '\x00' not in name,
                    'unsafe-artifact-member')
            require(name not in names, 'duplicate-artifact-member')
            names.add(name)
            mode = member.external_attr >> 16
            kind = stat.S_IFMT(mode)
            require(kind in (0, stat.S_IFDIR if member.is_dir() else stat.S_IFREG),
                    'unsafe-artifact-member')
        # Validate the complete member list before any extraction writes.
        for member in members:
            target = payload / member.filename
            if member.is_dir():
                target.mkdir(parents=True, exist_ok=True, mode=0o755)
            else:
                target.parent.mkdir(parents=True, exist_ok=True, mode=0o755)
                with source.open(member) as input_stream, target.open('xb') as output:
                    shutil.copyfileobj(input_stream, output)
                target.chmod(0o755 if (member.external_attr >> 16) & 0o111 else 0o644)


def install(records, config, *, allowed_url_prefixes=('https://github.com/',)):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'user-tool-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-user-tools')
    home = Path(account.pw_dir)
    changed = False
    for record in records:
        target = destination(home, record)
        if target.exists():
            validate_payload(target, record)
            continue
        target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.staging-', dir=target.parent) as temporary:
            staging = Path(temporary)
            archive = staging / 'download'
            require(record['url'].startswith(allowed_url_prefixes), 'unapproved-user-tool-url')
            with urllib.request.urlopen(record['url'], timeout=60) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
            require(digest(archive) == record['sha256'], 'user-tool-download-digest-mismatch')
            payload = staging / 'payload'
            payload.mkdir(mode=0o700)
            if record['format'] == 'binary':
                output = payload / record['entrypoint']
                archive.rename(output)
                output.chmod(0o755)
            elif record['format'] == 'zip':
                extract_zip(archive, payload)
            else:
                with tarfile.open(archive) as source:
                    source.extractall(payload, filter='data')
            validate_payload(payload, record)
            require(preflight(config)[1] == 0, 'storage-changed-before-user-tool-placement')
            payload.rename(target)
            changed = True
    return changed
