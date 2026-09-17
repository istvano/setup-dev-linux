"""Agent CLIs published as an npm entry package plus a Linux platform package.

Both tarballs are pinned by SHA-256, which covers every file inside them, and
the executable's own digest is recorded so replacement after installation is
detectable. Nothing resolves versions at install time and npm is never invoked:
the recorded tarballs are fetched and unpacked directly.

The payload is sealed read-only once in place, like the other user runtimes.
"""
import hashlib
import io
import json
import os
import shutil
import tarfile
import tempfile
import urllib.request
from pathlib import Path

from .config import ROOT, InputError, load_json, require

TOOLS = '.local/share/linux-os-setup/tools'
REGISTRY = 'https://registry.npmjs.org/'


def lock(identifier, root=ROOT):
    value, _ = load_json(Path(root) / 'locks' / f'{identifier}.json')
    require(value['schema_version'] == 1, f'unsupported-{identifier}-lock')
    require(value['id'] == identifier, f'{identifier}-lock-identity-mismatch')
    require(len(value['packages']) == 2, f'{identifier}-lock-must-pin-two-packages')
    for package in value['packages']:
        require(package['url'].startswith(REGISTRY), f'{identifier}-package-not-from-npm')
        require(len(package['sha256']) == 64, f'{identifier}-package-not-pinned')
    require(len(value['entrypoint_sha256']) == 64, f'{identifier}-entrypoint-not-pinned')
    require(not Path(value['entrypoint']).is_absolute()
            and '..' not in Path(value['entrypoint']).parts, f'{identifier}-unsafe-entrypoint')
    return value


def target(home, record):
    return Path(home) / TOOLS / record['id'] / record['version']


def executable(home, record):
    return target(home, record) / Path(record['entrypoint']).name


def fetch(package):
    with urllib.request.urlopen(package['url'], timeout=600) as response:
        data = response.read()
    if hashlib.sha256(data).hexdigest() != package['sha256']:
        raise InputError(f"{package['name']}-download-digest-mismatch")
    return data


def seal(path):
    """Runtime payloads stay read-only; nothing writes into them after install."""
    for member in path.rglob('*'):
        if not member.is_symlink():
            member.chmod(member.stat().st_mode & ~0o222)
    path.chmod(path.stat().st_mode & ~0o222)


def platform_package(record):
    return next(p for p in record['packages'] if p['name'] == record['platform_package'])


def install(home, identifier, root=ROOT):
    """Place the pinned executable. Returns True when anything changed."""
    record = lock(identifier, root)
    destination = target(home, record)
    if verify(home, identifier, root)[0]['status'] == 'passed':
        return False
    destination.parent.mkdir(parents=True, exist_ok=True, mode=0o700)

    for package in record['packages']:
        fetch(package)  # Both digests are checked; only the platform one is unpacked.
    data = fetch(platform_package(record))
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=destination.parent) as stage:
        payload = Path(stage) / 'payload'
        payload.mkdir(mode=0o700)
        with tarfile.open(fileobj=io.BytesIO(data)) as archive:
            member = archive.getmember(record['entrypoint'])
            with archive.extractfile(member) as stream:
                binary = payload / Path(record['entrypoint']).name
                binary.write_bytes(stream.read())
        if hashlib.sha256(binary.read_bytes()).hexdigest() != record['entrypoint_sha256']:
            raise InputError(f'{identifier}-entrypoint-digest-mismatch')
        binary.chmod(0o755)
        seal(payload)
        if destination.exists():
            shutil.rmtree(destination, ignore_errors=True)
        # Moving a directory into a new parent rewrites its own "..", which the
        # kernel refuses without write permission on the directory itself.
        sealed = payload.stat().st_mode
        payload.chmod(sealed | 0o200)
        payload.rename(destination)
        destination.chmod(sealed)
    return True


def verify(home, identifier, root=ROOT):
    try:
        record = lock(identifier, root)
    except (InputError, OSError, ValueError, KeyError):
        return [{'id': identifier, 'status': 'failed', 'reason': 'lock-unreadable-or-invalid'}]
    binary = executable(home, record)
    if not binary.is_file():
        return [{'id': identifier, 'status': 'failed', 'reason': 'not-installed'}]
    if not binary.stat().st_mode & 0o111:
        return [{'id': identifier, 'status': 'failed', 'reason': 'not-executable'}]
    with binary.open('rb') as stream:
        if hashlib.file_digest(stream, 'sha256').hexdigest() != record['entrypoint_sha256']:
            return [{'id': identifier, 'status': 'failed',
                     'reason': 'does-not-match-the-pinned-executable'}]
    return [{'id': identifier, 'status': 'passed',
             'reason': f"pinned-{record['version']}-present-and-unmodified"}]
