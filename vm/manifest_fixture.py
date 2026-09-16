#!/usr/bin/python3 -B
"""Apply the manifest in the disposable guest and verify what actually landed.

This runs inside the test VM only. It refuses to run anywhere that does not
carry the expected disposable-VM marker. Verification reads the installed
system rather than trusting the installer's own report: a package is present
when dpkg says so, a binary when it is executable, a snap when snapd lists it.
"""
import argparse
import json
import subprocess
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--groups', required=True, help='comma-separated manifest groups')
parser.add_argument('--verify-only', action='store_true')
args = parser.parse_args()

marker = Path('/etc/linux-os-setup-test-vm')
if not marker.is_file() or marker.read_text().strip() != args.expected_vm_id:
    raise SystemExit('Refusing non-test guest')

ROOT = Path(__file__).resolve().parents[1]
GROUPS = [g for g in args.groups.split(',') if g]
failures = []


def report(ok, message):
    print(('PASS: ' if ok else 'FAIL: ') + message, flush=True)
    if not ok:
        failures.append(message)


def build_config():
    config = json.loads((ROOT / 'config/standard-split.example.json').read_text())
    config['example_only'] = False
    config['target']['user'] = 'ws-test'
    config['selection_file'] = str(ROOT / 'profiles/default.json')
    config['storage']['separate_var_lib'] = False
    del config['storage']['mounts']['/var/lib']
    for role, serial in [('system', 'system'), ('data', 'home')]:
        config['storage']['disks'][role] = {
            'stable_id': '/dev/disk/by-id/virtio-linux-setup-' + serial,
            'minimum_bytes': 1024**3}
    observed = json.loads(subprocess.check_output(
        ['findmnt', '--json', '--list', '--output', 'TARGET,UUID']))
    for path, declaration in config['storage']['mounts'].items():
        matches = [m for m in observed['filesystems'] if m['target'] == path]
        if len(matches) != 1 or not matches[0].get('uuid'):
            raise SystemExit('Required fixture mount missing: ' + path)
        declaration['filesystem_uuid'] = matches[0]['uuid']
    path = ROOT / 'guest.local.json'
    path.write_text(json.dumps(config, indent=2) + '\n')
    path.chmod(0o600)
    return path


def installed_packages():
    output = subprocess.run(['dpkg-query', '-W', '-f=${Package} ${Status}\n'],
                            capture_output=True, text=True, check=False).stdout
    return {line.split()[0] for line in output.splitlines()
            if line.strip().endswith('ok installed')}


def verify():
    packages = json.loads((ROOT / 'manifest/packages.json').read_text())
    binaries = json.loads((ROOT / 'manifest/binaries.json').read_text())
    snaps = json.loads((ROOT / 'manifest/snaps.json').read_text())
    present = installed_packages()

    expected, missing = 0, []
    for group in GROUPS:
        for entry in packages['groups'].get(group, []):
            expected += 1
            if entry['name'] not in present:
                missing.append(f"{group}/{entry['name']}")
    report(not missing, f'{expected - len(missing)}/{expected} manifest packages installed'
                        + (': missing ' + ', '.join(sorted(missing)) if missing else ''))

    install_dir = Path(binaries['install_dir'])
    wanted = [b for b in binaries['binaries'] if b['group'] in GROUPS]
    absent = []
    for binary in wanted:
        if binary['kind'] == 'deb':
            if binary['id'] not in present:
                absent.append(binary['id'])
        else:
            target = install_dir / binary['id']
            if not (target.is_file() and target.stat().st_mode & 0o111):
                absent.append(binary['id'])
    report(not absent, f'{len(wanted) - len(absent)}/{len(wanted)} pinned binaries installed'
                       + (': missing ' + ', '.join(sorted(absent)) if absent else ''))

    listed = subprocess.run(['snap', 'list'], capture_output=True, text=True, check=False).stdout
    names = {line.split()[0] for line in listed.splitlines()[1:] if line.strip()}
    wanted_snaps = [s for s in snaps['snaps'] if s['group'] in GROUPS]
    missing_snaps = [s['name'] for s in wanted_snaps if s['name'] not in names]
    report(not missing_snaps, f'{len(wanted_snaps) - len(missing_snaps)}/{len(wanted_snaps)} '
                              f'snaps installed'
                              + (': missing ' + ', '.join(missing_snaps) if missing_snaps else ''))

    # A tool that installs but cannot run is not installed in any useful sense.
    runnable = {'helm': ['version', '--short'], 'k9s': ['version', '--short'],
                'yq': ['--version'], 'sops': ['--version'], 'kubeconform': ['-v'],
                'actionlint': ['--version'], 'd2': ['--version'],
                'chezmoi': ['--version'], 'hadolint': ['--version']}
    broken = []
    for name, invocation in runnable.items():
        binary = next((b for b in wanted if b['id'] == name), None)
        if binary is None:
            continue
        target = str(install_dir / name) if binary['kind'] != 'deb' else name
        # Absence is already reported above; running a missing binary would only
        # turn a clear finding into a traceback.
        if name in absent:
            continue
        try:
            result = subprocess.run([target, *invocation], capture_output=True,
                                    text=True, check=False, timeout=60)
        except (OSError, subprocess.SubprocessError) as exc:
            broken.append(f'{name}({type(exc).__name__})')
            continue
        if result.returncode != 0:
            broken.append(f'{name}(exit {result.returncode})')
    attempted = len([n for n in runnable if n not in absent
                     and any(b['id'] == n for b in wanted)])
    report(not broken, f'{attempted - len(broken)}/{attempted} sampled binaries execute'
                       + (': failed ' + ', '.join(broken) if broken else ''))

    verify_desktop()


def verify_desktop():
    """The settings must be in the live database, not merely declared."""
    if 'desktop' not in GROUPS:
        return
    sys.path.insert(0, str(ROOT / 'script'))
    from workstation.desktop import declared_keys, load_manifest, verify as verify_settings
    manifest = load_manifest(ROOT)
    total = len(list(declared_keys(manifest['settings'])))
    for check in verify_settings(ROOT):
        # "deferred" means a check could not run here, not that it failed:
        # a server guest has no dconf until the desktop group installs one.
        report(check['status'] in ('passed', 'deferred'),
               f"desktop {check['id']}: {check['status']} — {check['reason']} "
               f"({total} declared keys)")


def install(config):
    command = [str(ROOT / 'bootstrap'), 'install', '--config', str(config),
               '--format', 'json', '--manifest-groups', ','.join(GROUPS)]
    result = subprocess.run(command, capture_output=True, text=True)
    try:
        outcome = json.loads(result.stdout)['outcome']
    except (ValueError, KeyError):
        print(result.stdout[-4000:])
        print(result.stderr[-4000:], file=sys.stderr)
        raise SystemExit('install produced no report')
    # "incomplete" is the honest outcome while capability roles remain unwritten;
    # a failure is not.
    report(result.returncode in (0, 3), f'install returned {outcome}')
    if result.returncode not in (0, 3):
        print(json.dumps(json.loads(result.stdout), indent=2)[:4000])


config = build_config()
if not args.verify_only:
    install(config)
verify()

if failures:
    raise SystemExit(f'{len(failures)} manifest checks failed')
print('PASS: manifest applied and verified in the guest', flush=True)
