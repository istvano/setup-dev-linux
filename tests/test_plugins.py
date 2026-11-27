"""Editor extensions for the host VS Code.

They are installed by `code` rather than pinned and placed by this repository,
so the tests are about honouring the declaration and refusing to pass when the
editor is absent. kubectl plugins belong to setup-dev-linux-wsl.
"""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))

from workstation import plugins  # noqa: E402
from workstation.plugins import PluginError, install, manifest, verify  # noqa: E402


def result(stdout='', returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, '')


class ManifestTest(unittest.TestCase):
    def test_the_real_manifest_declares_extensions_only(self):
        declared = manifest(ROOT)
        self.assertIn('saoudrizwan.claude-dev', declared['vscode_extensions'])
        self.assertNotIn('krew_plugins', declared)

    def test_every_kept_catalogue_extension_is_a_declared_one(self):
        """D035: the catalogue's kept extension-* ids map onto what verify() checks.

        Optional ones stay deferred when selected: nothing installs them.
        """
        catalogue = json.loads((ROOT / 'catalogue/capabilities.json').read_text())
        ids = {c['id'] for c in catalogue['capabilities']
               if c['kind'] == 'extension' and c['decision'] == 'keep'}
        self.assertTrue(ids)
        self.assertEqual(ids - plugins.capability_ids(ROOT), set())


class ExtensionTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        (self.root / 'manifest/plugins.json').write_text(json.dumps(
            {'schema_version': 1, 'vscode_extensions': ['a.one', 'b.two']}))

    def test_missing_code_is_refused_not_skipped(self):
        with patch.object(plugins.shutil, 'which', return_value=None):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['dev-gui'])

    def test_only_absent_extensions_are_installed(self):
        calls = []

        def fake(command, timeout=300):
            calls.append(command)
            if command[1] == '--list-extensions':
                return result('a.one\n')
            return result()

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertTrue(install(self.home, self.root, groups=['dev-gui']))
        installed = [c[2] for c in calls if c[1] == '--install-extension']
        self.assertEqual(installed, ['b.two'], 'an already present extension is not reinstalled')

    def test_nothing_to_do_reports_no_change(self):
        def fake(command, timeout=300):
            return result('a.one\nb.two\n')

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertFalse(install(self.home, self.root, groups=['dev-gui']))

    def test_a_refused_extension_fails_loudly(self):
        def fake(command, timeout=300):
            if command[1] == '--list-extensions':
                return result('')
            return result(returncode=1)

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['dev-gui'])

    def test_extension_comparison_ignores_case(self):
        def fake(command, timeout=300):
            return result('A.One\nB.Two\n')

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertFalse(install(self.home, self.root, groups=['dev-gui']))


class GroupTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_nothing_runs_without_the_dev_gui_group(self):
        with patch.object(plugins, 'install_extensions') as extensions:
            install(self.home, ROOT, groups=['desktop'])
        extensions.assert_not_called()
        self.assertEqual(verify(self.home, ROOT, groups=['desktop']), [])

    def test_extensions_run_for_the_dev_gui_group(self):
        with patch.object(plugins, 'install_extensions', return_value=False) as extensions:
            install(self.home, ROOT, groups=['dev-gui'])
        extensions.assert_called_once()


class VerificationTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_missing_extensions_are_named_and_summarised(self):
        with patch.object(plugins, 'installed_extensions', return_value={'a.one'}), \
             patch.object(plugins, 'manifest',
                          return_value={'vscode_extensions': ['a.one', 'b.two']}):
            checks = verify(self.home, ROOT, groups=['dev-gui'])
        self.assertIn({'id': 'extension:b.two', 'status': 'failed', 'reason': 'not-installed'},
                      checks)
        self.assertEqual(checks[-1]['reason'], '1-of-2-extensions-installed')

    def test_a_missing_editor_is_deferred_not_failed(self):
        """The check could not run; that is different from having run and found
        the extensions absent."""
        with patch.object(plugins, 'installed_extensions',
                          side_effect=PluginError('code-not-installed')), \
             patch.object(plugins, 'manifest',
                          return_value={'vscode_extensions': ['a.one']}):
            checks = verify(self.home, ROOT, groups=['dev-gui'])
        self.assertEqual(checks[0]['status'], 'deferred')


if __name__ == '__main__':
    unittest.main()
