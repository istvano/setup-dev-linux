"""Pinned rustup/Rust delivery with local-only component acquisition."""
import hashlib
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tempfile
import tomllib
import urllib.parse
import urllib.request

from .artifacts import safe_path
from .config import ROOT, InputError, load_json, require, validate_schema
from .packages import verify_named_packages
from .prerequisites import registry as prerequisites


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def rust_lock(entries=None):
    lock, _ = load_json(ROOT / 'locks/rust.json')
    schema, _ = load_json(ROOT / 'locks/rust.schema.json')
    validate_schema(lock, schema)
    manager, toolchain = lock['manager'], lock['toolchain']
    require(manager['url'] ==
            f"https://static.rust-lang.org/rustup/archive/{manager['version']}/x86_64-unknown-linux-gnu/rustup-init",
            'unapproved-rustup-url')
    require(toolchain['manifest']['url'] ==
            f"https://static.rust-lang.org/dist/channel-rust-{toolchain['version']}.toml",
            'unapproved-rust-manifest-url')
    require(toolchain['manifest_checksum']['url'] == toolchain['manifest']['url'] + '.sha256',
            'unapproved-rust-manifest-checksum-url')
    components = {item['id']: item for item in toolchain['components']}
    require(set(components) == {'cargo', 'rust-std', 'rustc'} and
            len(components) == len(toolchain['components']), 'invalid-rust-components')
    for name, item in components.items():
        expected = (f"https://static.rust-lang.org/dist/{toolchain['date']}/"
                    f"{name}-{toolchain['version']}-{toolchain['host']}.tar.xz")
        require(item['url'] == expected, 'unapproved-rust-component-url')
    paths = [Path(item['path']) for item in toolchain['files']]
    require(len(paths) == len(set(paths)) and all(not path.is_absolute() and
            '..' not in path.parts and str(path) != '.' for path in paths),
            'unsafe-rust-payload-manifest')
    require({'bin/rustc', 'bin/cargo'} <= {str(path) for path in paths},
            'incomplete-rust-payload-manifest')
    if entries:
        entry = entries['rust']
        require(entry['owner'] == 'rustup' and entry['delivery']['status'] == 'verified' and
                entry['delivery']['channel'] == 'rustup' and
                entry['delivery']['version'] ==
                f"{toolchain['version']} / rustup {manager['version']}" and
                entry['licence']['status'] == 'reviewed' and
                entry['licence']['identifier'] == toolchain['licence'],
                'rust-approval-mismatch')
    return lock


def state_root(home, lock):
    path = (home / '.local/share/linux-os-setup/rust' /
            f"{lock['manager']['version']}-{lock['toolchain']['version']}")
    safe_path(home, path)
    return path


def cargo_home(home, lock):
    return state_root(home, lock) / 'cargo'


def rustup_home(home, lock):
    return state_root(home, lock) / 'rustup'


def toolchain_name(lock):
    return f"{lock['toolchain']['version']}-{lock['toolchain']['host']}"


def validate_manager(root, lock):
    cargo = root / 'cargo'
    rustup = root / 'rustup'
    binary = cargo / 'bin/rustup'
    require(cargo.is_dir() and not cargo.is_symlink() and
            rustup.is_dir() and not rustup.is_symlink() and
            binary.is_file() and not binary.is_symlink() and
            bool(binary.stat().st_mode & 0o111) and
            digest(binary) == lock['manager']['sha256'], 'rustup-manager-drift')
    expected = {'rustup', *lock['manager']['shims']}
    actual = {path.name for path in (cargo / 'bin').iterdir()}
    require(actual == expected, 'rustup-shim-drift')
    for name in lock['manager']['shims']:
        path = cargo / 'bin' / name
        require(path.is_symlink() and os.readlink(path) == 'rustup',
                'rustup-shim-drift')
    settings = rustup / 'settings.toml'
    require(settings.is_file() and not settings.is_symlink(), 'rustup-settings-drift')
    value = tomllib.loads(settings.read_text())
    require(set(value) == {'version', 'default_toolchain', 'profile', 'overrides'} and
            value['default_toolchain'] == toolchain_name(lock) and
            value['profile'] == 'minimal' and value['overrides'] == {},
            'rustup-settings-drift')


def validate_toolchain(root, lock):
    target = root / 'rustup/toolchains' / toolchain_name(lock)
    require(target.is_dir() and not target.is_symlink(), 'rust-toolchain-drift')
    expected = {item['path']: item for item in lock['toolchain']['files']}
    actual = {str(path.relative_to(target)) for path in target.rglob('*')
              if path.is_symlink() or not path.is_dir()}
    require(actual == set(expected), 'rust-toolchain-drift')
    for relative, item in expected.items():
        path = target / relative
        require(path.is_file() and not path.is_symlink() and
                path.resolve().is_relative_to(target.resolve()) and
                digest(path) == item['sha256'] and
                bool(path.stat().st_mode & 0o111) == item['executable'],
                'rust-toolchain-drift')


