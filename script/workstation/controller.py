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


FIREWALL_PLAYBOOK = 'firewall.yml'
FIREWALL_TIMEOUT = 1800


def host_stages(selection, root=ROOT):
    """The stages a selection runs, in order: (id, playbooks, timeout).

    Pure: reads the manifest, runs nothing. The base groups make the package
    stage run on every selection. Snaps are desktop software and run only with
    the desktop set; VS Code extensions only with dev-gui; GNOME settings only
    with desktop. A stage with no playbooks is run by the controller itself.
    """
    groups = set(selection['groups'])
    profiles = set(selection['profiles'])
    snaps, _ = load_json(Path(root) / 'manifest/snaps.json')
    binaries, _ = load_json(Path(root) / 'manifest/binaries.json')
    packages = ['repositories.yml', 'manifest-packages.yml']
    if selection['desktop'] and any(s['group'] in groups for s in snaps['snaps']):
        packages.append('snaps.yml')
    if any(b['group'] in groups for b in binaries['binaries']):
        packages.append('binaries.yml')
    stages = [
        # Distribution assertions first: nothing should be installed on a host
        # this repository does not support.
        ('foundation', ['foundation.yml'], 300),
        # Recorded before anything installs, so a re-run without --profiles
        # continues this selection even when this run stops part-way.
        ('record-selection', [], 0),
        # Network-bound and far slower than the rest; its timeout suits it.
        ('packages', packages, 7200),
        # Group membership follows the packages that create the groups. It only
        # takes effect in a later session anyway.
        ('system-groups', ['system-groups.yml'], 300),
    ]
    # Editor extensions need VS Code, which the package stage installed.
    if 'dev-gui' in profiles:
        stages.append(('plugins', ['plugins.yml'], 3600))
    # Desktop settings configure packages installed above.
    if 'desktop' in profiles:
        stages.append(('desktop', ['desktop.yml'], 300))
    if 'firewall' in selection['stages']:
        stages.append(('firewall', [FIREWALL_PLAYBOOK], FIREWALL_TIMEOUT))
    return stages


def apply_firewall_stage(run_stage, config):
    """The firewall stage: UFW and OpenSnitch (ansible/firewall.yml).

    The SSH choice and the desktop flag reach the playbook as extra variables
    (apply_foundation writes them), so the hook needs only the playbook.
    """
    run_stage([FIREWALL_PLAYBOOK], FIREWALL_TIMEOUT)


def record_selection(selection, allow_ssh=None):
    """Record the chosen profiles in per-user state, outside the clone.

    Verification then checks the machine this is, not the machine the manifest
    could describe, and a re-run without --profiles keeps this selection even
    after the clone or its .workstation directory is gone.
    """
    from . import state
    state.set('profiles', list(selection['profiles']))
    # Only an explicit --allow-ssh / --no-allow-ssh is recorded, and only when
    # the firewall is part of this selection; absent both, the recorded value
    # keeps holding so an omitted flag never removes the SSH rule.
    if allow_ssh is not None and 'firewall' in selection['stages']:
        from . import firewall
        firewall.record_allow_ssh(allow_ssh)


def run_host_stages(selection, run_stage, record, config, root=ROOT):
    """Run each stage of the selection in order; a failing stage raises."""
    for stage, playbooks, timeout in host_stages(selection, root):
        if stage == 'record-selection':
            record()
        elif stage == 'firewall':
            apply_firewall_stage(run_stage, config)
        else:
            run_stage(playbooks, timeout)


def apply_foundation(config, root=ROOT, selection=None, allow_ssh=False,
                     allow_ssh_explicit=False):
    require(selection is not None and selection['groups'], 'no-profile-selected')
    require(os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == config['target']['user'], 'controller-must-run-as-target-user')
    lock = validate_lock(root)  # Check frozen-input binding before the first write.
    state = root / '.workstation'
    require(not state.is_symlink(), 'unsafe-controller-path')
    if state.exists():
        require(state.stat().st_uid == os.geteuid(), 'controller-state-owner-mismatch')
    state.mkdir(mode=0o700, exist_ok=True)
    state.chmod(0o700)
    for name in ['venv', 'uv-cache', 'ansible-local', 'ansible-remote', 'foundation.log',
                 'ansible-vars.json']:
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
        variables = state / 'ansible-vars.json'
        variables.write_text(json.dumps({'workstation_root': str(root), 'workstation_config': config,
                                         'host_profiles': selection['profiles'],
                                         'manifest_groups': selection['groups'],
                                         'selected_repositories': selection['repositories'],
                                         'firewall_allow_ssh': bool(allow_ssh),
                                         'host_desktop': bool(selection['desktop'])}))
        variables.chmod(0o600)
        extra = ['--extra-vars', '@' + str(variables)]

        def run_stage(names, timeout):
            subprocess.run([str(state / 'venv/bin/ansible-playbook'), '-i', 'localhost,',
                            *[str(root / 'ansible' / n) if not n.startswith('/') else n
                              for n in names], *extra],
                           cwd=root, check=True, env=environment,
                           stdout=output, stderr=subprocess.STDOUT, timeout=timeout)

        run_host_stages(selection, run_stage, lambda: record_selection(
            selection, allow_ssh if allow_ssh_explicit else None), config, root)
    return {'id': 'controller-foundation', 'status': 'passed', 'reason': 'locked-controller-and-distribution-python-assertions-passed'}
