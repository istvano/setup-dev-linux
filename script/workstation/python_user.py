"""Pinned user uv and CPython; Ansible sequences delivery, verifier never repairs."""
import os
from pathlib import Path
import pwd
import shutil
import hashlib
import subprocess
import tempfile
import urllib.request

from .artifacts import destination, digest, install as install_artifacts, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema

PYTHON_NAME = 'cpython-3.14.7-linux-x86_64-gnu'
ARCHIVE_NAME = 'cpython-3.14.7+20260901-x86_64-unknown-linux-gnu-install_only_stripped.tar.gz'
SYSCONFIG = PYTHON_NAME + '/lib/python3.14/_sysconfigdata__linux_x86_64-linux-gnu.py'
PREFIX_MARKER = b'@MANAGED_PYTHON_PREFIX@'


def python_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/python-user.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    require([r['id'] for r in lock['artifacts']] == ['uv', 'python'],
            'invalid-python-user-lock')
    uv, python = lock['artifacts']
    require(uv['version'] == '0.12.13' and
            uv['url'] == 'https://github.com/astral-sh/uv/releases/download/0.12.13/uv-x86_64-unknown-linux-gnu.tar.gz' and
            uv['entrypoint'] == 'uv-x86_64-unknown-linux-gnu/uv' and
            uv['format'] == 'tar', 'unapproved-user-uv-source')
    require(python['version'] == '3.14.7+20260901' and
            python['url'] == 'https://github.com/astral-sh/python-build-standalone/releases/download/20260901/' + ARCHIVE_NAME.replace('+', '%2B') and
            python['entrypoint'] == PYTHON_NAME + '/bin/python3.14' and
            python['format'] == 'tar' and
            any(f['path'] == PYTHON_NAME + '/lib/python3.14/LICENSE.txt' and
                f['value'] == python['licence_sha256'] for f in python['files']),
            'unapproved-user-python-source')
    for record in (uv, python):
        require(record['entrypoint'] in {f['path'] for f in record['files']} and
                len({f['path'] for f in record['files']}) == len(record['files']),
                'invalid-user-python-manifest')
        require(all(not Path(f['path']).is_absolute() and
                    '..' not in Path(f['path']).parts for f in record['files']),
                'unsafe-user-python-manifest')
    require(any(f['path'] == 'cpython-3.14-linux-x86_64-gnu' and
                f['kind'] == 'symlink' and f['value'] == PYTHON_NAME
                for f in python['files']), 'missing-user-python-alias')
    if entries:
        for record, owner, channel in ((uv, 'ansible', 'upstream-release'),
                                       (python, 'uv', 'uv-python')):
            entry = entries[record['id']]
            require(entry['owner'] == owner and
                    entry['delivery']['status'] == 'verified' and
                    entry['delivery']['channel'] == channel and
                    entry['delivery']['version'] == record['version'] and
                    entry['licence']['status'] == 'reviewed' and
                    entry['licence']['identifier'] == record['licence'],
                    'user-python-approval-mismatch')
    return uv, python


def validate_python_payload(path, record, final_path=None):
    """Complete file tree; generated sysconfig has one approved path substitution."""
    require(path.is_dir() and not path.is_symlink(), 'missing-user-python')
    require(all(not (directory.stat().st_mode & 0o222)
                for directory in [path, *(p for p in path.rglob('*')
                                           if p.is_dir() and not p.is_symlink())]),
            'user-python-writable-tree')
    actual = {str(p.relative_to(path)) for p in path.rglob('*')
              if p.is_symlink() or not p.is_dir()}
    require(actual == {f['path'] for f in record['files']},
            'user-python-tree-drift')
    expected_dirs = {str(parent) for member in record['files']
                     for parent in Path(member['path']).parents if str(parent) != '.'}
    actual_dirs = {str(p.relative_to(path)) for p in path.rglob('*')
                   if p.is_dir() and not p.is_symlink()}
    require(actual_dirs == expected_dirs, 'user-python-directory-drift')
    prefix = str((final_path or path) / PYTHON_NAME).encode()
    for member in record['files']:
        file = path / member['path']
        require(file.resolve().is_relative_to(path.resolve()),
                'unsafe-user-python-member')
        if member['kind'] == 'symlink':
            require(file.is_symlink() and os.readlink(file) == member['value'],
                    'user-python-tree-drift')
            continue
        require(file.is_file() and not file.is_symlink() and
                bool(file.stat().st_mode & 0o111) == member['executable'] and
                not (file.stat().st_mode & 0o222),
                'user-python-tree-drift')
        if member['path'] == SYSCONFIG:
            content = file.read_bytes()
            require(prefix in content and PREFIX_MARKER not in content,
                    'user-python-prefix-drift')
            measured = hashlib.sha256(content.replace(prefix, PREFIX_MARKER)).hexdigest()
        else:
            measured = digest(file)
        require(measured == member['value'], 'user-python-tree-drift')


