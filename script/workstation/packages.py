"""APT package delivery from the manifest, and independent read-only verification.

`manifest/packages.json` is the single source of what a machine installs. Each
entry names the source it must come from: the Ubuntu archive, or a repository
declared in `manifest/repositories.json`. Both installation and verification
read that one file.

A package is acceptable only when the version APT offers actually comes from the
source the manifest declares. Checking that the package exists is not enough: a
name can resolve against any configured repository, so a declared source that is
not enforced is a source in name only. google-cloud-cli ships a kubectl whose
epoch outranks the upstream Kubernetes build, and without this check adding that
repository silently replaces kubectl.

Dependencies are not checked here. Only the declared repositories are configured
on the machine and APT refuses unsigned sources, so a dependency cannot come from
anywhere undeclared. Simulating the full transaction was tried and removed:
python-apt's manual marking is not a faithful model of APT's solver, and it
reported conflicts that a real install resolves without difficulty.
"""
import json
import platform
import re
import subprocess
from pathlib import Path
from urllib.parse import urlparse

from .config import ROOT, InputError, load_json, require, validate_schema

ARCHIVE = 'archive'
ARCHIVE_ORIGIN = 'Ubuntu'


def archive_suites():
    """Ubuntu pockets accepted for archive packages on this release."""
    try:
        codename = platform.freedesktop_os_release().get('VERSION_CODENAME')
    except (OSError, AttributeError):
        codename = None
    if not codename:
        return []
    return [codename, f'{codename}-updates', f'{codename}-security', f'{codename}-backports']


def repository_sites(root=ROOT):
    """Host each declared repository serves packages from."""
    manifest, _ = load_json(Path(root) / 'manifest/repositories.json')
    sites = {}
    for repository in manifest['repositories']:
        host = urlparse(repository['uri']).netloc
        require(host, f"{repository['id']}: repository uri has no host")
        sites[repository['id']] = host
    return sites


def applied_groups(root=ROOT):
    """Manifest groups the last install applied, or None when nothing has.

    Verification should describe the machine that exists. A machine installed
    without the gpu group has not failed to install it.
    """
    record = Path(root) / '.workstation/applied-groups.json'
    try:
        value = json.loads(record.read_text())
    except (OSError, ValueError):
        return None
    groups = value.get('groups')
    return groups if isinstance(groups, list) and groups else None


def expectations(root=ROOT, groups=None):
    """What each selected package must satisfy, keyed by package name."""
    manifest, _ = load_json(Path(root) / 'manifest/packages.json')
    sites = repository_sites(root)
    suites = archive_suites()
    selected = groups if groups is not None else list(manifest['groups'])
    records = {}
    for group in selected:
        for entry in manifest['groups'].get(group, []):
            source = entry['source']
            if source == ARCHIVE:
                record = {'kind': ARCHIVE, 'origin': ARCHIVE_ORIGIN, 'suites': suites, 'site': None}
            else:
                require(source in sites, f"{entry['name']}: undeclared repository {source}")
                record = {'kind': 'repository', 'origin': None, 'suites': [], 'site': sites[source]}
            records[entry['name']] = {'id': entry['name'], 'package': entry['name'],
                                      'group': group, 'source': source, **record}
    return records


def allowed_version(version, expectation):
    """Pure policy check, shared by the APT adapter and the negative fixtures."""
    if not version or not expectation:
        return False
    if version.get('architecture') not in ('amd64', 'all'):
        return False
    if not re.fullmatch('[0-9a-f]{64}', version.get('sha256') or ''):
        return False
    origins = version.get('origins', [])
    if not origins:
        return False
    if not all(origin.get('trusted') for origin in origins):
        return False
    if expectation['kind'] == ARCHIVE:
        return all(origin.get('origin') == expectation['origin']
                   and origin.get('suite') in expectation['suites'] for origin in origins)
    return all(origin.get('site') == expectation['site'] for origin in origins)


