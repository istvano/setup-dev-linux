"""Agent CLIs pinned to exact npm tarballs.

A tarball's SHA-256 covers everything inside it, and the executable's own digest
is recorded separately so replacement after installation is detectable. npm is
never invoked and no version is resolved at install time.
"""
import hashlib
import io
import json
import shutil
import sys
import tarfile
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))

from workstation import npm_cli  # noqa: E402
from workstation.config import InputError  # noqa: E402
from workstation.npm_cli import executable, install, lock, verify  # noqa: E402

BINARY = b'#!/bin/sh\necho pinned\n'


def make_tarball(entrypoint=b'package/tool', content=BINARY, mode=0o755):
    buffer = io.BytesIO()
    with tarfile.open(fileobj=buffer, mode='w:gz') as archive:
        info = tarfile.TarInfo(entrypoint.decode())
        info.size = len(content)
        info.mode = mode
        archive.addfile(info, io.BytesIO(content))
    return buffer.getvalue()


class LockValidationTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.root, ignore_errors=True)
        (self.root / 'locks').mkdir()

    def write(self, **overrides):
        record = {
            'schema_version': 1, 'id': 'tool', 'version': '1.0',
            'licence': 'x', 'entrypoint': 'package/tool',
            'entrypoint_sha256': 'a' * 64, 'platform_package': 'tool-linux-x64',
            'packages': [
                {'name': 'tool', 'version': '1.0',
                 'url': 'https://registry.npmjs.org/tool/-/tool-1.0.tgz', 'sha256': 'b' * 64},
                {'name': 'tool-linux-x64', 'version': '1.0',
                 'url': 'https://registry.npmjs.org/tool-linux-x64/-/x-1.0.tgz',
                 'sha256': 'c' * 64}],
        }
        record.update(overrides)
        (self.root / 'locks/tool.json').write_text(json.dumps(record))

    def test_a_valid_lock_loads(self):
        self.write()
        self.assertEqual(lock('tool', self.root)['version'], '1.0')

    def test_a_package_from_outside_npm_is_refused(self):
        self.write(packages=[
            {'name': 'tool', 'version': '1.0',
             'url': 'https://example.invalid/tool.tgz', 'sha256': 'b' * 64},
            {'name': 'tool-linux-x64', 'version': '1.0',
             'url': 'https://registry.npmjs.org/x/-/x-1.0.tgz', 'sha256': 'c' * 64}])
        with self.assertRaises(InputError):
            lock('tool', self.root)

    def test_an_unpinned_package_is_refused(self):
        self.write(packages=[
            {'name': 'tool', 'version': '1.0',
             'url': 'https://registry.npmjs.org/tool/-/tool-1.0.tgz', 'sha256': ''},
            {'name': 'tool-linux-x64', 'version': '1.0',
             'url': 'https://registry.npmjs.org/x/-/x-1.0.tgz', 'sha256': 'c' * 64}])
        with self.assertRaises(InputError):
            lock('tool', self.root)

    def test_an_unpinned_entrypoint_is_refused(self):
        self.write(entrypoint_sha256='')
        with self.assertRaises(InputError):
            lock('tool', self.root)

    def test_an_escaping_entrypoint_is_refused(self):
        self.write(entrypoint='../../etc/passwd')
        with self.assertRaises(InputError):
            lock('tool', self.root)

    def test_an_identity_mismatch_is_refused(self):
        self.write(id='other')
        with self.assertRaises(InputError):
            lock('tool', self.root)


