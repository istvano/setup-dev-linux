"""Mandrel as an additional SDKMAN JDK; never changes the Java default."""
import os
from pathlib import Path
import pwd
import subprocess
from .artifacts import destination, install as install_artifacts, safe_path, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema
from .java_runtime import verify as verify_java
from .sdkman_runtime import directory
from .packages import verify_named_packages
from .prerequisites import registry as prerequisites


def mandrel_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/mandrel.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    require(len(lock['artifacts']) == 1 and lock['artifacts'][0]['id'] == 'mandrel', 'invalid-mandrel-lock')
    record = lock['artifacts'][0]
    require(record['url'].startswith('https://github.com/graalvm/mandrel/') and record['format'] == 'tar', 'unapproved-mandrel-url')
    if entries:
        entry = entries['mandrel']
        require(entry['owner'] == 'sdkman' and entry['delivery']['status'] == 'verified' and
                entry['delivery']['version'] == record['version'] and entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == record['licence'], 'mandrel-approval-mismatch')
    return record


def candidate_id(record):
    value = record['version'].removesuffix('-Final') + '-ws-mandrel'
    require(len(value) <= 20, 'sdkman-candidate-id-too-long')
    return value


def paths(home, record):
    versions = directory(home) / 'candidates/java'
    safe_path(home, versions)
    return versions / candidate_id(record), (destination(home, record) / record['entrypoint']).parent.parent


def prerequisites_pass(home, selected):
    return ({'sdkman', 'java'} <= set(selected) and verify_java(home, selected)[0]['status'] == 'passed' and
            all(c['status'] == 'passed' for c in verify_named_packages([r['package'] for r in prerequisites()['mandrel']])))


def verify(home, selected):
    if 'mandrel' not in selected:
        return []
    try:
        require(prerequisites_pass(home, selected), 'mandrel-prerequisite-failed')
        record = mandrel_lock()
        validate_payload(destination(home, record), record)
        link, payload = paths(home, record)
        require(link.is_symlink() and os.readlink(link) == str(payload), 'mandrel-registration-drift')
        return [{'id': 'mandrel', 'status': 'passed', 'reason': 'mandrel-payload-registration-and-native-prerequisites-match'}]
    except (InputError, OSError):
        return [{'id': 'mandrel', 'status': 'failed', 'reason': 'mandrel-or-prerequisite-missing-modified'}]


def install(config, selected):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'mandrel-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-mandrel')
    home = Path(account.pw_dir)
    require(prerequisites_pass(home, selected), 'mandrel-prerequisite-failed')
    record = mandrel_lock()
    link, payload = paths(home, record)
    if link.exists() or link.is_symlink():
        require(link.is_symlink() and os.readlink(link) == str(payload), 'mandrel-registration-drift')
    changed = install_artifacts([record], config, allowed_url_prefixes=('https://github.com/graalvm/mandrel/',))
    if not link.is_symlink():
        environment = {k: v for k, v in os.environ.items() if not k.startswith(('SDKMAN_', 'JAVA_', 'JDK_JAVA_', '_JAVA_')) and k not in ('BASH_ENV', 'ENV', 'CLASSPATH')}
        environment.update(SDKMAN_DIR=str(directory(home)))
        require(preflight(config)[1] == 0, 'storage-changed-before-mandrel-registration')
        subprocess.run(['/bin/bash', '--noprofile', '--norc', '-c',
                        'source "$SDKMAN_DIR/bin/sdkman-init.sh" && __sdkman_install_local_version java "$1" "$2"',
                        '--', candidate_id(record), str(payload)], env=environment, check=True, capture_output=True, timeout=60)
        changed = True
    require(verify(home, selected)[0]['status'] == 'passed', 'mandrel-post-install-verification-failed')
    return changed