def verify(home, selected):
    records = python_lock()
    checks = []
    for record in records:
        if record['id'] not in selected:
            continue
        try:
            target = destination(home, record)
            if record['id'] == 'python':
                validate_python_payload(target, record)
            else:
                validate_payload(target, record)
            checks.append({'id': record['id'], 'status': 'passed',
                           'reason': 'user-runtime-full-payload-matches'})
        except (InputError, OSError):
            checks.append({'id': record['id'], 'status': 'failed',
                           'reason': 'user-runtime-missing-modified'})
    return checks


def seal_python_payload(path):
    """Keep runtime source files read-only; venvs and project caches live elsewhere."""
    for member in path.rglob('*'):
        if not member.is_symlink():
            member.chmod(member.stat().st_mode & ~0o222)
    path.chmod(path.stat().st_mode & ~0o222)


def install(config, selected):
    from .storage import preflight
    require('uv' in selected,
            'python-runtime-selection-required')
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'python-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-user-python')
    home = Path(account.pw_dir)
    uv, python = python_lock()
    changed = install_artifacts([uv], config,
                                allowed_url_prefixes=('https://github.com/astral-sh/uv/releases/download/',))
    if 'python' not in selected:
        require(verify(home, ['uv'])[0]['status'] == 'passed',
                'user-uv-post-install-verification-failed')
        return changed
    uv_bin = destination(home, uv) / uv['entrypoint']
    target = destination(home, python)
    if target.exists():
        validate_python_payload(target, python)
    else:
        target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
        with tempfile.TemporaryDirectory(prefix='.staging-', dir=target.parent) as temporary:
            stage = Path(temporary)
            mirror = stage / 'mirror' / '20260901'
            mirror.mkdir(parents=True)
            archive = mirror / ARCHIVE_NAME
            with urllib.request.urlopen(python['url'], timeout=60) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
            require(digest(archive) == python['sha256'], 'user-python-download-digest-mismatch')
            payload = stage / 'payload'
            environment = {key: value for key, value in os.environ.items()
                           if not key.startswith(('UV_', 'PYTHON', 'PIP_', 'VIRTUAL_ENV', 'CONDA_', 'RYE_'))}
            environment.update({'UV_CACHE_DIR': str(stage / 'cache'),
                                'UV_PYTHON_INSTALL_DIR': str(payload),
                                'UV_PYTHON_DOWNLOADS': 'manual'})
            subprocess.run([str(uv_bin), 'python', 'install', '3.14.7', '--no-bin',
                            '--mirror', (stage / 'mirror').as_uri(), '--no-cache',
                            '--no-config', '--offline'], env=environment,
                           stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                           check=True, timeout=180)
            alias = payload / 'cpython-3.14-linux-x86_64-gnu'
            require(alias.is_symlink() and alias.resolve() == payload / PYTHON_NAME,
                    'user-python-install-layout-mismatch')
            alias.unlink()
            alias.symlink_to(PYTHON_NAME)
            for sidecar in ('.lock', '.gitignore'):
                (payload / sidecar).unlink(missing_ok=True)
            (payload / '.temp').rmdir()
            sysconfig = payload / SYSCONFIG
            staged_prefix = str(payload / PYTHON_NAME).encode()
            final_prefix = str(target / PYTHON_NAME).encode()
            original = sysconfig.read_bytes()
            require(staged_prefix in original and final_prefix not in original,
                    'user-python-staged-prefix-missing')
            sysconfig.write_bytes(original.replace(staged_prefix, final_prefix))
            seal_python_payload(payload)
            validate_python_payload(payload, python, target)
            require(preflight(config)[1] == 0, 'storage-changed-before-user-python-placement')
            # Moving a directory into a different parent rewrites its own ".."
            # entry, which the kernel refuses without write permission on the
            # directory being moved. The tree is validated sealed and restored to
            # the same mode once it is in place; the only writable window is
            # inside this process's private staging directory.
            sealed_mode = payload.stat().st_mode
            payload.chmod(sealed_mode | 0o200)
            payload.rename(target)
            target.chmod(sealed_mode)
            changed = True
    require(all(c['status'] == 'passed' for c in verify(home, selected)),
            'user-python-post-install-verification-failed')
    return changed
