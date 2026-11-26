"""Nothing the manifests install may disappear without a recorded destination.

tests/fixtures/manifest-before.json is a snapshot of every item the manifests
installed before the host refactor. docs/MOVED.md says where each command-line
item went (setup-dev-linux-wsl) or why it was dropped. An item that leaves the
manifests without a row fails here.
"""
import json
import re
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'tests' / 'fixtures'))

from snapshot_manifest import items  # noqa: E402

BEFORE = json.loads((ROOT / 'tests' / 'fixtures' / 'manifest-before.json').read_text())

# Profiles on setup-dev-linux-wsl main, plus the apt base list.
WSL_LABELS = {
    'base', 'ai-agents', 'backup', 'cloud', 'cloud-aws', 'cloud-azure', 'cloud-gcp',
    'core', 'dev', 'docs', 'gpu-nvidia', 'kubernetes', 'productivity-extra',
    'runtime-docker', 'security', 'security-scan', 'shell-zsh',
}
# Rows of docs/DROPPED.md on setup-dev-linux-wsl main (the Name column).
DROPPED_ROWS = {
    'sdkman', 'nvm', 'oh-my-zsh (+ agnoster theme)', 'httpie',
    'Mandrel / GraalVM via SDKMAN',
}
# script/docker-setup: where setup-dev-linux-wsl adds the operator to the docker group.
FILE = (r'(?:profiles/[a-z0-9-]+\.Brewfile|apt/base\.list|apt/vendor\.list'
        r'|chezmoi/[A-Za-z0-9_./-]+|script/docker-setup)')
MOVED = re.compile(r'^setup-dev-linux-wsl:([a-z0-9-]+) \((' + FILE + r')\)$')
DROPPED = re.compile(r'^dropped:(?! )(.+)$')
# Decision-reference forms. The test cannot reach setup-dev-linux-wsl, so it checks the
# form and a closed set of ADR numbers verified against that repository's main
# docs/DECISIONS.md (ADR-010: sniff not carried; ADR-014: Java 25 / Temurin).
ADR = re.compile(r'^dropped: setup-dev-linux-wsl ADR-(\d{3}) \(.+\)$')
MISE_JAVA = re.compile(r'^setup-dev-linux-wsl: mise java temurin-\d+( / temurin-\d+)* \(.+; ADR-(\d{3})\)$')
ADRS = {'010', '014'}

# What stays on the host: these must remain in the manifests.
HOST_KEPT = {
    'repository:vscode', 'repository:google-chrome', 'repository:slack',
    'repository:dbeaver', 'repository:claude-desktop', 'repository:chatgpt',
    'repository:ppa-obs', 'repository:ppa-quickemu',
    'snap:firefox', 'snap:thunderbird', 'snap:bitwarden', 'snap:remmina',
    'binary:zed', 'binary:obsidian',
    'package:code', 'package:dbeaver-ce', 'package:meld',
    'package:google-chrome-stable', 'package:slack-desktop',
    'package:claude-desktop', 'package:chatgpt',
}


def rows():
    table = {}
    for line in (ROOT / 'docs' / 'MOVED.md').read_text().splitlines():
        cells = [c.strip().strip('`') for c in line.strip().strip('|').split('|')]
        if line.startswith('|') and len(cells) >= 2 and ':' in cells[0] and cells[0] != 'Item':
            table.setdefault(cells[0], []).append(cells[1])
    return table


class LosslessTableTest(unittest.TestCase):
    def test_every_removed_item_is_accounted_for(self):
        table = rows()
        gone = sorted(set(BEFORE) - set(items()))
        missing = [i for i in gone if i not in table]
        self.assertEqual(missing, [], 'removed from the manifests with no row in docs/MOVED.md')
        duplicated = [i for i in gone if len(table[i]) != 1]
        self.assertEqual(duplicated, [], 'more than one MOVED.md row')

    def test_moved_destinations_are_concrete(self):
        for item, dests in rows().items():
            for dest in dests:
                m = MOVED.match(dest)
                if m:
                    self.assertIn(m.group(1), WSL_LABELS, f'{item}: unknown profile in {dest}')
                    continue
                a = ADR.match(dest)
                if a:
                    self.assertIn(a.group(1), ADRS, f'{item}: unknown ADR in {dest}')
                    continue
                a = MISE_JAVA.match(dest)
                if a:
                    self.assertIn(a.group(2), ADRS, f'{item}: unknown ADR in {dest}')
                    continue
                d = DROPPED.match(dest)
                self.assertTrue(d, f'{item}: destination {dest!r} is neither a profile/file nor a DROPPED row')
                self.assertIn(d.group(1), DROPPED_ROWS, f'{item}: no such DROPPED.md row {dest!r}')

    def test_rows_name_real_items(self):
        for item in rows():
            self.assertIn(item, BEFORE, f'{item} was never in the manifests (typo?)')

    def test_nothing_the_host_keeps_has_a_moved_row(self):
        for item in HOST_KEPT:
            self.assertIn(item, BEFORE)
            self.assertNotIn(item, rows(), f'{item} stays on the host')

    def test_host_kept_items_are_still_installed(self):
        self.assertEqual(sorted(HOST_KEPT - set(items())), [], 'a host item was removed')


if __name__ == '__main__':
    unittest.main()