def prerequisites_pass(selected):
    return all(item['status'] == 'passed'
               for item in verify_named_packages([r['package'] for r in prerequisites()['rust']]))


def verify(home, selected):
    if 'rust' not in selected:
        return []
    try:
        require(prerequisites_pass(selected), 'rust-prerequisite-failed')
        lock = rust_lock()
        root = state_root(home, lock)
        validate_manager(root, lock)
        validate_toolchain(root, lock)
        return [{'id': 'rust', 'status': 'passed',
                 'reason': 'rustup-manager-default-and-full-toolchain-match'}]
    except (InputError, OSError, UnicodeError, tomllib.TOMLDecodeError):
        return [{'id': 'rust', 'status': 'failed',
                 'reason': 'rust-runtime-or-prerequisite-missing-modified'}]


def download(source, output):
    require(source['url'].startswith('https://static.rust-lang.org/'),
            'unapproved-rust-download-url')
    with urllib.request.urlopen(source['url'], timeout=60) as response, output.open('xb') as stream:
        shutil.copyfileobj(response, stream)
    require(digest(output) == source['sha256'], 'rust-download-digest-mismatch')


def install(config, selected):
    from .storage import preflight
    account = pwd.getpwuid(os.geteuid())
    require(os.geteuid() != 0 and account.pw_name == config['target']['user'],
            'rust-target-user-required')
    require(preflight(config)[1] == 0, 'storage-changed-before-rust')
    require(prerequisites_pass(selected), 'rust-prerequisite-failed')
    lock = rust_lock()
    home = Path(account.pw_dir)
    target = state_root(home, lock)
    if target.exists():
        validate_manager(target, lock)
        validate_toolchain(target, lock)
        return False
    target.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    target.parent.chmod(0o700)
    with tempfile.TemporaryDirectory(prefix='.rust-staging-', dir=target.parent) as temporary:
        staging = Path(temporary)
        inputs = staging / 'inputs'
        dist = inputs / 'dist'
        dated = dist / lock['toolchain']['date']
        dated.mkdir(parents=True)
        manager = inputs / 'rustup-init'
        download(lock['manager'], manager)
        manager.chmod(0o755)
        manifest = dist / f"channel-rust-{lock['toolchain']['version']}.toml"
        download(lock['toolchain']['manifest'], manifest)
        checksum = manifest.with_suffix(manifest.suffix + '.sha256')
        download(lock['toolchain']['manifest_checksum'], checksum)
        require(checksum.read_text() ==
                f"{lock['toolchain']['manifest']['sha256']}  {manifest.name}\n",
                'rust-manifest-checksum-content-mismatch')
        for component in lock['toolchain']['components']:
            download(component, dated / Path(urllib.parse.urlsplit(component['url']).path).name)
        require(preflight(config)[1] == 0, 'storage-changed-before-rust-execution')
        runtime = staging / 'runtime'
        cargo = runtime / 'cargo'
        rustup = runtime / 'rustup'
        environment = {key: value for key, value in os.environ.items()
                       if not key.startswith(('RUSTUP_', 'CARGO_')) and
                       key not in ('RUSTC', 'RUSTDOC', 'RUSTFLAGS')}
        environment.update(HOME=str(home), CARGO_HOME=str(cargo), RUSTUP_HOME=str(rustup),
                           RUSTUP_INIT_SKIP_PATH_CHECK='yes',
                           RUSTUP_DIST_SERVER=inputs.as_uri(),
                           RUSTUP_UPDATE_ROOT=(inputs / 'rustup').as_uri())
        subprocess.run([str(manager), '-y', '--no-modify-path', '--default-toolchain',
                        'none', '--profile', 'minimal'], check=True, env=environment,
                       capture_output=True, timeout=60)
        command = cargo / 'bin/rustup'
        subprocess.run([str(command), 'toolchain', 'install', lock['toolchain']['version'],
                        '--profile', 'minimal', '--no-self-update'], check=True,
                       env=environment, capture_output=True, timeout=300)
        subprocess.run([str(command), 'default', lock['toolchain']['version']], check=True,
                       env=environment, capture_output=True, timeout=60)
        env_file = cargo / 'env'
        if env_file.exists():
            env_file.unlink()
        validate_manager(runtime, lock)
        validate_toolchain(runtime, lock)
        require(preflight(config)[1] == 0, 'storage-changed-before-rust-placement')
        runtime.rename(target)
    require(verify(home, selected)[0]['status'] == 'passed',
            'rust-post-install-verification-failed')
    return True
