"""This repository provisions fresh machines only: no migration, no file copy."""
import re
import subprocess
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
PATTERN = re.compile(r'\bmigrat(e|ion)\b|rsync', re.I)
# docs/DECISIONS.md and docs/superpowers keep the history; specs and the older
# evidence documents are records of what was built and are not live surface.
SCANNED = ('script', 'tests', 'manifest', 'catalogue', 'profiles', 'vm',
           'justfile', 'Makefile', 'bootstrap', 'README.md', 'AGENTS.md',
           'docs/NEW-MACHINE.md', 'docs/ARCHITECTURE.md', 'docs/TESTING.md',
           'docs/OPERATIONS.md', 'docs/README.md', 'docs/CAPABILITY-MATRIX.md')
# docs/software-review.md is hash-verified by check-catalogue and must not be
# edited; its Remmina row ("... and migrate profiles") is carried verbatim into the
# catalogue as provenance and into the generated matrix. That is source text, not a
# command or feature.
PROVENANCE = 'reconcile installation channel and migrate profiles'


def files():
    for name in SCANNED:
        path = ROOT / name
        if path.is_file():
            yield path
        elif path.is_dir():
            for item in sorted(path.rglob('*')):
                if (item.is_file() and not item.is_symlink()
                        and '__pycache__' not in item.parts
                        and item.suffix not in ('.pyc', '.tar', '.gz', '.zst')):
                    yield item


class NoMigrationSurfaceTest(unittest.TestCase):
    def test_bootstrap_migrate_is_an_unknown_command(self):
        result = subprocess.run(
            [sys.executable, '-B', str(ROOT / 'bootstrap'), 'migrate',
             '--config', 'x.json'], cwd=ROOT, capture_output=True, text=True)
        self.assertEqual(result.returncode, 2, result.stdout + result.stderr)
        self.assertIn('invalid-command-line', result.stdout + result.stderr)

    def test_the_removed_options_are_rejected(self):
        for option in ('--to', '--secrets', '--dry-run', '--rsh', '--remote-home',
                       '--only-trees', '--source-home'):
            args = ['install', '--config', 'x.json', option]
            if option not in ('--secrets', '--dry-run'):
                args.append('v')
            result = subprocess.run(
                [sys.executable, '-B', str(ROOT / 'bootstrap'), *args],
                cwd=ROOT, capture_output=True, text=True)
            self.assertEqual(result.returncode, 2, option)
            self.assertIn('invalid-command-line', result.stdout + result.stderr, option)

    def test_no_file_mentions_migration_or_rsync(self):
        me = Path(__file__).resolve()
        hits = []
        for path in files():
            if path.resolve() == me:
                continue
            for number, line in enumerate(path.read_text(errors='replace').splitlines(), 1):
                if PATTERN.search(line) and PROVENANCE not in line:
                    hits.append(f'{path.relative_to(ROOT)}:{number}: {line.strip()[:100]}')
        self.assertEqual(hits, [])

    def test_the_migration_files_are_gone(self):
        for name in ('script/workstation/migrate.py', 'tests/test_migrate.py',
                     'manifest/migrate.json', 'vm/migration_leak_check.py'):
            self.assertFalse((ROOT / name).exists(), name)


if __name__ == '__main__':
    unittest.main()
