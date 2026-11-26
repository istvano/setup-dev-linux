"""This repository sets up the Linux host; the command line belongs elsewhere.

setup-dev-linux-wsl installs every command-line tool, runtime, shell file and
dotfile, on WSL and on a Linux machine alike (docs/MOVED.md says where each one
went). What stays here is the operating system and the desktop. These tests
fail if a command-line installer, its module or its manifest entry comes back.
"""
import hashlib
import importlib.util
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'script'))

# Removed with the command-line layer (host refactor, Task 3).
CLI_PLAYBOOKS = (
    'user-tools', 'sdkman', 'java-runtime', 'jvm-tools', 'mandrel', 'go-runtime',
    'rust-runtime', 'python-user', 'node-runtime', 'npm-cli', 'opencode-runtime',
    'codex-runtime', 'cline-runtime', 'user-environment',
)
CLI_MODULES = (
    'artifacts', 'sdkman_runtime', 'java_runtime', 'jvm_tools', 'mandrel_runtime',
    'go_runtime', 'rust_runtime', 'python_user', 'node_runtime', 'npm_cli',
    'opencode_runtime', 'codex_runtime', 'cline_runtime', 'user_environment',
    'prerequisites',
)
CLI_ENTRY_POINTS = (
    'apply-user-tools', 'apply-sdkman', 'apply-java-runtime', 'apply-jvm-tools',
    'apply-mandrel', 'apply-go-runtime', 'apply-rust-runtime', 'apply-python-user',
    'apply-node-runtime', 'apply-npm-cli', 'apply-opencode-runtime',
    'apply-codex-runtime', 'apply-cline-runtime', 'apply-user-environment',
    'resolve-npm-cli',
)
CLI_MANIFESTS = ('shell', 'dotfiles', 'runtimes')

HOST_GROUPS = {'base', 'dev-gui', 'lab', 'gpu', 'desktop', 'media', 'productivity', 'ai', 'network'}
HOST_BINARIES = {'zed', 'obsidian'}
HOST_REPOSITORIES = {'vscode', 'google-chrome', 'slack', 'dbeaver', 'claude-desktop',
                     'chatgpt', 'ppa-obs', 'ppa-quickemu'}

# One Anthropic keyring on the machine, shared with setup-dev-linux-wsl's
# claude-code source, so APT never sees two Signed-By values for one vendor key.
ANTHROPIC_KEYRING = '/etc/apt/keyrings/anthropic.asc'
# sha256 of setup-dev-linux-wsl's apt/keys/anthropic.asc on its main (855b8b2).
WSL_ANTHROPIC_KEY_SHA256 = 'bd70a5e4a268002704024ceba7f8446024114e94f3f0bdd11c23a9e592be81c6'
WSL_ANTHROPIC_URI = 'https://downloads.claude.ai/claude-code/apt/stable'


def manifest(name):
    return json.loads((ROOT / 'manifest' / f'{name}.json').read_text())


class NoCliModulesTest(unittest.TestCase):
    def test_no_cli_module_is_importable(self):
        for name in CLI_MODULES:
            self.assertIsNone(importlib.util.find_spec(f'workstation.{name}'),
                              f'workstation.{name} installs command-line tools')

    def test_no_cli_playbook_exists(self):
        for name in CLI_PLAYBOOKS:
            self.assertFalse((ROOT / 'ansible' / f'{name}.yml').exists(), name)

    def test_the_controller_never_references_a_cli_playbook(self):
        for source in ('controller.py', 'cli.py'):
            text = (ROOT / 'script/workstation' / source).read_text()
            for name in CLI_PLAYBOOKS:
                self.assertNotIn(f'{name}.yml', text, f'{source} runs {name}.yml')
            for name in CLI_MODULES:
                self.assertNotIn(f'.{name} import', text, f'{source} imports {name}')

    def test_no_cli_entry_point_exists(self):
        for name in CLI_ENTRY_POINTS:
            self.assertFalse((ROOT / 'script' / name).exists(), name)

    def test_no_cli_manifest_exists(self):
        for name in CLI_MANIFESTS:
            self.assertFalse((ROOT / 'manifest' / f'{name}.json').exists(), name)

    def test_this_repository_runs_no_chezmoi(self):
        self.assertFalse((ROOT / 'user-files').exists(), 'chezmoi sources belong to setup-dev-linux-wsl')
        # The one permitted mention: check-catalogue's optional audit of the Mac
        # checkout's layout, whose chezmoi/ directory is provenance, not something run.
        mac_audit = "path.startswith(('chezmoi/', 'script/'))"
        # And the handoff's first-run hint, which only tests whether
        # setup-dev-linux-wsl's record file exists (controller ruling RB3).
        handoff_record = "RECORD = ('chezmoi', 'chezmoi.toml')"
        for path in list((ROOT / 'script').rglob('*')) + list((ROOT / 'ansible').rglob('*.yml')):
            if path.is_file() and '__pycache__' not in path.parts:
                text = path.read_text(errors='replace').replace(mac_audit, '')
                text = text.replace(handoff_record, '')
                self.assertFalse('chezmoi' in text.lower(), f'{path.relative_to(ROOT)} mentions chezmoi')


