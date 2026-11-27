"""The manifest is the delivery authority; nothing may be lost between the
reviewed decision and what a machine actually installs."""
import json
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'script'))

from workstation.manifest import ALIASES, covers, delivered, load  # noqa: E402


class RouteTest(unittest.TestCase):
    def setUp(self):
        self.manifest = load(ROOT)
        self.routes = delivered(self.manifest)

    def test_every_route_names_how_it_installs(self):
        for name, route in self.routes.items():
            self.assertTrue(
                route.startswith('apt:') or route in ('snap', 'binary'),
                f'{name} has an unrecognised route {route}')

    def test_archive_packages_are_distinguished_from_third_party(self):
        self.assertEqual(self.routes['ffmpeg'], 'apt:archive')
        self.assertEqual(self.routes['code'], 'apt:vscode')

    def test_capability_spelled_differently_is_still_covered(self):
        self.assertTrue(covers(self.routes, 'dbeaver'), 'dbeaver is packaged as dbeaver-ce')
        self.assertTrue(covers(self.routes, 'vscode'), 'vscode is packaged as code')

    def test_something_the_manifest_does_not_install_is_not_covered(self):
        self.assertFalse(covers(self.routes, 'emacs'))
        self.assertFalse(covers(self.routes, 'kubectl'), 'kubectl belongs to setup-dev-linux-wsl')
        self.assertFalse(covers(self.routes, 'docker-ce'), 'Docker belongs to setup-dev-linux-wsl')

    def test_ubuntu_desktop_defaults_are_delivered(self):
        """D035: the default apps are declared, so verify checks them."""
        for capability in ('libreoffice', 'rhythmbox', 'shotwell', 'showtime', 'gnome-disks',
                           'deja-dup', 'baobab', 'resources', 'transmission',
                           'scanner-utilities'):
            self.assertTrue(covers(self.routes, capability), capability)
            self.assertEqual(self.routes[ALIASES.get(capability, capability)], 'apt:archive')

    def test_every_alias_target_is_actually_delivered(self):
        for source, target in ALIASES.items():
            self.assertIn(target, self.routes,
                          f'alias {source} points at {target}, which nothing delivers')


class PinningTest(unittest.TestCase):
    def setUp(self):
        self.manifest = load(ROOT)

    def test_every_binary_is_pinned_before_it_may_install(self):
        for binary in self.manifest['binaries']['binaries']:
            self.assertTrue(binary['version'], f"{binary['id']} has no version")
            self.assertTrue(binary['url'], f"{binary['id']} has no url")
            self.assertRegex(binary['sha256'], r'^[0-9a-f]{64}$',
                             f"{binary['id']} has no usable checksum")
            self.assertTrue(binary['licence'], f"{binary['id']} records no licence")

    def test_every_third_party_repository_pins_its_signing_key(self):
        for repo in self.manifest['repositories']['repositories']:
            self.assertRegex(repo.get('key_fingerprint', ''), r'^[0-9A-F]{40}$',
                             f"{repo['id']} does not pin a signing key")
            self.assertTrue(repo.get('key_url') or repo.get('key_file'),
                            f"{repo['id']} has no key source")

    def test_every_third_party_package_names_a_declared_repository(self):
        declared = {r['id'] for r in self.manifest['repositories']['repositories']}
        for group, entries in self.manifest['packages']['groups'].items():
            for entry in entries:
                if entry['source'] != 'archive':
                    self.assertIn(entry['source'], declared,
                                  f"{entry['name']} names an undeclared repository")


class CoverageCommandTest(unittest.TestCase):
    """check-manifest is the gate that stops a reviewed selection from
    silently failing to reach installation."""

    def run_checker(self):
        return subprocess.run([sys.executable, '-B', str(ROOT / 'script/check-manifest')],
                              capture_output=True, text=True)

    def test_the_repository_passes_its_own_coverage_check(self):
        self.assertEqual(self.run_checker().returncode, 0)

    def test_every_kept_selection_has_a_delivery(self):
        curation = json.loads((ROOT / 'catalogue/curation.json').read_text())
        routes = delivered(load(ROOT))
        undelivered = [item['id'] for item in curation['items']
                       if item['proposal'] == 'keep' and not covers(routes, item['id'])]
        self.assertEqual(undelivered, [])


if __name__ == '__main__':
    unittest.main()
