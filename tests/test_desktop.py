"""Behavioural tests for GNOME settings delivery."""
import json
import shutil
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'script'))

from workstation import desktop  # noqa: E402
from workstation.desktop import (  # noqa: E402
    DesktopError, declared_keys, load_manifest, normalise, render_keyfile, verify)


class KeyfileTest(unittest.TestCase):
    def test_sections_and_keys_are_rendered(self):
        text = render_keyfile({'org/gnome/shell': {'favorite-apps': "['a.desktop']"}})
        self.assertIn('[org/gnome/shell]', text)
        self.assertIn("favorite-apps=['a.desktop']", text)

    def test_values_are_written_verbatim(self):
        """dconf values are arbitrary GVariant text; a value that looks like
        template syntax must survive untouched."""
        awkward = "'{{ not a template }}'"
        text = render_keyfile({'org/example': {'key': awkward}})
        self.assertIn(f'key={awkward}', text)

    def test_sections_are_separated_by_a_blank_line(self):
        text = render_keyfile({'a/b': {'k': '1'}, 'c/d': {'k': '2'}})
        self.assertIn('\n\n[c/d]', text)

    def test_rendering_is_stable(self):
        settings = {'b/x': {'q': '1', 'a': '2'}, 'a/y': {'z': '3'}}
        self.assertEqual(render_keyfile(settings), render_keyfile(settings))

    def test_the_real_manifest_renders(self):
        manifest = load_manifest(ROOT)
        text = render_keyfile(manifest['settings'])
        self.assertIn('[org/gnome/desktop/interface]', text)
        self.assertGreater(len(text.splitlines()), 50)


class NormaliseTest(unittest.TestCase):
    def test_type_prefix_is_ignored_when_comparing(self):
        self.assertEqual(normalise("@ms 'green'"), normalise("'green'"))

    def test_unprefixed_values_are_unchanged(self):
        self.assertEqual(normalise("'Ubuntu Sans 11'"), "'Ubuntu Sans 11'")

    def test_surrounding_whitespace_is_ignored(self):
        self.assertEqual(normalise('  false  '), 'false')


class DeclaredKeyTest(unittest.TestCase):
    def test_paths_are_absolute_dconf_paths(self):
        keys = dict(declared_keys({'org/gnome/shell': {'favorite-apps': '[]'}}))
        self.assertIn('/org/gnome/shell/favorite-apps', keys)

    def test_the_real_manifest_declares_keys(self):
        keys = dict(declared_keys(load_manifest(ROOT)['settings']))
        self.assertGreater(len(keys), 50)
        for path in keys:
            self.assertTrue(path.startswith('/'), f'{path} is not a dconf path')