class ManifestHostOnlyTest(unittest.TestCase):
    def test_exactly_the_host_package_groups_remain(self):
        self.assertEqual(set(manifest('packages')['groups']), HOST_GROUPS)

    def test_the_gui_part_of_dev_is_dev_gui(self):
        names = {e['name'] for e in manifest('packages')['groups']['dev-gui']}
        self.assertEqual(names, {'code', 'dbeaver-ce', 'meld'})

    def test_exactly_the_host_binaries_remain(self):
        self.assertEqual({b['id'] for b in manifest('binaries')['binaries']}, HOST_BINARIES)

    def test_exactly_the_host_repositories_remain(self):
        self.assertEqual({r['id'] for r in manifest('repositories')['repositories']},
                         HOST_REPOSITORIES)

    def test_docker_the_container_toolkit_and_chezmoi_are_not_installed_here(self):
        names = {e['name'] for entries in manifest('packages')['groups'].values() for e in entries}
        names |= {b['id'] for b in manifest('binaries')['binaries']}
        names |= {s['name'] for s in manifest('snaps')['snaps']}
        for name in ('docker-ce', 'containerd.io', 'nvidia-container-toolkit', 'chezmoi'):
            self.assertNotIn(name, names)
        self.assertNotIn('docker', {g['group'] for g in manifest('system')['user_groups']})

    def test_kubectl_plugins_are_not_installed_here(self):
        self.assertNotIn('krew_plugins', manifest('plugins'))
        self.assertTrue(manifest('plugins')['vscode_extensions'])

    def test_ppa_management_stays_on_the_host(self):
        """RB6: software-properties-common manages the obs and quickemu PPAs."""
        names = {e['name'] for entries in manifest('packages')['groups'].values() for e in entries}
        self.assertIn('software-properties-common', names)

    def test_every_group_a_binary_or_snap_names_exists(self):
        groups = set(manifest('packages')['groups'])
        for item in manifest('binaries')['binaries'] + manifest('snaps')['snaps']:
            self.assertIn(item['group'], groups, item.get('id') or item.get('name'))


class AnthropicKeyringTest(unittest.TestCase):
    def setUp(self):
        repositories = manifest('repositories')['repositories']
        self.claude = next(r for r in repositories if r['id'] == 'claude-desktop')

    def test_claude_desktop_uses_the_shared_anthropic_keyring(self):
        self.assertEqual(self.claude.get('keyring'), ANTHROPIC_KEYRING)

    def test_the_vendored_key_is_byte_identical_to_setup_dev_linux_wsl(self):
        data = (ROOT / self.claude['key_file']).read_bytes()
        self.assertEqual(hashlib.sha256(data).hexdigest(), WSL_ANTHROPIC_KEY_SHA256)

    def test_no_host_source_shares_a_uri_with_setup_dev_linux_wsl(self):
        """Same keyring path is fine; the same URI under another Signed-By is not."""
        uris = {r['uri'].rstrip('/') for r in manifest('repositories')['repositories']}
        self.assertNotIn(WSL_ANTHROPIC_URI, uris)
        for wsl_uri in ('https://download.docker.com/linux/ubuntu',
                        'https://packages.microsoft.com/repos/azure-cli',
                        'https://packages.cloud.google.com/apt'):
            self.assertNotIn(wsl_uri, uris)


class CatalogueHostOnlyTest(unittest.TestCase):
    def test_no_selected_capability_is_a_command_line_item(self):
        target = set(json.loads((ROOT / 'profiles/target.json').read_text())['capability_ids'])
        for name in ('chezmoi', 'docker-engine', 'nvidia-container-toolkit', 'kubectl',
                     'node', 'java', 'oh-my-zsh', 'shell-integration', 'krew-neat', 'zsh'):
            self.assertNotIn(name, target)

    def test_no_selected_capability_is_owned_by_a_cli_manager(self):
        catalogue = json.loads((ROOT / 'catalogue/capabilities.json').read_text())
        owners = {e['owner'] for e in catalogue['capabilities']}
        for owner in ('chezmoi', 'nvm', 'sdkman', 'krew', 'rustup'):
            self.assertNotIn(owner, owners)

    def test_the_user_environment_preferences_are_gone(self):
        self.assertEqual(sorted(p.name for p in (ROOT / 'profiles').glob('user-environment*')), [])


if __name__ == '__main__':
    unittest.main()
