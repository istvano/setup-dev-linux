"""Independent verification of manifest delivery beyond APT packages.

`bootstrap verify` reads the installed system and reports drift. Until now it
covered packages, user tools, runtimes and desktop settings, so a clean verify
did not mean the machine matched the manifest: the pinned binaries, the snaps
and the repositories they come from were checked only by the VM fixture.

Verification never repairs. Where a stronger check is available it is used: a
binary installed from a raw release asset is the asset, so its SHA-256 must
still equal the pin. Archives are unpacked, so only presence and executability
can be checked there.
"""
import hashlib
import json
import re
import subprocess
from pathlib import Path

from .config import ROOT, load_json

KEYRING_DIR = Path('/etc/apt/keyrings')
SOURCES_DIR = Path('/etc/apt/sources.list.d')
FINGERPRINT = re.compile(r'^[0-9A-F]{40}$')


def _load(name, root=ROOT):
    value, _ = load_json(Path(root) / 'manifest' / name)
    return value


def _summary(identifier, failures, total, subject):
    return {'id': identifier,
            'status': 'failed' if failures else 'passed',
            'reason': f'{total - failures}-of-{total}-{subject}'}


def digest(path):
    with path.open('rb') as stream:
        return hashlib.file_digest(stream, 'sha256').hexdigest()


def installed_packages():
    output = subprocess.run(['dpkg-query', '-W', '-f=${Package} ${Status}\n'],
                            capture_output=True, text=True, check=False).stdout
    return {line.split()[0] for line in output.splitlines()
            if line.strip().endswith('ok installed')}


def verify_binaries(root=ROOT, groups=None):
    """Every pinned artifact is present, executable and — where it is the
    downloaded asset itself — still the artifact that was pinned."""
    manifest = _load('binaries.json', root)
    wanted = [b for b in manifest['binaries']
              if groups is None or b['group'] in groups]
    if not wanted:
        return []
    install_dir = Path(manifest['install_dir'])
    present = installed_packages()
    checks, failures = [], 0
    for binary in sorted(wanted, key=lambda b: b['id']):
        identifier = f"binary:{binary['id']}"
        if binary['kind'] == 'deb':
            if binary['id'] not in present:
                checks.append({'id': identifier, 'status': 'failed',
                               'reason': 'vendor-package-not-installed'})
                failures += 1
            continue
        target = install_dir / binary['id']
        if not target.is_file():
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'missing'})
            failures += 1
        elif not target.stat().st_mode & 0o111:
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'not-executable'})
            failures += 1
        elif binary['kind'] == 'raw' and digest(target) != binary['sha256']:
            # A raw asset is installed verbatim, so the pin still describes it.
            checks.append({'id': identifier, 'status': 'failed',
                           'reason': 'does-not-match-the-pinned-checksum'})
            failures += 1
    checks.append(_summary('manifest-binaries', failures, len(wanted),
                           'pinned-binaries-present'))
    return checks


def verify_snaps(root=ROOT, groups=None):
    """Each declared snap is installed, on the channel the manifest declares."""
    manifest = _load('snaps.json', root)
    wanted = [s for s in manifest['snaps'] if groups is None or s['group'] in groups]
    if not wanted:
        return []
    listed = subprocess.run(['snap', 'list'], capture_output=True, text=True,
                            check=False)
    if listed.returncode != 0:
        return [{'id': 'manifest-snaps', 'status': 'failed',
                 'reason': 'snapd-unavailable'}]
    installed = {}
    for line in listed.stdout.splitlines()[1:]:
        fields = line.split()
        if len(fields) >= 4:
            installed[fields[0]] = fields[3]
    checks, failures = [], 0
    for snap in sorted(wanted, key=lambda s: s['name']):
        identifier = f"snap:{snap['name']}"
        if snap['name'] not in installed:
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'not-installed'})
            failures += 1
        elif installed[snap['name']] != snap['channel']:
            checks.append({'id': identifier, 'status': 'failed',
                           'reason': f"tracking-{installed[snap['name']]}-"
                                     f"not-{snap['channel']}"})
            failures += 1
    checks.append(_summary('manifest-snaps', failures, len(wanted), 'snaps-installed'))
    return checks


def key_fingerprint(path):
    result = subprocess.run(
        ['gpg', '--show-keys', '--with-colons', '--with-fingerprint', str(path)],
        capture_output=True, text=True, check=False)
    if result.returncode != 0:
        return None
    for line in result.stdout.splitlines():
        if line.startswith('fpr:'):
            value = line.split(':')[9]
            if FINGERPRINT.match(value):
                return value
    return None


def verify_repositories(root=ROOT):
    """Each declared repository has its recorded key installed.

    A source a vendor package manages is not checked for a source file: the
    repository was configured to obtain the package and then handed back, so the
    file is the vendor's and named as the vendor chose. Its key still has to be
    the recorded one.
    """
    manifest = _load('repositories.json', root)
    repositories = manifest['repositories']
    checks, failures = [], 0
    for repository in sorted(repositories, key=lambda r: r['id']):
        identifier = f"repository:{repository['id']}"
        keyring = KEYRING_DIR / f"{repository['id']}.gpg"
        if not keyring.is_file():
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'keyring-missing'})
            failures += 1
            continue
        observed = key_fingerprint(keyring)
        if observed != repository.get('key_fingerprint'):
            checks.append({'id': identifier, 'status': 'failed',
                           'reason': 'keyring-is-not-the-recorded-key'})
            failures += 1
            continue
        if repository.get('self_registers_source'):
            continue
        if not (SOURCES_DIR / f"workstation-{repository['id']}.sources").is_file():
            checks.append({'id': identifier, 'status': 'failed', 'reason': 'source-not-configured'})
            failures += 1
    checks.append(_summary('manifest-repositories', failures, len(repositories),
                           'repositories-configured-with-their-recorded-key'))
    return checks


def verify(root=ROOT, groups=None):
    return (verify_binaries(root, groups) + verify_snaps(root, groups)
            + verify_repositories(root))
