"""Guarded acquisition and execution of the isolated automation foundation."""
import hashlib
import json
import os
from pathlib import Path
import pwd
import shutil
import subprocess
import tarfile
import tempfile
import urllib.request
from .config import InputError, ROOT, load_json, require


def file_hash(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def validate_lock(root=ROOT):
    lock, _ = load_json(root / 'locks/bootstrap.json')
    require(lock['schema_version'] == 1, 'unsupported-bootstrap-lock')
    require(file_hash(root / 'pyproject.toml') == lock['project_sha256'], 'project-lock-drift')
    require(file_hash(root / 'uv.lock') == lock['uv_lock_sha256'], 'dependency-lock-drift')
    return lock


def verify_archive(path, expected):
    require(file_hash(path) == expected, 'bootstrap-artifact-digest-mismatch')


def download(artifact, target):
    if target.exists():
        verify_archive(target, artifact['sha256'])
        return
    require(artifact['url'].startswith('https://github.com/astral-sh/'), 'unapproved-bootstrap-source')
    partial = target.with_suffix('.partial')
    require(not partial.is_symlink(), 'unsafe-controller-path')
    with urllib.request.urlopen(artifact['url'], timeout=60) as response, partial.open('wb') as output:
        shutil.copyfileobj(response, output)
    verify_archive(partial, artifact['sha256'])
    partial.rename(target)


def validate_tree(archive, destination):
    """Check every archive member on reuse, including symlink targets; no done marker."""
    allowed = set()
    with tarfile.open(archive) as source:
        for member in source:
            path = destination / member.name
            relative = Path(member.name)
            allowed.add(relative)
            allowed.update(p for p in relative.parents if p != Path('.'))
            require(path.resolve().is_relative_to(destination.resolve()), 'unsafe-controller-member')
            if member.issym():
                require(path.is_symlink() and os.readlink(path) == member.linkname, 'controller-tree-drift')
            elif member.isfile() or member.islnk():
                require(path.is_file() and not path.is_symlink(), 'controller-tree-drift')
                with source.extractfile(member) as contents:
                    expected = hashlib.file_digest(contents, 'sha256').hexdigest()
                require(file_hash(path) == expected, 'controller-tree-drift')
            elif member.isdir():
                require(path.is_dir() and not path.is_symlink(), 'controller-tree-drift')
            else:
                raise InputError('unsupported-controller-archive-member')
    require(all(p.relative_to(destination) in allowed for p in destination.rglob('*')), 'unexpected-controller-runtime-file')


def unpack(archive, destination):
    if not destination.exists():
        with tempfile.TemporaryDirectory(dir=destination.parent) as temporary:
            with tarfile.open(archive) as source:
                source.extractall(temporary, filter='data')
            Path(temporary).rename(destination)
    validate_tree(archive, destination)


def apply_foundation(config, root=ROOT, manifest_groups=None):
    require(os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == config['target']['user'], 'controller-must-run-as-target-user')
    lock = validate_lock(root)  # Check frozen-input binding before the first write.
    state = root / '.workstation'
    require(not state.is_symlink(), 'unsafe-controller-path')
    if state.exists():
        require(state.stat().st_uid == os.geteuid(), 'controller-state-owner-mismatch')
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    for name in ['venv', 'uv-cache', 'ansible-local', 'ansible-remote', 'foundation.log', 'ansible-vars.json']:
        require(not (state / name).is_symlink(), 'unsafe-controller-path')
    executables = {}
    for key, artifact in lock['artifacts'].items():
        archive = state / (key + '-' + artifact['version'] + '.tar.gz')
        directory = state / (key + '-' + artifact['version'])
        require(not archive.is_symlink() and not directory.is_symlink(), 'unsafe-controller-path')
        download(artifact, archive)
        unpack(archive, directory)
        executable = directory / artifact['executable']
        require(file_hash(executable) == artifact['executable_sha256'], 'controller-executable-drift')
        executables[key] = executable
    environment = dict(os.environ)
    # Do not let external uv/Ansible/Python settings redirect the controller.
    for key in list(environment):
        if key.startswith(('UV_', 'ANSIBLE_', 'PYTHON')):
            del environment[key]
    environment.update({'UV_CACHE_DIR': str(state / 'uv-cache'), 'UV_PROJECT_ENVIRONMENT': str(state / 'venv'),
                        'UV_PYTHON_DOWNLOADS': 'never', 'PYTHONDONTWRITEBYTECODE': '1',
                        'ANSIBLE_LOCAL_TEMP': str(state / 'ansible-local'),
                        'ANSIBLE_REMOTE_TEMP': str(state / 'ansible-remote'),
                        'ANSIBLE_NOCOLOR': '1', 'ANSIBLE_CONFIG': str(root / 'ansible/ansible.cfg')})
    log = state / 'foundation.log'
    from .storage import preflight
    require(preflight(config)[1] == 0, 'storage-changed-before-controller-sync')
    with log.open('w') as output:
        log.chmod(0o600)
        subprocess.run([str(executables['uv']), 'sync', '--frozen', '--no-config', '--no-build', '--all-groups',
                        '--project', str(root), '--python', str(executables['python'])],
                       check=True, env=environment, stdout=output, stderr=subprocess.STDOUT, timeout=300)
        require(preflight(config)[1] == 0, 'storage-changed-before-ansible')
        extra = []
        if manifest_groups:
            variables = state / 'ansible-vars.json'
            variables.write_text(json.dumps({'workstation_root': str(root), 'workstation_config': config,
                                             'manifest_groups': manifest_groups}))
            variables.chmod(0o600)
            extra = ['--extra-vars', '@' + str(variables)]

        def run_stage(names, timeout):
            subprocess.run([str(state / 'venv/bin/ansible-playbook'), '-i', 'localhost,',
                            *[str(root / 'ansible' / n) if not n.startswith('/') else n
                              for n in names], *extra],
                           cwd=root, check=True, env=environment,
                           stdout=output, stderr=subprocess.STDOUT, timeout=timeout)

        # Distribution assertions first: nothing should be installed on a host
        # this repository does not support.
        run_stage([str(root / 'ansible/foundation.yml')], 300)

        # Packages next. This stage is network-bound and far slower than the
        # rest, so it gets a timeout that suits it.
        if manifest_groups:
            run_stage(['repositories.yml', 'manifest-packages.yml', 'snaps.yml',
                       'binaries.yml'], 7200)

        # Record what was applied so verification checks the machine this is,
        # not the machine the manifest could describe. Without it, verify
        # reports every group the operator deliberately did not install.
        if manifest_groups:
            applied = state / 'applied-groups.json'
            applied.write_text(json.dumps({'schema_version': 1,
                                           'groups': sorted(manifest_groups)}))
            applied.chmod(0o600)

        # Group membership follows the packages that create the groups, and
        # precedes nothing: it only takes effect in a later session anyway.
        if manifest_groups:
            run_stage(['system-groups.yml'], 300)

        # Editor extensions need VS Code, which the package stage installed.
        if manifest_groups and 'dev-gui' in manifest_groups:
            run_stage(['plugins.yml'], 3600)

        # Desktop settings last: they configure packages installed above.
        if manifest_groups and 'desktop' in manifest_groups:
            run_stage(['desktop.yml'], 300)
    return {'id': 'controller-foundation', 'status': 'passed', 'reason': 'locked-controller-and-distribution-python-assertions-passed'}
