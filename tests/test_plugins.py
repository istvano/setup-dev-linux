"""Editor extensions and kubectl plugins.

These are installed by the tool that owns them rather than pinned and placed by
this repository, so the tests are about honouring the declaration and refusing
to pass when the owning tool is absent.
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
from workstation.plugins import PluginError, install, krew_environment, manifest, verify  # noqa: E402


def result(stdout='', returncode=0):
    return subprocess.CompletedProcess([], returncode, stdout, '')


class ManifestTest(unittest.TestCase):
    def test_the_real_manifest_declares_both_kinds(self):
        declared = manifest(ROOT)
        self.assertIn('saoudrizwan.claude-dev', declared['vscode_extensions'])
        self.assertIn('neat', declared['krew_plugins'])


class KrewEnvironmentTest(unittest.TestCase):
    """kubectl only finds plugins named kubectl-<name> on PATH, which is why
    krew has to bootstrap itself into KREW_ROOT."""

    def test_krew_root_and_path_are_set(self):
        environment = krew_environment('/home/someone')
        self.assertEqual(environment['KREW_ROOT'], '/home/someone/.krew')
        self.assertTrue(environment['PATH'].startswith('/home/someone/.krew/bin:'))


class ExtensionTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        (self.root / 'manifest/plugins.json').write_text(json.dumps(
            {'schema_version': 1, 'vscode_extensions': ['a.one', 'b.two'],
             'krew_plugins': []}))

    def test_missing_code_is_refused_not_skipped(self):
        with patch.object(plugins.shutil, 'which', return_value=None):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['dev'])

    def test_only_absent_extensions_are_installed(self):
        calls = []

        def fake(command, home, timeout=300):
            calls.append(command)
            if command[1] == '--list-extensions':
                return result('a.one\n')
            return result()

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertTrue(install(self.home, self.root, groups=['dev']))
        installed = [c[2] for c in calls if c[1] == '--install-extension']
        self.assertEqual(installed, ['b.two'], 'an already present extension is not reinstalled')

    def test_nothing_to_do_reports_no_change(self):
        def fake(command, home, timeout=300):
            return result('a.one\nb.two\n')

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertFalse(install(self.home, self.root, groups=['dev']))

    def test_a_refused_extension_fails_loudly(self):
        def fake(command, home, timeout=300):
            if command[1] == '--list-extensions':
                return result('')
            return result(returncode=1)

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['dev'])

    def test_extension_comparison_ignores_case(self):
        def fake(command, home, timeout=300):
            return result('A.One\nB.Two\n')

        with patch.object(plugins.shutil, 'which', return_value='/usr/bin/code'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertFalse(install(self.home, self.root, groups=['dev']))


class KrewTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / 'manifest').mkdir()
        (self.root / 'manifest/plugins.json').write_text(json.dumps(
            {'schema_version': 1, 'vscode_extensions': [], 'krew_plugins': ['neat', 'tree']}))
        self.shim = self.home / '.krew/bin/kubectl-krew'

    def make_shim(self):
        self.shim.parent.mkdir(parents=True, exist_ok=True)
        self.shim.write_text('#!/bin/sh\n')
        self.shim.chmod(0o755)

    def test_krew_bootstraps_itself_before_plugins_install(self):
        calls = []

        def fake(command, home, timeout=300):
            calls.append(command)
            if command[1] == 'install' and command[2] == 'krew':
                self.make_shim()
            if command[1] == 'list':
                return result('PLUGIN\n')
            return result()

        with patch.object(plugins.shutil, 'which', return_value='/usr/local/bin/krew'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertTrue(install(self.home, self.root, groups=['kubernetes']))
        self.assertEqual(calls[0][1:], ['install', 'krew'],
                         'krew must install itself before any plugin')

    def test_missing_krew_binary_is_refused(self):
        with patch.object(plugins.shutil, 'which', return_value=None):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['kubernetes'])

    def test_a_bootstrap_that_produces_no_shim_fails(self):
        with patch.object(plugins.shutil, 'which', return_value='/usr/local/bin/krew'), \
             patch.object(plugins, 'run', return_value=result()):
            with self.assertRaises(PluginError):
                install(self.home, self.root, groups=['kubernetes'])

    def test_already_installed_plugins_are_left_alone(self):
        self.make_shim()

        def fake(command, home, timeout=300):
            if command[1] == 'list':
                return result('PLUGIN\nneat\ntree\n')
            return result()

        with patch.object(plugins.shutil, 'which', return_value='/usr/local/bin/krew'), \
             patch.object(plugins, 'run', side_effect=fake):
            self.assertFalse(install(self.home, self.root, groups=['kubernetes']))


class GroupTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_neither_half_runs_when_its_group_is_absent(self):
        with patch.object(plugins, 'install_extensions') as extensions, \
             patch.object(plugins, 'install_krew_plugins') as krew:
            install(self.home, ROOT, groups=['core'])
        extensions.assert_not_called()
        krew.assert_not_called()
        self.assertEqual(verify(self.home, ROOT, groups=['core']), [])

    def test_each_half_runs_for_its_own_group(self):
        with patch.object(plugins, 'install_extensions', return_value=False) as extensions, \
             patch.object(plugins, 'install_krew_plugins', return_value=False) as krew:
            install(self.home, ROOT, groups=['dev'])
        extensions.assert_called_once()
        krew.assert_not_called()


class VerificationTest(unittest.TestCase):
    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)

    def test_missing_extensions_are_named_and_summarised(self):
        with patch.object(plugins, 'installed_extensions', return_value={'a.one'}), \
             patch.object(plugins, 'manifest',
                          return_value={'vscode_extensions': ['a.one', 'b.two'],
                                        'krew_plugins': []}):
            checks = verify(self.home, ROOT, groups=['dev'])
        self.assertIn({'id': 'extension:b.two', 'status': 'failed', 'reason': 'not-installed'},
                      checks)
        self.assertEqual(checks[-1]['reason'], '1-of-2-extensions-installed')

    def test_a_missing_editor_is_deferred_not_failed(self):
        """The check could not run; that is different from having run and found
        the extensions absent."""
        with patch.object(plugins, 'installed_extensions',
                          side_effect=PluginError('code-not-installed')), \
             patch.object(plugins, 'manifest',
                          return_value={'vscode_extensions': ['a.one'], 'krew_plugins': []}):
            checks = verify(self.home, ROOT, groups=['dev'])
        self.assertEqual(checks[0]['status'], 'deferred')

    def test_krew_not_bootstrapped_fails(self):
        with patch.object(plugins, 'manifest',
                          return_value={'vscode_extensions': [], 'krew_plugins': ['neat']}):
            checks = verify(self.home, ROOT, groups=['kubernetes'])
        self.assertEqual(checks[0]['status'], 'failed')
        self.assertEqual(checks[0]['reason'], 'krew-not-bootstrapped')


class KrewListParsingTest(unittest.TestCase):
    """krew prints a bare list when stdout is not a terminal and a header when
    it is. Both shapes must be read correctly, or a plugin that is installed is
    reported missing."""

    def setUp(self):
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.home, ignore_errors=True)
        shim = self.home / '.krew/bin/kubectl-krew'
        shim.parent.mkdir(parents=True)
        shim.write_text('#!/bin/sh\n')
        shim.chmod(0o755)

    def listed(self, stdout):
        with patch.object(plugins, 'run', return_value=result(stdout)):
            return plugins.installed_krew_plugins(self.home)

    def test_a_bare_list_keeps_every_name(self):
        names = self.listed('images\nkrew\nneat\ntree\n')
        self.assertEqual(names, {'images', 'krew', 'neat', 'tree'},
                         'the first line is a plugin, not a header')

    def test_a_header_is_not_mistaken_for_a_plugin(self):
        names = self.listed('PLUGIN   VERSION\nimages   v0.1\nneat     v0.2\n')
        self.assertEqual(names, {'images', 'neat'})

    def test_blank_lines_are_ignored(self):
        self.assertEqual(self.listed('\nneat\n\n'), {'neat'})


if __name__ == '__main__':
    unittest.main()
