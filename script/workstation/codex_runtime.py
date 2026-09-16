"""Reviewed Codex CLI artifact; independent verification never launches the agent."""
import os
from pathlib import Path
import pwd
import shutil
import tarfile
import tempfile
import urllib.request

from .artifacts import destination, digest, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema

ARCHIVE_MEMBER = 'codex-x86_64-unknown-linux-musl'
ARCHIVE_SIZE_LIMIT = 130 * 1024 * 1024
EXECUTABLE_SIZE = 262858016


def codex_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/codex.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    require(len(lock['artifacts']) == 1 and lock['artifacts'][0]['id'] == 'codex',
            'invalid-codex-lock')
    record = lock['artifacts'][0]
    require(record['version'] == '0.154.0' and
            record['url'] == 'https://github.com/openai/codex/releases/download/rust-v0.154.0/codex-x86_64-unknown-linux-musl.tar.gz' and
            record['format'] == 'tar' and record['entrypoint'] == 'codex' and
            len(record['files']) == 1 and record['files'][0]['path'] == 'codex' and
            record['files'][0]['kind'] == 'file' and record['files'][0]['executable'],
            'unapproved-codex-source-or-layout')
    if entries:
        entry = entries['codex']
        require(entry['owner'] == 'ansible' and
                entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'upstream-release' and
                entry['delivery']['version'] == record['version'] and
                entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == record['licence'],
                'codex-approval-mismatch')
    return record


def verify(home, selected):
    if 'codex' not in selected:
        return []
    try:
        record = codex_lock()
        validate_payload(destination(home, record), record)
        return [{'id': 'codex', 'status': 'passed',
                 'reason': 'codex-full-payload-matches'}]
    except (InputError, OSError):
        return [{'id': 'codex', 'status': 'failed',
                 'reason': 'codex-missing-modified'}]


def extract_exact(archive, payload, record):
    with tarfile.open(archive, mode='r:gz') as source:
        members = source.getmembers()
        require(len(members) == 1 and members[0].name == ARCHIVE_MEMBER and
                members[0].isfile() and members[0].size == EXECUTABLE_SIZE,
                'unexpected-codex-archive-layout')
        stream = source.extractfile(members[0])
        require(stream is not None, 'unreadable-codex-archive-member')
        with stream, (payload / 'codex').open('xb') as output:
            shutil.copyfileobj(stream, output)
    (payload / 'codex').chmod(0o755)
    validate_payload(payload, record)


def install(config):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'codex-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-codex')
    record = codex_lock()
    home = Path(account.pw_dir)
    target = destination(home, record)
    if target.exists():
        validate_payload(target, record)
        return False
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.staging-', dir=target.parent) as temporary:
        staging = Path(temporary)
        archive = staging / 'download'
        require(record['url'].startswith('https://github.com/openai/codex/releases/download/'),
                'unapproved-codex-url')
        with urllib.request.urlopen(record['url'], timeout=60) as response, archive.open('xb') as output:
            copied = 0
            while chunk := response.read(1024 * 1024):
                copied += len(chunk)
                require(copied <= ARCHIVE_SIZE_LIMIT, 'codex-download-too-large')
                output.write(chunk)
        require(digest(archive) == record['sha256'], 'codex-download-digest-mismatch')
        payload = staging / 'payload'
        payload.mkdir(mode=0o700)
        extract_exact(archive, payload, record)
        require(preflight(config)[1] == 0, 'storage-changed-before-codex-placement')
        payload.rename(target)
    require(verify(home, ['codex'])[0]['status'] == 'passed',
            'codex-post-install-verification-failed')
    return True
