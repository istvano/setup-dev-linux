"""Cline's CLI-only archive boundary, no lifecycle hooks and read-only drift."""
import hashlib
import io
from pathlib import Path
import shutil
import sys
import tarfile
import tempfile
import types
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import destination
from workstation.cline_runtime import extract_exact, install, launcher_text, verify
from workstation.config import InputError


def make_archive(path, contents, *, extra=None, link=False):
    with tarfile.open(path, 'w:gz') as stream:
        for name, data in contents.items():
            member = tarfile.TarInfo(name)
            member.size = len(data)
            member.mode = 0o755
            stream.addfile(member, io.BytesIO(data))
        if extra:
            member = tarfile.TarInfo(extra)
            member.size = 1
            stream.addfile(member, io.BytesIO(b'x'))
        if link:
            member = tarfile.TarInfo('package/bin/cline')
            member.type = tarfile.SYMTYPE
            member.linkname = '/tmp/host'
            stream.addfile(member)


class ClineDelivery(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.home = Path(self.temp.name)
        self.selected = ['cline', 'node', 'nvm']
        self.config = {'target': {'user': 'fixture'}}
        self.contents = [
            {'package/package.json': b'{"name":"cline"}',
             'package/bin/cline': b'#!/usr/bin/env node\n',
             'package/postinstall.mjs': b'write-a-sentinel-if-executed'},
            {'package/package.json': b'{"name":"@cline/cli-linux-x64"}',
             'package/bin/cline': b'compiled-cli-fixture',
             'package/webview/index.html': b'<p>fixture asset</p>'},
        ]
        self.archives = []
        self.packages = []
        for index, (name, contents, destination_path) in enumerate(zip(
                ['cline', '@cline/cli-linux-x64'], self.contents,
                ['node_modules/cline', 'node_modules/@cline/cli-linux-x64'])):
            archive = self.home / ('archive-' + str(index) + '.tgz')
            make_archive(archive, contents)
            self.archives.append(archive)
            self.packages.append({
                'name': name, 'version': '3.0.62',
                'url': 'https://registry.npmjs.org/fixture-' + str(index),
                'destination': destination_path,
                'sha256': hashlib.sha256(archive.read_bytes()).hexdigest(),
                'sha512': hashlib.sha512(archive.read_bytes()).hexdigest(),
                'members': [{'path': path, 'size': len(data),
                             'sha256': hashlib.sha256(data).hexdigest(),
                             'executable': path == 'package/bin/cline'}
                            for path, data in contents.items()],
            })
        launcher = launcher_text('v26.8.2').encode()
        self.lock = {'node_version': 'v26.8.2', 'packages': self.packages}
        files = [{'path': 'bin/cline', 'kind': 'file',
                  'value': hashlib.sha256(launcher).hexdigest(), 'executable': True}]
        for package in self.packages:
            files += [{'path': package['destination'] + '/' + member['path'][8:],
                       'kind': 'file', 'value': member['sha256'],
                       'executable': member['executable']}
                      for member in package['members']]
        self.record = {'id': 'cline', 'version': '3.0.62', 'files': files,
                       'entrypoint': 'bin/cline'}

    def target(self):
        return destination(self.home, self.record)

    def node_pass(self, *_):
        return [{'id': 'node', 'status': 'passed'}]

    def test_exact_two_package_install_never_runs_postinstall_or_sdk(self):
        lookup = {p['url']: a.read_bytes() for p, a in zip(self.packages, self.archives)}
        with patch('workstation.cline_runtime.pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
             patch('workstation.cline_runtime.os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.cline_runtime.cline_lock', return_value=(self.lock, self.record)), \
             patch('workstation.cline_runtime.nvm_record', return_value={}), \
             patch('workstation.cline_runtime.verify_node', side_effect=self.node_pass), \
             patch('workstation.cline_runtime.urllib.request.urlopen', side_effect=lambda url, timeout: io.BytesIO(lookup[url])) as download:
            self.assertTrue(install(self.config, self.selected))
            self.assertFalse(install(self.config, self.selected))
            self.assertEqual(download.call_count, 2)
            self.assertEqual(verify(self.home, self.selected)[0]['status'], 'passed')
        target = self.target()
        self.assertEqual((target / 'node_modules/@cline/cli-linux-x64/bin/cline').read_bytes(), b'compiled-cli-fixture')
        self.assertIn('CLINE_NO_AUTO_UPDATE=1', (target / 'bin/cline').read_text())
        self.assertFalse((target / 'node_modules/cline/bin/.cline').exists())
        self.assertFalse((self.home / 'postinstall-sentinel').exists())

    def test_reject_extra_or_link_member_before_writing(self):
        payload = self.home / 'payload'
        payload.mkdir()
        archive = self.home / 'unexpected.tgz'
        make_archive(archive, self.contents[0], extra='package/hook')
        with self.assertRaisesRegex(InputError, 'unexpected-cline-archive-layout'):
            extract_exact(archive, payload, self.packages[0])
        self.assertEqual(list(payload.iterdir()), [])
        archive = self.home / 'link.tgz'
        contents = {key: value for key, value in self.contents[0].items() if key != 'package/bin/cline'}
        make_archive(archive, contents, link=True)
        with self.assertRaisesRegex(InputError, 'unsafe-cline-archive-member'):
            extract_exact(archive, payload, self.packages[0])
        self.assertEqual(list(payload.iterdir()), [])

    def test_wrong_download_digest_never_places_payload(self):
        with patch('workstation.cline_runtime.pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
             patch('workstation.cline_runtime.os.geteuid', return_value=1000), \
             patch('workstation.storage.preflight', return_value=([], 0)), \
             patch('workstation.cline_runtime.cline_lock', return_value=(self.lock, self.record)), \
             patch('workstation.cline_runtime.nvm_record', return_value={}), \
             patch('workstation.cline_runtime.verify_node', side_effect=self.node_pass), \
             patch('workstation.cline_runtime.urllib.request.urlopen', return_value=io.BytesIO(b'corrupt')):
            with self.assertRaisesRegex(InputError, 'cline-download-digest-mismatch'):
                install(self.config, self.selected)
        self.assertFalse(self.target().exists())

    def test_existing_binary_asset_or_launcher_drift_refuses_replacement(self):
        target = self.target()
        for name in ['node_modules/@cline/cli-linux-x64/bin/cline',
                     'node_modules/@cline/cli-linux-x64/webview/index.html', 'bin/cline']:
            if target.exists():
                shutil.rmtree(target)
            target.mkdir(parents=True)
            for file in self.record['files']:
                source = target / file['path']
                source.parent.mkdir(parents=True, exist_ok=True)
                if file['path'] == 'bin/cline':
                    source.write_text(launcher_text('v26.8.2'))
                else:
                    package = self.packages[0] if file['path'].startswith('node_modules/cline/') else self.packages[1]
                    source.write_bytes(self.contents[self.packages.index(package)]['package/' + file['path'].split(package['destination'] + '/', 1)[1]])
                source.chmod(0o755 if file['executable'] else 0o644)
            (target / name).write_bytes(b'deliberate-drift')
            with patch('workstation.cline_runtime.cline_lock', return_value=(self.lock, self.record)), \
                 patch('workstation.cline_runtime.nvm_record', return_value={}), \
                 patch('workstation.cline_runtime.verify_node', side_effect=self.node_pass):
                self.assertEqual(verify(self.home, self.selected)[0]['status'], 'failed')
            with patch('workstation.cline_runtime.pwd.getpwuid', return_value=types.SimpleNamespace(pw_name='fixture', pw_dir=str(self.home))), \
                 patch('workstation.cline_runtime.os.geteuid', return_value=1000), \
                 patch('workstation.storage.preflight', return_value=([], 0)), \
                 patch('workstation.cline_runtime.cline_lock', return_value=(self.lock, self.record)), \
                 patch('workstation.cline_runtime.nvm_record', return_value={}), \
                 patch('workstation.cline_runtime.verify_node', side_effect=self.node_pass), \
                 patch('workstation.cline_runtime.urllib.request.urlopen', side_effect=AssertionError('must not download')):
                with self.assertRaisesRegex(InputError, 'user-tool-tree-drift'):
                    install(self.config, self.selected)
            self.assertEqual((target / name).read_bytes(), b'deliberate-drift')


if __name__ == '__main__':
    unittest.main()
