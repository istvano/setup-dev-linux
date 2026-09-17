import json
from pathlib import Path
import runpy
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import InputError
from workstation.user_environment import BEGIN, END, merge_include, render, settings


class UserFiles(unittest.TestCase):
    def test_existing_content_preserved_and_include_not_duplicated(self):
        original = '# unrelated custom function\nfunction retained() { :; }\n'
        once = merge_include(original, 'source managed')
        self.assertTrue(once.startswith(original))
        self.assertEqual(merge_include(once, 'source managed'), once)

    def test_conflicting_markers_fail(self):
        for value in [BEGIN, END, END + '\n' + BEGIN, BEGIN + '\n' + BEGIN + '\n' + END]:
            with self.subTest(value=value), self.assertRaises(InputError):
                merge_include(value, 'source managed')

    def test_no_implicit_identity_or_prerequisite_install(self):
        with tempfile.TemporaryDirectory() as temp:
            files, owners, deferred = render(Path(temp), ['git-identity', 'shell-integration'], {}, {})
        self.assertEqual(files, {})
        self.assertEqual(set(deferred), {'git-identity', 'shell-integration'})

    def test_uv_only_shell_disables_automatic_python_downloads(self):
        from unittest.mock import patch
        tools = {
            'chezmoi': {'id': 'chezmoi', 'version': 'fixture', 'entrypoint': 'chezmoi'},
            'oh-my-zsh': {'id': 'oh-my-zsh', 'version': 'fixture', 'entrypoint': 'source/oh-my-zsh.sh'},
        }
        uv = {'id': 'uv', 'version': 'fixture', 'entrypoint': 'bundle/uv'}
        python = {'id': 'python', 'version': 'fixture', 'entrypoint': 'runtime/bin/python'}
        selected = ['shell-integration', 'chezmoi', 'oh-my-zsh', 'zsh',
                    'zsh-autosuggestions', 'zsh-syntax-highlighting', 'uv']
        with tempfile.TemporaryDirectory() as temp, \
                patch('workstation.python_user.python_lock', return_value=(uv, python)):
            files, _, deferred = render(Path(temp), selected, {}, tools)
        self.assertEqual(deferred, [])
        shell = files['.config/linux-os-setup/shell.zsh']
        self.assertIn('export UV_PYTHON_DOWNLOADS=never', shell)
        self.assertIn('/tools/uv/fixture/bundle', shell)
        self.assertNotIn('UV_PYTHON_INSTALL_DIR', shell)
        self.assertNotIn('/tools/python/', shell)

    def test_failed_backup_prevents_chezmoi_and_replacement(self):
        import pwd
        import types
        from unittest.mock import patch
        from workstation.user_environment import apply
        with tempfile.TemporaryDirectory() as temp:
            home = Path(temp)
            existing = home / '.zshrc'
            existing.write_text('# preserve this configuration\n')
            account = types.SimpleNamespace(pw_name='fixture', pw_dir=str(home))
            tools = {'chezmoi': {'id': 'chezmoi', 'version': 'v1', 'entrypoint': 'chezmoi'},
                     'oh-my-zsh': {'id': 'oh-my-zsh', 'version': 'v1', 'entrypoint': 'source/oh-my-zsh.sh'}}
            selected = ['shell-integration', 'chezmoi', 'oh-my-zsh', 'zsh', 'zsh-autosuggestions', 'zsh-syntax-highlighting']
            with patch('workstation.user_environment.pwd.getpwuid', return_value=account), \
                    patch('workstation.storage.preflight', return_value=([], 0)), \
                    patch('workstation.user_environment.validate_payload'), \
                    patch.object(Path, 'write_bytes', side_effect=PermissionError('fixture backup unavailable')), \
                    patch('workstation.user_environment.subprocess.run') as command:
                with self.assertRaises(PermissionError):
                    apply({'target': {'user': 'fixture'}}, selected, {}, tools)
            command.assert_not_called()
            self.assertEqual(existing.read_text(), '# preserve this configuration\n')

    def test_private_identity_is_redacted_from_plan(self):
        import subprocess
        with tempfile.TemporaryDirectory() as temp:
            directory = Path(temp)
            private = directory / 'private.json'
            private.write_text(json.dumps({'schema_version': 1, 'identities': [{'scope': 'work', 'directory': '/synthetic-work', 'name': 'PRIVATE-IDENTITY-MARKER', 'email': 'private@example.invalid'}]}))
            private.chmod(0o600)
            config = json.loads((ROOT / 'config/standard-split.example.json').read_text())
            config['selection_file'] = str(ROOT / 'profiles/default.json')
            config['user_settings_file'] = str(private)
            path = directory / 'machine.json'
            path.write_text(json.dumps(config))
            result = subprocess.run([str(ROOT / 'bootstrap'), 'plan', '--config', str(path), '--format', 'json'], text=True, capture_output=True)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotIn('PRIVATE-IDENTITY-MARKER', result.stdout)
            self.assertNotIn('private@example.invalid', result.stdout)
            self.assertTrue(json.loads(result.stdout)['provenance']['user_settings_sha256'])

    def test_settings_private_and_nonoverlapping(self):
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'settings.json'
            value = {'schema_version': 1, 'identities': [
                {'scope': 'personal', 'name': 'Fixture', 'email': 'fixture@example.invalid', 'directory': '/projects'},
                {'scope': 'work', 'name': 'Work', 'email': 'work@example.invalid', 'directory': '/projects/work'}]}
            path.write_text(json.dumps(value))
            path.chmod(0o644)
            with self.assertRaisesRegex(InputError, 'private'):
                settings(path)
            path.chmod(0o600)
            with self.assertRaisesRegex(InputError, 'overlapping'):
                settings(path)