def inspect_packages(records, root=ROOT):
    """Ask the APT adapter what each package would install from its source.

    """
    command = ['/usr/bin/python3', '-B', str(Path(root) / 'script/workstation/apt_probe.py')]
    try:
        result = subprocess.run(
            command, input=json.dumps(records), capture_output=True, text=True,
            timeout=300, check=True)
        value = json.loads(result.stdout)
        require({r['id'] for r in value} == {r['id'] for r in records}
                and len(value) == len(records), 'package-inspection-coverage')
        return value
    except (OSError, subprocess.SubprocessError, ValueError):
        raise InputError('required-package-inspection-unavailable') from None


def verify_packages(root=ROOT, groups=None):
    """Report whether every manifest package is installed from its declared source.

    Failures are named individually; the pass is summarised, because listing
    eighty-four passing packages buries the ones that matter.
    """
    records = list(expectations(root, groups).values())
    if not records:
        return []
    observations = inspect_packages(records, root)
    by_id = {r['id']: r for r in records}
    failed = [o for o in observations if not o['installed_allowed']]
    checks = [{'id': f"package:{o['id']}", 'status': 'failed',
               'reason': f"missing-or-not-from-declared-source:{by_id[o['id']]['source']}"}
              for o in sorted(failed, key=lambda o: o['id'])]
    checks.append({'id': 'manifest-packages',
                   'status': 'failed' if failed else 'passed',
                   'reason': f'{len(observations) - len(failed)}-of-{len(observations)}'
                             '-installed-from-their-declared-source'})
    return checks


def verify_named_packages(names, root=ROOT):
    """Check that specific Ubuntu archive packages are installed.

    Used by runtimes that need a system dependency present before they can
    work — Mandrel's native-image support needs a compiler and the zlib and
    freetype headers. Those packages are declared in the manifest like any
    other; this asks only whether they are there.
    """
    names = sorted(set(names))
    if not names:
        return []
    suites = archive_suites()
    records = [{'id': name, 'package': name, 'source': ARCHIVE, 'kind': ARCHIVE,
                'origin': ARCHIVE_ORIGIN, 'suites': suites, 'site': None} for name in names]
    return [{'id': o['id'],
             'status': 'passed' if o['installed_allowed'] else 'failed',
             'reason': 'installed-from-the-ubuntu-archive' if o['installed_allowed']
                       else 'missing-or-not-from-the-ubuntu-archive'}
            for o in inspect_packages(records, root)]


def approved_registry(entries, root=ROOT):
    """Licence and copyright evidence for reviewed archive packages.

    Provenance only: installation reads the manifest, not this registry. The
    records are retained because they carry reviewed licence identifiers and
    copyright digests that nothing else records.
    """
    registry, _ = load_json(Path(root) / 'catalogue/approved-delivery.json')
    schema, _ = load_json(Path(root) / 'catalogue/approved-delivery.schema.json')
    validate_schema(registry, schema)
    records = {r['id']: r for r in registry['entries']}
    require(len(records) == len(registry['entries']), 'duplicate-approved-delivery')
    for id, record in records.items():
        require(id in entries, 'unknown-approved-delivery')
        entry = entries[id]
        require(entry['owner'] == 'ansible' and entry['kind'] == 'package', 'wrong-package-owner')
        require(entry['delivery']['status'] == 'verified'
                and entry['delivery']['channel'] == 'ubuntu-apt', 'delivery-approval-mismatch')
        require(entry['delivery']['identifier'] == record['package'], 'package-identifier-mismatch')
        require(entry['licence']['status'] == 'reviewed'
                and entry['licence']['identifier'] == record['licence'], 'package-licence-mismatch')
    require({i for i, e in entries.items()
             if e['delivery']['channel'] == 'ubuntu-apt'
             and e['delivery']['status'] == 'verified'} == set(records), 'approved-registry-coverage')
    return records
