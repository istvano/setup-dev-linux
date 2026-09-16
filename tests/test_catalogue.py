"""Negative tests for P0 selection/storage guarantees, not installer tests."""
import copy
import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest
from unittest.mock import patch

sys.dont_write_bytecode = True
ROOT = Path(__file__).resolve().parents[1]
qa = runpy.run_path(str(ROOT / 'script/check-catalogue'))


class CatalogueContracts(unittest.TestCase):
    def setUp(self):
        self.catalogue = qa['read_json'](ROOT / 'catalogue/capabilities.json')
        self.target = qa['read_json'](ROOT / 'profiles/target.json')
        self.default = qa['read_json'](ROOT / 'profiles/default.json')
        self.entries = {e['id']: e for e in self.catalogue['capabilities']}

    def check_catalogue(self):
        qa['check_catalogue'](self.catalogue, self.target, self.default)

    def config(self, name):
        return qa['read_json'](ROOT / f'config/{name}.example.json')

    def check_config(self, config):
        selection = self.target if config['features']['gpu'] == 'nvidia' else self.default
        qa['check_config'](config, self.entries, selection['capability_ids'])

    def test_confirmed_selection_passes(self):
        self.check_catalogue()

    def test_python_selection_requires_explicit_uv(self):
        selected = [i for i in self.target['capability_ids'] if i != 'uv']
        with self.assertRaisesRegex(ValueError, 'python-requires-selected-uv'):
            qa['validate_semantics'](self.config('standard-split'), self.entries, selected)

    def test_openhands_deferred_from_both_profiles(self):
        self.assertEqual(self.entries['openhands']['decision'], 'optional')
        self.assertNotIn('openhands', self.target['capability_ids'])
        self.assertNotIn('openhands', self.default['capability_ids'])

    def test_missing_keep_rejected(self):
        self.target['capability_ids'].remove('git')
        with self.assertRaisesRegex(ValueError, 'every KEEP'):
            self.check_catalogue()

    def test_optional_leak_rejected(self):
        self.target['capability_ids'].append('thunderbird')
        with self.assertRaisesRegex(ValueError, 'no optional'):
            self.check_catalogue()

    def test_pending_leak_rejected(self):
        self.target['capability_ids'].append('fish')
        with self.assertRaisesRegex(ValueError, 'no optional/pending/omit'):
            self.check_catalogue()

    def test_duplicate_ids_rejected(self):
        self.target['capability_ids'].append('git')
        with self.assertRaises(ValueError):
            self.check_catalogue()

    def test_unknown_schema_field_rejected(self):
        self.catalogue['silently_install_optional'] = True
        with self.assertRaisesRegex(ValueError, 'Additional properties'):
            self.check_catalogue()

    def test_unverified_pin_cannot_claim_readiness(self):
        self.entries['node']['delivery']['status'] = 'unverified'
        self.entries['node']['delivery']['blocker'] = 'Fixture source remains unverified'
        self.entries['node']['delivery']['version'] = 'unverified-release'
        with self.assertRaisesRegex(ValueError, 'unverified pin claimed'):
            self.check_catalogue()

    def test_verified_source_requires_licence(self):
        self.entries['node']['delivery']['status'] = 'verified'
        self.entries['node']['licence']['status'] = 'unreviewed'
        with self.assertRaisesRegex(ValueError, 'licence not reviewed'):
            self.check_catalogue()

    def test_duplicate_json_keys_rejected(self):
        with self.assertRaisesRegex(ValueError, 'duplicate JSON key'):
            json.loads('{"mode":"standard","mode":"standard"}', object_pairs_hook=qa['unique_object'])

    def test_single_layout_accepts_var_lib_on_root(self):
        self.check_config(self.config('standard-single'))

    def test_split_layout_can_keep_var_lib_on_root(self):
        config = self.config('standard-split')
        config['storage']['separate_var_lib'] = False
        del config['storage']['mounts']['/var/lib']
        self.check_config(config)

    def test_same_disk_for_split_roles_rejected(self):
        config = self.config('standard-split')
        config['storage']['disks']['data'] = copy.deepcopy(config['storage']['disks']['system'])
        with self.assertRaisesRegex(ValueError, 'duplicate physical disk'):
            self.check_config(config)

    def test_wrong_home_role_rejected(self):
        config = self.config('standard-split')
        config['storage']['mounts']['/home']['disk_role'] = 'system'
        with self.assertRaisesRegex(ValueError, 'wrong disk role'):
            self.check_config(config)

    def test_placeholder_not_operational(self):
        config = self.config('standard-single')
        config['example_only'] = False
        with self.assertRaisesRegex(ValueError, 'placeholders'):
            self.check_config(config)

    def test_gpu_feature_must_agree_with_selection(self):
        config = self.config('standard-single')
        with self.assertRaisesRegex(ValueError, 'GPU feature'):
            qa['check_config'](config, self.entries, self.target['capability_ids'])

    def test_private_selection_can_explicitly_enable_optional(self):
        config = self.config('standard-single')
        selection = self.default['capability_ids'] + ['thunderbird']
        qa['check_config'](config, self.entries, selection)

    def test_private_selection_rejects_password_manager_conflict(self):
        config = self.config('standard-single')
        with self.assertRaisesRegex(ValueError, 'conflicting selected'):
            qa['check_config'](config, self.entries, self.default['capability_ids'] + ['1password'])

    def test_private_selection_cannot_enable_pending(self):
        config = self.config('standard-single')
        with self.assertRaisesRegex(ValueError, 'pending/omitted'):
            qa['check_config'](config, self.entries, self.default['capability_ids'] + ['fish'])


