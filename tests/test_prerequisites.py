import copy
import json
from pathlib import Path
import shutil
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError
from workstation.prerequisites import registry, selected_records, combine_records


class CapabilityPrerequisites(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name)
        (self.root / 'catalogue').mkdir()
        shutil.copyfile(ROOT / 'catalogue/prerequisites.schema.json', self.root / 'catalogue/prerequisites.schema.json')
        self.value = json.loads((ROOT / 'catalogue/prerequisites.json').read_text())
        self.entries = {
            'mandrel': {'kind': 'package', 'delivery': {'status': 'verified'}},
            'rust': {'kind': 'package', 'delivery': {'status': 'verified'}},
        }

    def check(self):
        (self.root / 'catalogue/prerequisites.json').write_text(json.dumps(self.value))
        return registry(self.entries, self.root)

    def test_unselected_capability_requests_nothing(self):
        self.assertEqual(selected_records(self.check(), ['java']), [])

    def test_selected_mandrel_uses_resolute_freetype_package(self):
        self.assertEqual({r['package'] for r in selected_records(self.check(), ['mandrel'])},
                         {'g++', 'zlib1g-dev', 'libfreetype-dev'})

    def test_selected_rust_requests_reviewed_linker(self):
        self.assertEqual({r['package'] for r in selected_records(self.check(), ['rust'])},
                         {'g++'})

    def test_shared_mandrel_rust_linker_deduplicates(self):
        records = selected_records(self.check(), ['mandrel', 'rust'])
        self.assertEqual([r['package'] for r in records].count('g++'), 1)

    def test_unapproved_capability_mapping_fails(self):
        self.entries['mandrel']['delivery']['status'] = 'unverified'
        with self.assertRaises(InputError):
            self.check()

    def test_unknown_capability_mapping_fails(self):
        self.entries = {}
        with self.assertRaises(InputError):
            self.check()

    def test_duplicate_package_mapping_fails(self):
        self.value['requirements'][0]['packages'].append(copy.deepcopy(self.value['requirements'][0]['packages'][0]))
        with self.assertRaises(InputError):
            self.check()

    def test_shared_package_deduplicates(self):
        record = self.value['requirements'][0]['packages'][0]
        self.assertEqual(combine_records([record, dict(record, id='another-root')]), [record])

    def test_conflicting_package_source_fails(self):
        record = self.value['requirements'][0]['packages'][0]
        with self.assertRaises(InputError):
            combine_records([record, dict(record, source_package='unexpected')])
