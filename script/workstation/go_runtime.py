"""Reviewed Go toolchain delivery with read-only full-payload verification."""
from pathlib import Path
import os
import pwd

from .artifacts import destination, install as install_artifacts, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema


def go_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/go.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    require(len(lock['artifacts']) == 1 and lock['artifacts'][0]['id'] == 'go',
            'invalid-go-lock')
    record = lock['artifacts'][0]
    require(record['url'] == 'https://go.dev/dl/' + record['version'] + '.linux-amd64.tar.gz' and
            record['format'] == 'tar' and record['entrypoint'] == 'go/bin/go',
            'unapproved-go-url-or-layout')
    if entries:
        entry = entries['go']
        require(entry['owner'] == 'ansible' and
                entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'upstream-release' and
                entry['delivery']['version'] == record['version'] and
                entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == record['licence'],
                'go-approval-mismatch')
    return record


def verify(home, selected):
    if 'go' not in selected:
        return []
    try:
        record = go_lock()
        validate_payload(destination(home, record), record)
        return [{'id': 'go', 'status': 'passed',
                 'reason': 'go-toolchain-full-payload-matches'}]
    except (InputError, OSError):
        return [{'id': 'go', 'status': 'failed',
                 'reason': 'go-toolchain-missing-modified'}]


def install(config):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'go-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-go')
    record = go_lock()
    changed = install_artifacts([record], config,
                                allowed_url_prefixes=('https://go.dev/dl/',))
    require(verify(Path(account.pw_dir), ['go'])[0]['status'] == 'passed',
            'go-post-install-verification-failed')
    return changed
