"""Reviewed OpenCode CLI artifact; no agent launch in independent verification."""
from pathlib import Path
import os
import pwd

from .artifacts import destination, install as install_artifacts, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema


def opencode_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/opencode.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    require(len(lock['artifacts']) == 1 and lock['artifacts'][0]['id'] == 'opencode',
            'invalid-opencode-lock')
    record = lock['artifacts'][0]
    require(record['version'] == '1.18.31' and
            record['url'] == 'https://github.com/anomalyco/opencode/releases/download/v1.18.31/opencode-linux-x64-baseline.tar.gz' and
            record['entrypoint'] == 'opencode' and record['format'] == 'tar' and
            len(record['files']) == 1 and record['files'][0]['path'] == 'opencode' and
            record['files'][0]['kind'] == 'file' and record['files'][0]['executable'],
            'unapproved-opencode-source-or-layout')
    if entries:
        entry = entries['opencode']
        require(entry['owner'] == 'ansible' and
                entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'upstream-release' and
                entry['delivery']['version'] == record['version'] and
                entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == record['licence'],
                'opencode-approval-mismatch')
    return record


def verify(home, selected):
    if 'opencode' not in selected:
        return []
    try:
        record = opencode_lock()
        validate_payload(destination(home, record), record)
        return [{'id': 'opencode', 'status': 'passed',
                 'reason': 'opencode-full-payload-matches'}]
    except (InputError, OSError):
        return [{'id': 'opencode', 'status': 'failed',
                 'reason': 'opencode-missing-modified'}]


def install(config):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'opencode-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-opencode')
    record = opencode_lock()
    changed = install_artifacts([record], config,
                                allowed_url_prefixes=('https://github.com/anomalyco/opencode/releases/download/',))
    require(verify(Path(account.pw_dir), ['opencode'])[0]['status'] == 'passed',
            'opencode-post-install-verification-failed')
    return changed