class InstallTest(unittest.TestCase):
    def setUp(self):
        self.root = Path(tempfile.mkdtemp())
        self.home = Path(tempfile.mkdtemp())
        self.addCleanup(self.cleanup)
        (self.root / 'locks').mkdir()
        self.tarball = make_tarball()
        self.write()

    def cleanup(self):
        for base in (self.root, self.home):
            for path in sorted(base.rglob('*'), reverse=True):
                if not path.is_symlink():
                    try:
                        path.chmod(0o700)
                    except OSError:
                        pass
            shutil.rmtree(base, ignore_errors=True)

    def write(self, **overrides):
        record = {
            'schema_version': 1, 'id': 'tool', 'version': '1.0', 'licence': 'x',
            'entrypoint': 'package/tool',
            'entrypoint_sha256': hashlib.sha256(BINARY).hexdigest(),
            'platform_package': 'tool-linux-x64',
            'packages': [
                {'name': 'tool', 'version': '1.0',
                 'url': 'https://registry.npmjs.org/tool/-/tool-1.0.tgz',
                 'sha256': hashlib.sha256(b'entry').hexdigest()},
                {'name': 'tool-linux-x64', 'version': '1.0',
                 'url': 'https://registry.npmjs.org/tool-linux-x64/-/x-1.0.tgz',
                 'sha256': hashlib.sha256(self.tarball).hexdigest()}],
        }
        record.update(overrides)
        (self.root / 'locks/tool.json').write_text(json.dumps(record))

    def payloads(self, entry=b'entry', platform=None):
        platform = self.tarball if platform is None else platform

        def fake(package):
            return entry if package['name'] == 'tool' else platform
        return fake

    def test_the_pinned_executable_is_placed_and_sealed(self):
        with patch.object(npm_cli, 'fetch', side_effect=self.payloads()):
            self.assertTrue(install(self.home, 'tool', self.root))
        binary = executable(self.home, lock('tool', self.root))
        self.assertTrue(binary.is_file() and binary.stat().st_mode & 0o111)
        self.assertEqual(binary.read_bytes(), BINARY)
        self.assertFalse(binary.parent.stat().st_mode & 0o222,
                         'the installed payload must be read-only')

    def test_a_second_install_changes_nothing(self):
        with patch.object(npm_cli, 'fetch', side_effect=self.payloads()):
            install(self.home, 'tool', self.root)
            self.assertFalse(install(self.home, 'tool', self.root))

    def test_a_tampered_tarball_is_refused(self):
        with patch.object(npm_cli, 'fetch', side_effect=InputError('digest-mismatch')):
            with self.assertRaises(InputError):
                install(self.home, 'tool', self.root)

    def test_a_tarball_whose_executable_is_not_the_pinned_one_is_refused(self):
        other = make_tarball(content=b'different binary')
        self.write(packages=[
            {'name': 'tool', 'version': '1.0',
             'url': 'https://registry.npmjs.org/tool/-/tool-1.0.tgz',
             'sha256': hashlib.sha256(b'entry').hexdigest()},
            {'name': 'tool-linux-x64', 'version': '1.0',
             'url': 'https://registry.npmjs.org/tool-linux-x64/-/x-1.0.tgz',
             'sha256': hashlib.sha256(other).hexdigest()}])
        with patch.object(npm_cli, 'fetch', side_effect=self.payloads(platform=other)):
            with self.assertRaises(InputError):
                install(self.home, 'tool', self.root)

    def test_verification_detects_a_replaced_executable(self):
        with patch.object(npm_cli, 'fetch', side_effect=self.payloads()):
            install(self.home, 'tool', self.root)
        binary = executable(self.home, lock('tool', self.root))
        binary.parent.chmod(0o700)
        binary.chmod(0o755)
        binary.write_bytes(b'replaced')
        self.assertEqual(verify(self.home, 'tool', self.root)[0]['reason'],
                         'does-not-match-the-pinned-executable')

    def test_not_installed_is_reported(self):
        self.assertEqual(verify(self.home, 'tool', self.root)[0]['reason'], 'not-installed')


class RealLockTest(unittest.TestCase):
    """The repository's own agent locks must be well formed."""

    def test_both_agent_locks_are_valid_and_pinned_to_npm(self):
        for identifier in ('claude-code', 'copilot'):
            record = lock(identifier, ROOT)
            self.assertEqual(len(record['packages']), 2)
            for package in record['packages']:
                self.assertTrue(package['url'].startswith('https://registry.npmjs.org/'))
                self.assertRegex(package['sha256'], r'^[0-9a-f]{64}$')
            self.assertRegex(record['entrypoint_sha256'], r'^[0-9a-f]{64}$')

    def test_the_manifest_names_a_lock_for_every_pinned_agent(self):
        agents = json.loads((ROOT / 'manifest/runtimes.json').read_text())['agents']
        pinned = [a for a in agents if a.get('delivery') == 'npm-pinned']
        self.assertTrue(pinned)
        for agent in pinned:
            self.assertTrue((ROOT / 'locks' / f"{agent['lock_id']}.json").is_file(),
                            f"{agent['id']} names a lock that does not exist")


if __name__ == '__main__':
    unittest.main()
