"""The justfile and the Makefile must offer the same targets.

Two entry points exist because a brand-new machine does not have `just` on it
yet. That only helps if they stay in step, and the obvious failure is one
gaining a target the other never hears about.
"""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
JUSTFILE = ROOT / 'justfile'
MAKEFILE = ROOT / 'Makefile'
# Grouped subcommands: make spells them "vm/status", just spells the same thing
# "vm::status" because "/" is a module path separator there. Compared by the
# same name either way.
MODULES = {'vm': ROOT / 'vm/mod.just', 'update': ROOT / 'just/update.just'}

# Listing targets is each tool's own convention, not a shared workflow step.
LIST_ONLY = {'default', 'help'}


def recipes(path, prefix=''):
    targets = set()
    for line in path.read_text().splitlines():
        match = re.match(r'^([a-z][a-z0-9-]*)(\s+[^:]*)?:', line)
        if match and not line.startswith(('set ', 'mod ')):
            targets.add(prefix + match.group(1))
    return targets


def just_targets():
    targets = recipes(JUSTFILE)
    for name, path in MODULES.items():
        assert path.is_file(), f'{name} module file is missing: {path}'
        targets |= recipes(path, prefix=f'{name}/')
    return targets - LIST_ONLY


def make_targets():
    targets = set()
    for line in MAKEFILE.read_text().splitlines():
        match = re.match(r'^\.PHONY:\s*([a-z][a-z0-9/-]*)\s*$', line)
        if match:
            targets.add(match.group(1))
    return targets - LIST_ONLY


class ParityTest(unittest.TestCase):
    def test_both_entry_points_exist(self):
        self.assertTrue(JUSTFILE.is_file())
        self.assertTrue(MAKEFILE.is_file())

    def test_the_same_targets_are_offered(self):
        missing_from_make = sorted(just_targets() - make_targets())
        missing_from_just = sorted(make_targets() - just_targets())
        self.assertEqual(missing_from_make, [],
                         'targets in the justfile with no Makefile equivalent')
        self.assertEqual(missing_from_just, [],
                         'targets in the Makefile with no justfile equivalent')

    def test_the_expected_workflow_targets_are_present(self):
        expected = {'check', 'check-manifest', 'test', 'verify-static',
                    'inventory', 'review', 'update/report', 'update/apply',
                    'plan', 'preflight', 'install', 'verify',
                    'migrate-plan', 'migrate', 'migrate-secrets',
                    'vm/reset', 'vm/up', 'vm/status', 'vm/accept', 'vm/clean-cycle',
                    'vm/foundation', 'desktop-manifest'}
        for name in sorted(expected):
            self.assertIn(name, make_targets(), f'Makefile is missing {name}')
            self.assertIn(name, just_targets(), f'justfile is missing {name}')

    def test_every_make_target_documents_itself(self):
        """`make help` reads these comments; an undocumented target is invisible."""
        text = MAKEFILE.read_text()
        undocumented = [name for name in sorted(make_targets())
                        if not re.search(rf'^{re.escape(name)}:.*## ', text, re.M)]
        self.assertEqual(undocumented, [])

    def test_every_module_recipe_documents_itself(self):
        """`just --list vm` reads the doc attributes."""
        for name, path in MODULES.items():
            text = path.read_text()
            for recipe in sorted(recipes(path)):
                self.assertRegex(
                    text, rf'\[doc\("[^"]+"\)\]\n{re.escape(recipe)}\b',
                    f'{name}/{recipe} has no [doc(...)] annotation')

    def test_grouped_subcommands_use_a_slash(self):
        """The vm group is addressed as vm/<recipe>, not vm-<recipe>."""
        targets = make_targets() | just_targets()
        self.assertTrue(any(t.startswith('vm/') for t in targets))
        self.assertEqual([t for t in sorted(targets) if t.startswith('vm-')], [])


@unittest.skipIf(subprocess.run(['which', 'make'], capture_output=True).returncode != 0,
                 'make is not installed')
class MakefileBehaviourTest(unittest.TestCase):
    def make(self, *args):
        return subprocess.run(['make', '-C', str(ROOT), *args],
                              capture_output=True, text=True)

    def test_a_target_needing_config_refuses_without_it(self):
        # Run these for real rather than with -n: make does not execute recipe
        # lines under -n, so the guard would never fire and the test would pass
        # for the wrong reason. The guard exits before any command runs.
        for target in ('plan', 'preflight', 'install', 'verify', 'migrate'):
            result = self.make(target)
            self.assertNotEqual(result.returncode, 0, f'{target} ran without CONFIG')
            self.assertIn('CONFIG is required', result.stdout + result.stderr)

    def test_migration_refuses_without_a_destination(self):
        result = self.make('migrate', 'CONFIG=config/standard-split.example.json')
        self.assertNotEqual(result.returncode, 0)
        self.assertIn('HOST is required', result.stdout + result.stderr)

    def test_group_selection_is_passed_through_only_when_given(self):
        with_groups = self.make('-n', 'install', 'CONFIG=x.json', 'GROUPS=core,dev')
        self.assertIn('--manifest-groups core,dev', with_groups.stdout)
        without = self.make('-n', 'install', 'CONFIG=x.json')
        self.assertNotIn('--manifest-groups', without.stdout)

    def test_help_lists_the_targets(self):
        result = self.make('help')
        self.assertEqual(result.returncode, 0)
        for name in ('install', 'migrate', 'vm/clean-cycle'):
            self.assertIn(name, result.stdout)


if __name__ == '__main__':
    unittest.main()
