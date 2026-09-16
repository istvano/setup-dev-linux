"""Verified local JDK registration through SDKMAN; Temurin 25 is the default."""
import json
import os
from pathlib import Path
import pwd
import subprocess
import uuid
from .artifacts import destination, install as install_artifacts, safe_path, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema
from .sdkman_runtime import directory, verify as verify_sdkman


def java_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/java-review.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    records = lock['artifacts']
    require([r['id'] for r in records] == ['temurin-25', 'temurin-21', 'microsoft-25', 'microsoft-21'], 'invalid-java-lock')
    for record in records:
        require(record['url'].startswith(('https://github.com/adoptium/', 'https://aka.ms/download-jdk/')) and
                record['format'] == 'tar' and record['entrypoint'].endswith('/bin/java'), 'unapproved-java-url')
    if entries:
        entry = entries['java']
        require(entry['owner'] == 'sdkman' and entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'sdkman' and entry['delivery']['version'] == records[0]['version'] and
                entry['licence']['status'] == 'reviewed' and entry['licence']['identifier'] == records[0]['licence'],
                'java-approval-mismatch')
    return records


def candidate_id(record):
    value = record['version'].replace('-', '.') + '-ws-' + ('tem' if record['id'].startswith('temurin') else 'ms')
    require(len(value) <= 20, 'sdkman-candidate-id-too-long')
    return value


def payload_home(home, record):
    return (destination(home, record) / record['entrypoint']).parent.parent


def candidates(home):
    path = directory(home) / 'candidates/java'
    safe_path(home, path)
    return path


def default_matches(current, versions, record):
    return current.is_symlink() and os.readlink(current) in (candidate_id(record), str(versions / candidate_id(record)))


def verify(home, selected):
    if 'java' not in selected:
        return []
    try:
        require('sdkman' in selected and verify_sdkman(home, selected)[0]['status'] == 'passed', 'java-requires-sdkman')
        records = java_lock()
        versions = candidates(home)
        for record in records:
            validate_payload(destination(home, record), record)
            link = versions / candidate_id(record)
            require(link.is_symlink() and os.readlink(link) == str(payload_home(home, record)), 'java-candidate-link-drift')
        require(default_matches(versions / 'current', versions, records[0]), 'java-default-drift')
        return [{'id': 'java', 'status': 'passed', 'reason': 'four-jdk-payloads-and-temurin25-default-match'}]
    except (InputError, OSError):
        return [{'id': 'java', 'status': 'failed', 'reason': 'java-runtime-registration-or-default-missing-modified'}]


def install(config, selected):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'java-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-java')
    home = Path(account.pw_dir)
    require('sdkman' in selected and verify_sdkman(home, selected)[0]['status'] == 'passed', 'java-requires-sdkman')
    records = java_lock()
    versions = candidates(home)
    for record in records:
        link = versions / candidate_id(record)
        if link.exists() or link.is_symlink():
            require(link.is_symlink() and os.readlink(link) == str(payload_home(home, record)), 'java-candidate-link-drift')
    current = versions / 'current'
    require(not current.exists() or current.is_symlink(), 'java-default-not-managed-link')
    changed = install_artifacts(records, config, allowed_url_prefixes=('https://github.com/adoptium/', 'https://aka.ms/download-jdk/'))
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('SDKMAN_', 'JAVA_', 'JDK_JAVA_', '_JAVA_')) and k not in ('BASH_ENV', 'ENV', 'CLASSPATH')}
    environment.update(SDKMAN_DIR=str(directory(home)))
    def sdk(command, *arguments):
        require(preflight(config)[1] == 0, 'storage-changed-before-java-registration')
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c',
                        'source "$SDKMAN_DIR/bin/sdkman-init.sh" && ' + command, '--', *arguments],
                       env=environment, check=True, capture_output=True, timeout=60)
    for record in records:
        link = versions / candidate_id(record)
        if not link.is_symlink():
            sdk('__sdkman_install_local_version java "$1" "$2"', candidate_id(record), str(payload_home(home, record)))
            changed = True
    if not default_matches(current, versions, records[0]):
        if current.is_symlink():
            backup = home / '.local/state/linux-os-setup/java-default-backups' / (uuid.uuid4().hex + '.json')
            safe_path(home, backup)
            backup.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
            with backup.open('x') as output:
                json.dump({'kind': 'symlink', 'target': os.readlink(current)}, output)
            backup.chmod(0o600)
        # Native SDKMAN tests exists(), which misses dangling symlinks and triggers
        # an unsafe copy fallback. The original link is already privately backed up.
        if current.is_symlink() and not current.exists():
            current.unlink()
        sdk('sdk default java "$1"', candidate_id(records[0]))
        changed = True
    require(verify(home, selected)[0]['status'] == 'passed', 'java-post-install-verification-failed')
    return changed