class ProxyInput(unittest.TestCase):
    def setUp(self):
        self.reader = runpy.run_path(str(ROOT / 'user-files/proxy-settings.py'))['read_settings']
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.path = Path(self.temp.name) / 'proxy.json'
        self.path.write_text(json.dumps(dict(http_proxy='http://127.0.0.1:12345', https_proxy='', all_proxy='', no_proxy='localhost')))
        self.path.chmod(0o600)

    def test_private_valid_values(self):
        self.assertEqual(self.reader(self.path)['no_proxy'], 'localhost')

    def test_public_settings_rejected(self):
        self.path.chmod(0o644)
        with self.assertRaises(ValueError):
            self.reader(self.path)

    def test_duplicate_keys_rejected(self):
        self.path.write_text('{"http_proxy":"", "http_proxy":""}')
        with self.assertRaises(ValueError):
            self.reader(self.path)

    def test_symlink_rejected(self):
        link = self.path.with_name('linked')
        link.symlink_to(self.path)
        with self.assertRaises(OSError):
            self.reader(link)

    def test_control_characters_rejected(self):
        value = json.loads(self.path.read_text())
        value['no_proxy'] = 'localhost\nsecret'
        self.path.write_text(json.dumps(value))
        with self.assertRaises(ValueError):
            self.reader(self.path)

class DeclarationMatchesDeliveryTest(unittest.TestCase):
    """manifest/dotfiles.json must declare exactly what is delivered.

    Declaring a file nothing installs is how a new machine ends up with the
    starship binary and no prompt configuration.
    """

    def rendered(self):
        import json
        tools = {a['id']: a for a in
                 json.loads((ROOT / 'locks/user-tools.json').read_text())['artifacts']}
        selected = {'shell-integration', 'git-identity', 'chezmoi', 'git', 'oh-my-zsh',
                    'zsh', 'zsh-autosuggestions', 'zsh-syntax-highlighting',
                    'starship', 'atuin'}
        private = {'identities': [{'scope': 'personal', 'directory': '/tmp/fixture',
                                   'name': 'Fixture', 'email': 'fixture@example.invalid'}]}
        files, _, deferred = render(Path('/home/fixture'), selected, private, tools, ROOT)
        self.assertEqual(deferred, [], 'the fixture selection should defer nothing')
        return set(files)

    def declared(self):
        import json
        manifest = json.loads((ROOT / 'manifest/dotfiles.json').read_text())
        return {entry['path'] for entry in manifest['managed']}

    def test_every_declared_dotfile_is_delivered(self):
        undelivered = sorted(self.declared() - self.rendered())
        self.assertEqual(undelivered, [],
                         'declared in manifest/dotfiles.json but nothing writes it')

    def test_the_prompt_configuration_is_delivered_when_starship_is_selected(self):
        self.assertIn('.config/starship.toml', self.rendered())

    def test_the_prompt_is_actually_started(self):
        """ZSH_THEME is empty in the managed shell, so the configuration file
        renders nothing unless starship is initialised."""
        import json
        tools = {a['id']: a for a in
                 json.loads((ROOT / 'locks/user-tools.json').read_text())['artifacts']}
        selected = {'shell-integration', 'chezmoi', 'oh-my-zsh', 'zsh',
                    'zsh-autosuggestions', 'zsh-syntax-highlighting', 'starship', 'atuin'}
        files, _, _ = render(Path('/home/fixture'), selected, {}, tools, ROOT)
        shell = files['.config/linux-os-setup/shell.zsh']
        self.assertIn('starship init zsh', shell)
        self.assertIn('atuin init zsh', shell)

    def test_tool_configuration_is_absent_when_the_tool_is_not_selected(self):
        import json
        tools = {a['id']: a for a in
                 json.loads((ROOT / 'locks/user-tools.json').read_text())['artifacts']}
        selected = {'shell-integration', 'chezmoi', 'oh-my-zsh', 'zsh',
                    'zsh-autosuggestions', 'zsh-syntax-highlighting'}
        files, _, _ = render(Path('/home/fixture'), selected, {}, tools, ROOT)
        self.assertNotIn('.config/starship.toml', files)
        self.assertNotIn('.config/atuin/config.toml', files)
        self.assertNotIn('starship init', files['.config/linux-os-setup/shell.zsh'])

    def test_private_dotfiles_are_never_declared_as_managed(self):
        """A committed .npmrc would carry an employer registry and address."""
        import json
        manifest = json.loads((ROOT / 'manifest/dotfiles.json').read_text())
        never = {entry['path'] for entry in manifest['never_managed']}
        self.assertIn('.npmrc', never)
        self.assertEqual(self.declared() & never, set())



if __name__ == '__main__':
    unittest.main()
