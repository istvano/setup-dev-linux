#!/usr/bin/python3 -B
"""Synthetic guest test fixture, never a production machine input generator."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--controller', action='store_true')
args = parser.parse_args()
marker = Path('/etc/linux-os-setup-test-vm')
if not marker.is_file() or marker.read_text().strip() != args.expected_vm_id:
    raise SystemExit('Refusing non-test guest')
ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / 'config/standard-split.example.json').read_text())
config['example_only'] = False
config['target']['user'] = 'ws-test'
config['selection_file'] = str(ROOT / 'profiles/default.json')
config['storage']['separate_var_lib'] = False
del config['storage']['mounts']['/var/lib']
for role, serial in [('system', 'system'), ('data', 'home')]:
    config['storage']['disks'][role] = {'stable_id': '/dev/disk/by-id/virtio-linux-setup-' + serial, 'minimum_bytes': 1024**3}
observed = json.loads(subprocess.check_output(['findmnt', '--json', '--list', '--output', 'TARGET,UUID']))
for path, declaration in config['storage']['mounts'].items():
    matches = [m for m in observed['filesystems'] if m['target'] == path]
    if len(matches) != 1 or not matches[0].get('uuid'):
        raise SystemExit('Required fixture mount missing')
    declaration['filesystem_uuid'] = matches[0]['uuid']
path = ROOT / 'guest.local.json'
path.write_text(json.dumps(config, indent=2) + '\n')
path.chmod(0o600)

def run(*args, expected=0):
    result = subprocess.run([str(ROOT / 'bootstrap'), *args, '--config', str(path), '--format', 'json'], capture_output=True, text=True)
    value = json.loads(result.stdout)
    if result.returncode != expected:
        print(result.stdout)
        raise SystemExit('Guest command returned unexpected exit: ' + str(result.returncode))
    print(args[0] + ': expected exit ' + str(expected) + ', observed ' + value['outcome'])
    return value

run('plan')
run('preflight')
# Restore fixture input even if a negative assertion fails.
try:
    bad = copy.deepcopy(config)
    bad['storage']['mounts']['/home']['filesystem_uuid'] = 'intentionally-wrong-fixture-uuid'
    path.write_text(json.dumps(bad))
    run('preflight', expected=1)
    run('install', expected=1)
finally:
    path.write_text(json.dumps(config, indent=2) + '\n')
print('PASS: real Ubuntu guest config/plan/preflight and failed-guard install boundary')
if args.controller:
    tool_env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    tool_env['PATH'] = str(ROOT / '.workstation/venv/bin') + ':' + tool_env['PATH']
    for attempt in range(2):
        result = run('install', expected=1)
        if not any(c['id'] == 'controller-foundation' and c['status'] == 'passed' for c in result['checks']):
            raise SystemExit('Controller foundation failed')
    subprocess.run([str(ROOT / '.workstation/venv/bin/python'), '-B', str(ROOT / 'script/test')], cwd=ROOT, env=tool_env, check=True)
    subprocess.run([str(ROOT / '.workstation/venv/bin/ansible-lint'), '--offline', *[str(p) for p in sorted((ROOT / 'ansible').glob('*.yml'))]], cwd=ROOT, env=tool_env, check=True)
    result = run('install', expected=1)
    if not any(c['id'] == 'controller-foundation' and c['status'] == 'passed' for c in result['checks']):
        raise SystemExit('Controller did not remain intact after QA/lint')
    print('PASS: locked controller, two Ansible foundation applies, pinned QA and Ansible lint')
    print('Application source/role gates remain failed; no full workstation success claimed.')
