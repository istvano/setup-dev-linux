"""F01/F02 behavioral contracts; fixtures never substitute for real guest tests."""
import copy
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError, load_context, load_json, validate_schema
from workstation.storage import assess, preflight, InspectionError


class ConfigAndPlan(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'machine.json'
        self.config = json.loads((ROOT / 'config/standard-single.example.json').read_text())
        self.config['selection_file'] = str(ROOT / 'profiles/default.json')
        self.save()

    def save(self):
        self.path.write_text(json.dumps(self.config))

    def cli(self, *args):
        return subprocess.run(['/usr/bin/python3', '-I', '-S', '-B', str(ROOT / 'bootstrap'), *args], capture_output=True, text=True)

    def test_all_examples_load_without_third_party_packages(self):
        for p in (ROOT / 'config').glob('*.example.json'):
            result = self.cli('plan', '--config', str(p), '--format', 'json')
            self.assertEqual(result.returncode, 0, result.stderr + result.stdout)
            report = json.loads(result.stdout)
            self.assertFalse(report['workstation_ready'])
            self.assertTrue(any(c['status'] == 'blocked-source' for c in report['checks']))

    def test_plan_makes_no_repo_or_input_writes(self):
        def snapshot():
            files = [ROOT / 'bootstrap', self.path]
            files += list((ROOT / 'script').rglob('*'))
            return {str(p): hashlib.sha256(p.read_bytes()).hexdigest() for p in files if p.is_file()}
        before = snapshot()
        result = self.cli('plan', '--config', str(self.path), '--format', 'json')
        self.assertEqual(result.returncode, 0)
        self.assertEqual(before, snapshot())

    def test_private_values_absent_from_report(self):
        self.config['target']['user'] = 'PRIVATE_SENTINEL_ACCOUNT'
        self.config['storage']['disks']['system']['stable_id'] = 'PRIVATE_SENTINEL_DISK'
        self.save()
        result = self.cli('plan', '--config', str(self.path), '--format', 'json')
        self.assertEqual(result.returncode, 0)
        self.assertNotIn('PRIVATE_SENTINEL', result.stdout + result.stderr)

    def test_parser_error_is_redacted_json(self):
        result = self.cli('plan', '--private-secret-value', '--format', 'json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('private-secret-value', result.stdout + result.stderr)
        self.assertEqual(json.loads(result.stdout)['outcome'], 'invalid')

    def test_config_is_explicit(self):
        self.assertEqual(self.cli('plan', '--format', 'json').returncode, 2)

    def test_bad_json_does_not_echo_content(self):
        self.path.write_text('{"secret": "DO_NOT_PRINT"')
        result = self.cli('plan', '--config', str(self.path), '--format', 'json')
        self.assertEqual(result.returncode, 2)
        self.assertNotIn('DO_NOT_PRINT', result.stdout + result.stderr)

    def test_nested_duplicates_rejected(self):
        self.path.write_text('{"outer":{"password":1,"password":2}}')
        with self.assertRaisesRegex(InputError, 'duplicate-json-key'):
            load_json(self.path)

    def test_nan_rejected(self):
        self.path.write_text('{"capacity":NaN}')
        with self.assertRaisesRegex(InputError, 'nonfinite'):
            load_json(self.path)

    def test_boolean_not_integer(self):
        self.config['schema_version'] = True
        self.save()
        with self.assertRaises(InputError):
            load_context(self.path)

    def test_unknown_schema_keyword_fails_closed(self):
        with self.assertRaisesRegex(InputError, 'unsupported-schema-keyword'):
            validate_schema('x', {'type': 'string', 'futureConstraint': True})

    def test_example_install_rejected_before_inspection(self):
        result = self.cli('install', '--config', str(self.path), '--format', 'json')
        self.assertEqual(result.returncode, 2)
        self.assertIn('example-input-not-operational', result.stdout)

    def test_relative_selection_resolves_from_config(self):
        selection = json.loads((ROOT / 'profiles/default.json').read_text())
        (self.path.parent / 'selected.json').write_text(json.dumps(selection))
        self.config['selection_file'] = 'selected.json'
        self.save()
        self.assertEqual(load_context(self.path)['selected'], selection['capability_ids'])


def fixture():
    config = json.loads((ROOT / 'config/standard-split.example.json').read_text())
    config['example_only'] = False
    config['target']['user'] = 'fixture'
    config['storage']['separate_var_lib'] = False
    del config['storage']['mounts']['/var/lib']
    devices = [{'name': '/dev/vda', 'type': 'disk', 'size': 64000, 'uuid': None, 'pkname': None},
               {'name': '/dev/vdb', 'type': 'disk', 'size': 32000, 'uuid': None, 'pkname': None}]
    aliases = {}
    for role, name in [('system', '/dev/vda'), ('data', '/dev/vdb')]:
        declaration = config['storage']['disks'][role]
        declaration.update(stable_id='/dev/disk/by-id/fixture-' + role, minimum_bytes=1000)
        aliases[declaration['stable_id']] = name
    mounts = []
    for n, (path, declaration) in enumerate(config['storage']['mounts'].items(), 1):
        disk = '/dev/vdb' if path == '/home' else '/dev/vda'
        declaration['filesystem_uuid'] = 'uuid-' + str(n)
        devices.append({'name': disk + str(n), 'type': 'part', 'size': 4000, 'uuid': declaration['filesystem_uuid'], 'pkname': disk})
        mounts.append({'target': path, 'source': disk + str(n), 'uuid': declaration['filesystem_uuid'], 'options': 'rw,relatime', 'fstype': 'ext4', 'fsroot': '/'})
    observed = {'os': 'ubuntu', 'release': '26.04', 'architecture': 'x86_64', 'user_valid': True,
                'user_home': '/home/fixture', 'devices': devices, 'mounts': mounts, 'aliases': aliases}
    return config, observed


class StorageGuard(unittest.TestCase):
    def setUp(self):
        self.config, self.observed = fixture()

    def test_standard_split_passes(self):
        self.assertEqual(assess(self.config, self.observed)[1], 0)

    def test_reordered_disks_pass(self):
        self.observed['devices'].reverse()
        self.assertEqual(assess(self.config, self.observed)[1], 0)

    def test_wrong_uuid_fails(self):
        self.config['storage']['mounts']['/home']['filesystem_uuid'] = 'wrong'
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_missing_exact_mount_fails(self):
        self.observed['mounts'] = [m for m in self.observed['mounts'] if m['target'] != '/home']
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_same_physical_disk_fails(self):
        self.observed['aliases']['/dev/disk/by-id/fixture-data'] = '/dev/vda'
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_insufficient_capacity_fails(self):
        self.config['storage']['disks']['data']['minimum_bytes'] = 100000
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_duplicate_uuid_fails(self):
        d = copy.deepcopy(self.observed['devices'][-1]);d['name'] = '/dev/vdc1'
        self.observed['devices'].append(d)
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_readonly_mount_fails(self):
        self.observed['mounts'][-1]['options'] = 'ro,relatime'
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_subdirectory_bind_fails(self):
        self.observed['mounts'][-1]['fsroot'] = '/old-home'
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_unexpected_var_parent_mount_fails(self):
        self.observed['mounts'].append({'target': '/var', 'uuid': 'other'})
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_nested_home_mount_fails(self):
        self.observed['mounts'].append({'target': '/home/fixture/.local', 'uuid': 'other'})
        self.assertEqual(assess(self.config, self.observed)[1], 1)

    def test_missing_inspection_tool_is_failure(self):
        with patch('workstation.storage.inventory', side_effect=InspectionError):
            self.assertEqual(preflight(self.config)[1], 2)

    def test_wrong_os_rejected(self):
        self.observed['release'] = '24.04'
        self.assertEqual(assess(self.config, self.observed)[1], 2)

    def test_root_or_invalid_account_rejected(self):
        self.observed['user_valid'] = False
        self.assertEqual(assess(self.config, self.observed)[1], 2)


if __name__ == '__main__':
    unittest.main()
