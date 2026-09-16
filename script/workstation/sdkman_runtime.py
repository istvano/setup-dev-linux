"""Guarded SDKMAN manager delivery; candidate runtimes have separate delivery gates."""
import os
from pathlib import Path
import pwd
import shutil
import tempfile
from .artifacts import destination, install as install_artifacts, safe_path, validate_payload
from .config import ROOT, InputError, load_json, require, validate_schema

POLICY = '''sdkman_auto_answer=true
sdkman_selfupdate_feature=false
sdkman_auto_env=false
sdkman_auto_complete=false
sdkman_healthcheck_enable=false
sdkman_native_enable=true
sdkman_insecure_ssl=false
sdkman_checksum_enable=true
'''


def manager_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/sdkman-review.json')
    validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
    records = lock['artifacts']
    require([r['id'] for r in records] == ['sdkman-cli', 'sdkman-native'], 'invalid-sdkman-lock')
    for record in records:
        require(record['url'].startswith('https://github.com/sdkman/') and record['format'] == 'zip', 'unapproved-sdkman-url')
    if entries:
        entry = entries['sdkman']
        require(entry['owner'] == 'ansible' and entry['delivery']['status'] == 'verified' and
                entry['delivery']['version'] == records[0]['version'] and
                entry['licence']['status'] == 'reviewed' and entry['licence']['identifier'] == 'Apache-2.0',
                'sdkman-approval-mismatch')
    return records


def directory(home):
    path = home / '.local/share/linux-os-setup/sdkman'
    safe_path(home, path)
    return path


def metadata(records):
    return {'etc/config': POLICY, 'var/platform': 'linuxx64\n',
            'var/candidates': 'java,maven,gradle,kotlin\n',
            'var/version': records[0]['version'] + '\n',
            'var/version_native': records[1]['version'] + '\n'}


def verify_manager(home, manager, records):
    safe_path(home, manager)
    require(manager.is_dir(), 'missing-sdkman-manager')
    for record in records:
        for component in {Path(m['path']).parts[1] for m in record['files']}:
            payload = manager / component
            safe_path(home, payload)
            files = [dict(m, path=str(Path(*Path(m['path']).parts[2:])))
                     for m in record['files'] if Path(m['path']).parts[1] == component]
            validate_payload(payload, {'files': files})
    for relative, value in metadata(records).items():
        target = manager / relative
        safe_path(home, target)
        require(target.is_file() and target.read_text() == value and target.stat().st_mode & 0o777 == 0o600,
                'sdkman-policy-or-metadata-drift')
    for name in ('ext', 'tmp', 'candidates', 'var'):
        safe_path(home, manager / name)
        require((manager / name).is_dir(), 'sdkman-state-directory-missing')
    require(not any((manager / 'ext').iterdir()), 'unreviewed-sdkman-extension')


def verify(home, selected):
    if 'sdkman' not in selected:
        return []
    try:
        records = manager_lock()
        for record in records:
            validate_payload(destination(home, record), record)
        verify_manager(home, directory(home), records)
        return [{'id': 'sdkman', 'status': 'passed', 'reason': 'sdkman-manager-payload-policy-match'}]
    except (InputError, OSError):
        return [{'id': 'sdkman', 'status': 'failed', 'reason': 'sdkman-manager-missing-modified'}]


def install(config):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'], 'sdkman-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-sdkman')
    home = Path(account.pw_dir)
    records = manager_lock()
    target = directory(home)
    # Refuse modified managed state before acquiring or writing anything else.
    if target.exists():
        verify_manager(home, target, records)
    changed = install_artifacts(records, config)
    if target.exists():
        return changed
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='.sdkman-staging-', dir=target.parent) as temporary:
        staging = Path(temporary) / 'manager'
        staging.mkdir(mode=0o700)
        for record in records:
            source = destination(home, record) / Path(record['entrypoint']).parts[0]
            for component in source.iterdir():
                shutil.copytree(component, staging / component.name)
        for name in ('etc', 'var', 'ext', 'tmp', 'candidates'):
            (staging / name).mkdir(mode=0o700, exist_ok=True)
        for relative, value in metadata(records).items():
            target_file = staging / relative
            target_file.write_text(value)
            target_file.chmod(0o600)
        (staging / 'var/delay_upgrade').touch(mode=0o600)
        verify_manager(home, staging, records)
        require(preflight(config)[1] == 0, 'storage-changed-before-sdkman-placement')
        staging.rename(target)
    return True