class ReviewContracts(unittest.TestCase):
    def setUp(self):
        self.catalogue = qa['read_json'](ROOT / 'catalogue/capabilities.json')
        self.review = qa['read_json'](ROOT / 'catalogue/source-review.json')
        self.preferences = qa['read_json'](ROOT / 'profiles/user-environment.json')

    def check_review(self):
        qa['check_source_review'](self.catalogue, self.review)

    def test_current_review_passes(self):
        self.check_review()

    def test_missing_selected_source_rejected(self):
        self.review['records'].pop()
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.check_review()

    def test_duplicate_source_record_rejected(self):
        self.review['records'].append(copy.deepcopy(self.review['records'][0]))
        with self.assertRaisesRegex(ValueError, 'duplicate source-review'):
            self.check_review()

    def test_optional_source_cannot_replace_selected(self):
        self.review['records'][0]['capability_id'] = 'thunderbird'
        with self.assertRaisesRegex(ValueError, 'coverage'):
            self.check_review()

    def test_metadata_cannot_claim_install_approval(self):
        self.review['status'] = 'ready-to-install'
        with self.assertRaises(ValueError):
            self.check_review()

    def test_malformed_digest_rejected(self):
        self.review['records'][0]['artifacts'][0]['digest'] = 'sha256:guessed'
        with self.assertRaises(ValueError):
            self.check_review()

    def test_missing_digest_cannot_claim_integrity(self):
        self.review['records'][0]['artifacts'][0]['digest'] = None
        with self.assertRaisesRegex(ValueError, 'digest/verification'):
            self.check_review()

    def test_wrong_ubuntu_suite_rejected(self):
        row = next(r for r in self.review['records'] if 'apt_observation' in r)
        row['apt_observation']['origins'][0]['suite'] = 'resolute-proposed'
        with self.assertRaisesRegex(ValueError, 'unsupported Ubuntu'):
            self.check_review()

    def test_extension_identity_mismatch_rejected(self):
        row = next(r for r in self.review['records'] if 'extension_manifest' in r)
        row['extension_manifest']['publisher'] = 'unrelated-publisher'
        with self.assertRaisesRegex(ValueError, 'manifest identity'):
            self.check_review()

    def test_extension_version_mismatch_rejected(self):
        row = next(r for r in self.review['records'] if 'extension_manifest' in r)
        row['artifacts'][0]['version'] = '0.0.0'
        with self.assertRaisesRegex(ValueError, 'manifest version'):
            self.check_review()

    def test_confirmed_environment_passes(self):
        qa['check_user_environment'](self.catalogue, self.preferences)

    def test_java_default_cannot_revert_to_21(self):
        self.preferences['java']['default_major'] = 21
        with self.assertRaises(ValueError):
            qa['check_user_environment'](self.catalogue, self.preferences)

    def test_version_policy_cannot_silently_revert(self):
        self.preferences['version_policy'] = 'preserve-old-major-versions'
        with self.assertRaises(ValueError):
            qa['check_user_environment'](self.catalogue, self.preferences)

    def test_existing_project_validation_cannot_be_assumed(self):
        self.preferences['compatibility_validation'] = 'existing-projects-validated'
        with self.assertRaises(ValueError):
            qa['check_user_environment'](self.catalogue, self.preferences)

    def test_confirmed_plugin_cannot_disappear(self):
        self.preferences['shell']['plugins'].remove('zsh-autosuggestions')
        with self.assertRaises(ValueError):
            qa['check_user_environment'](self.catalogue, self.preferences)

    def test_proxy_values_cannot_enter_preferences(self):
        self.preferences['shell']['proxy_url'] = 'https://private-proxy.example'
        with self.assertRaises(ValueError):
            qa['check_user_environment'](self.catalogue, self.preferences)

    def test_wrong_mac_mapping_detected(self):
        self.catalogue['mac_profile_mappings'][0]['capability_ids'] = ['git']
        self.catalogue['mac_profile_mappings'][0]['note'] = 'Wrong mapping'
        with self.assertRaisesRegex(ValueError, 'matrix differs'):
            qa['check_matrix'](self.catalogue)

    def test_wrong_extension_family_detected(self):
        self.catalogue['linux_extension_families'][0]['capability_ids'] = ['git']
        with self.assertRaisesRegex(ValueError, 'matrix differs'):
            qa['check_matrix'](self.catalogue)

    def test_changed_source_note_detected(self):
        self.catalogue['mac_source_mappings'][0]['note'] = 'Changed ownership'
        with self.assertRaisesRegex(ValueError, 'matrix differs'):
            qa['check_matrix'](self.catalogue)

    def test_extra_matrix_row_detected(self):
        matrix = (ROOT / 'docs/CAPABILITY-MATRIX.md').read_text()
        with patch.object(Path, 'read_text', return_value=matrix + '| bogus | row |\n'):
            with self.assertRaisesRegex(ValueError, 'matrix differs'):
                qa['check_matrix'](self.catalogue)

    def test_renderers_are_deterministic(self):
        self.assertEqual(qa['render_matrix'](self.catalogue), qa['render_matrix'](copy.deepcopy(self.catalogue)))
        self.assertEqual(qa['render_source_review'](self.review), qa['render_source_review'](copy.deepcopy(self.review)))

    def test_private_controller_docs_are_not_repository_links(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            (root / '.workstation').mkdir()
            (root / '.workstation/vendor.md').write_text('[vendor link](absent.txt)')
            (root / 'README.md').write_text('Repository documentation')
            with patch.dict(qa['check_links'].__globals__, {'ROOT': root}):
                qa['check_links']()
                (root / 'README.md').write_text('[broken repository link](absent.txt)')
                with self.assertRaisesRegex(ValueError, 'broken link'):
                    qa['check_links']()


if __name__ == '__main__':
    unittest.main()