class VerifyTest(unittest.TestCase):
    """Verification must report drift rather than hide it."""

    def setUp(self):
        self.manifest = {'settings': {'org/example': {'colour': "'green'"}},
                         'extensions': []}

    def test_matching_value_passes(self):
        with patch.object(desktop, 'read_key', return_value="'green'"), \
             patch.object(desktop.shutil, 'which', return_value='/usr/bin/dconf'):
            checks = verify(manifest=self.manifest)
        self.assertEqual(checks[0]['status'], 'passed')

    def test_differing_value_fails(self):
        with patch.object(desktop, 'read_key', return_value="'purple'"), \
             patch.object(desktop.shutil, 'which', return_value='/usr/bin/dconf'):
            checks = verify(manifest=self.manifest)
        self.assertEqual(checks[0]['status'], 'failed')
        self.assertIn('differ', checks[0]['reason'])

    def test_type_prefix_alone_is_not_drift(self):
        with patch.object(desktop, 'read_key', return_value="@ms 'green'"), \
             patch.object(desktop.shutil, 'which', return_value='/usr/bin/dconf'):
            checks = verify(manifest=self.manifest)
        self.assertEqual(checks[0]['status'], 'passed')

    def test_unreadable_key_fails_rather_than_passing_quietly(self):
        with patch.object(desktop, 'read_key', side_effect=DesktopError('x')), \
             patch.object(desktop.shutil, 'which', return_value='/usr/bin/dconf'):
            checks = verify(manifest=self.manifest)
        self.assertEqual(checks[0]['status'], 'failed')
        self.assertIn('unreadable', checks[0]['reason'])

    def test_missing_dconf_is_deferred_not_passed(self):
        with patch.object(desktop.shutil, 'which', return_value=None):
            checks = verify(manifest=self.manifest)
        self.assertEqual(checks[0]['status'], 'deferred')

    def extension_check(self, manifest, observed):
        with patch.object(desktop, 'read_key', return_value=observed), \
             patch.object(desktop.shutil, 'which', return_value='/usr/bin/dconf'):
            checks = verify(manifest=manifest)
        return [c for c in checks if c['id'] == 'desktop-extensions'][0]

    def test_an_extension_that_should_be_enabled_and_is_not_fails(self):
        manifest = {'settings': {'org/gnome/shell': {'enabled-extensions': "['a@x']"}},
                    'extensions_enabled': ['a@x', 'b@y'], 'extensions_disabled': []}
        self.assertEqual(self.extension_check(manifest, "['a@x']")['status'], 'failed')

    def test_an_installed_extension_left_switched_off_is_not_a_failure(self):
        """Installed and enabled are different things: an extension that is
        present but deliberately off must not read as a missing setting."""
        manifest = {'settings': {'org/gnome/shell': {'enabled-extensions': "['a@x']"}},
                    'extensions_enabled': ['a@x'], 'extensions_disabled': ['b@y']}
        check = self.extension_check(manifest, "['a@x']")
        self.assertEqual(check['status'], 'passed')
        self.assertIn('1-left-off', check['reason'])

    def test_an_extension_that_should_be_off_but_is_enabled_fails(self):
        manifest = {'settings': {'org/gnome/shell': {'enabled-extensions': "['a@x', 'b@y']"}},
                    'extensions_enabled': ['a@x'], 'extensions_disabled': ['b@y']}
        self.assertEqual(self.extension_check(manifest, "['a@x', 'b@y']")['status'], 'failed')

    def test_the_real_manifest_separates_installed_from_enabled(self):
        manifest = load_manifest(ROOT)
        for key in ('extensions_installed', 'extensions_enabled', 'extensions_disabled'):
            self.assertIn(key, manifest)
        self.assertEqual(
            sorted(manifest['extensions_enabled'] + manifest['extensions_disabled']),
            sorted(manifest['extensions_installed']),
            'every installed extension must be accounted for as enabled or disabled')


@unittest.skipIf(shutil.which('dconf') is None, 'dconf is not installed')
class LiveDconfTest(unittest.TestCase):
    """Exercised against the real dconf on this machine, in a scratch path that
    no GNOME component reads."""

    SECTION = 'org/linux-os-setup/test'

    def tearDown(self):
        subprocess.run(['dconf', 'reset', '-f', f'/{self.SECTION}/'],
                       capture_output=True, check=False)

    def test_declared_values_load_and_read_back(self):
        manifest = {'settings': {self.SECTION: {'colour': "'green'", 'count': '42'}},
                    'extensions': []}
        self.assertTrue(desktop.apply(manifest=manifest))
        self.assertEqual(desktop.read_key(f'/{self.SECTION}/colour'), "'green'")
        self.assertEqual(desktop.read_key(f'/{self.SECTION}/count'), '42')

    def test_reapplying_the_same_values_reports_no_change(self):
        manifest = {'settings': {self.SECTION: {'colour': "'green'"}}, 'extensions': []}
        desktop.apply(manifest=manifest)
        self.assertFalse(desktop.apply(manifest=manifest),
                         'a second apply of identical settings must be a no-op')

    def test_verification_sees_drift_introduced_behind_its_back(self):
        manifest = {'settings': {self.SECTION: {'colour': "'green'"}}, 'extensions': []}
        desktop.apply(manifest=manifest)
        self.assertEqual(verify(manifest=manifest)[0]['status'], 'passed')
        subprocess.run(['dconf', 'write', f'/{self.SECTION}/colour', "'purple'"],
                       capture_output=True, check=True)
        self.assertEqual(verify(manifest=manifest)[0]['status'], 'failed')

    def test_a_malformed_value_is_rejected(self):
        manifest = {'settings': {self.SECTION: {'colour': 'not-a-gvariant-literal'}},
                    'extensions': []}
        with self.assertRaises(DesktopError):
            desktop.apply(manifest=manifest)


if __name__ == '__main__':
    unittest.main()
