"""Reviewed Maven/Gradle/Kotlin archives, registered locally through SDKMAN."""
import json
import os
from pathlib import Path
import pwd
import subprocess
import uuid
from .artifacts import destination, install as install_artifacts, safe_path, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema
from .sdkman_runtime import directory
from .java_runtime import verify as verify_java

URL_PREFIXES = ('https://dlcdn.apache.org/maven/', 'https://services.gradle.org/distributions/',
                'https://github.com/JetBrains/kotlin/')
IDS = {'maven', 'gradle', 'kotlin'}


def tool_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/jvm-tools.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    records = lock['artifacts']
    require([r['id'] for r in records] == ['maven', 'gradle', 'kotlin'], 'invalid-jvm-tool-lock')
    for record, prefix in zip(records, URL_PREFIXES):
        require(record['url'].startswith(prefix), 'unapproved-jvm-tool-url')
        if entries:
            entry = entries[record['id']]
            require(entry['owner'] == 'sdkman' and entry['delivery']['status'] == 'verified' and
                    entry['delivery']['channel'] == 'sdkman' and entry['delivery']['version'] == record['version'] and
                    entry['licence']['status'] == 'reviewed' and entry['licence']['identifier'] == record['licence'],
                    'jvm-tool-approval-mismatch')
    return records


def candidate_id(record):
    value = record['version'] + '-ws'
    require(len(value) <= 20, 'sdkman-candidate-id-too-long')
    return value


def paths(home, record):
    versions = directory(home) / 'candidates' / record['id']
    safe_path(home, versions)
    payload = (destination(home, record) / record['entrypoint']).parent.parent
    return versions, payload


def default_matches(versions, record):
    current = versions / 'current'
    return current.is_symlink() and os.readlink(current) in (candidate_id(record), str(versions / candidate_id(record)))


def verify(home, selected):
    records = [r for r in tool_lock() if r['id'] in selected]
    if not records:
        return []
    prerequisites = {'sdkman', 'java'} <= set(selected) and verify_java(home, selected)[0]['status'] == 'passed'
    checks = []
    for record in records:
        try:
            require(prerequisites, 'jvm-tool-requires-java-and-sdkman')
            validate_payload(destination(home, record), record)
            versions, payload = paths(home, record)
            link = versions / candidate_id(record)
            require(link.is_symlink() and os.readlink(link) == str(payload), 'jvm-tool-registration-drift')
            require(default_matches(versions, record), 'jvm-tool-default-drift')
            checks.append({'id': record['id'], 'status': 'passed', 'reason': 'jvm-tool-payload-registration-default-match'})
        except (InputError, OSError):
            checks.append({'id': record['id'], 'status': 'failed', 'reason': 'jvm-tool-or-prerequisite-missing-modified'})
    return checks


def install(config, selected):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'jvm-tool-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-jvm-tools')
    home = Path(account.pw_dir)
    require({'sdkman', 'java'} <= set(selected) and verify_java(home, selected)[0]['status'] == 'passed',
            'jvm-tool-requires-java-and-sdkman')
    records = [r for r in tool_lock() if r['id'] in selected]
    for record in records:
        versions, payload = paths(home, record)
        link = versions / candidate_id(record)
        if link.exists() or link.is_symlink():
            require(link.is_symlink() and os.readlink(link) == str(payload), 'jvm-tool-registration-drift')
        current = versions / 'current'
        require(not current.exists() or current.is_symlink(), 'jvm-tool-default-not-managed-link')
    changed = install_artifacts(records, config, allowed_url_prefixes=URL_PREFIXES)
    environment = {k: v for k, v in os.environ.items() if not k.startswith(('SDKMAN_', 'JAVA_', 'JDK_JAVA_', '_JAVA_')) and k not in ('BASH_ENV', 'ENV', 'CLASSPATH')}
    environment.update(SDKMAN_DIR=str(directory(home)))
    def sdk(command, *arguments):
        require(preflight(config)[1] == 0, 'storage-changed-before-jvm-tool-registration')
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c',
                        'source "$SDKMAN_DIR/bin/sdkman-init.sh" && ' + command, '--', *arguments],
                       env=environment, check=True, capture_output=True, timeout=60)
    for record in records:
        versions, payload = paths(home, record)
        link = versions / candidate_id(record)
        if not link.is_symlink():
            sdk('__sdkman_install_local_version "$1" "$2" "$3"', record['id'], candidate_id(record), str(payload))
            changed = True
        if not default_matches(versions, record):
            current = versions / 'current'
            if current.is_symlink():
                backup = home / '.local/state/linux-os-setup/jvm-tool-default-backups' / (uuid.uuid4().hex + '.json')
                safe_path(home, backup)
                backup.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
                with backup.open('x') as output:
                    json.dump({'candidate': record['id'], 'kind': 'symlink', 'target': os.readlink(current)}, output)
                backup.chmod(0o600)
            # Native SDKMAN tests exists(), which misses dangling symlinks and triggers
            # an unsafe copy fallback. The original link is already privately backed up.
            if current.is_symlink() and not current.exists():
                current.unlink()
            sdk('sdk default "$1" "$2"', record['id'], candidate_id(record))
            changed = True
    require(all(c['status'] == 'passed' for c in verify(home, selected)), 'jvm-tool-post-install-verification-failed')
    return changed
