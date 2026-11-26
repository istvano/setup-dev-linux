"""List every item the manifests install, one stable identifier each.

Run once to (re)generate tests/fixtures/manifest-before.json; tests/test_moved.py
imports items() to see what the manifests install now. A manifest file that no
longer exists contributes nothing: that is how a removal shows up.

    python3 -B tests/fixtures/snapshot_manifest.py > tests/fixtures/manifest-before.json
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent


def _load(root, name):
    path = Path(root) / 'manifest' / f'{name}.json'
    return json.loads(path.read_text()) if path.exists() else {}


def items(root=ROOT):
    out = set()
    for entries in _load(root, 'packages').get('groups', {}).values():
        out.update(f'package:{e["name"]}' for e in entries)
    out.update(f'repository:{r["id"]}' for r in _load(root, 'repositories').get('repositories', []))
    out.update(f'snap:{s["name"]}' for s in _load(root, 'snaps').get('snaps', []))
    out.update(f'binary:{b["id"]}' for b in _load(root, 'binaries').get('binaries', []))
    runtimes = _load(root, 'runtimes')
    out.update(f'agent:{a["id"]}' for a in runtimes.get('agents', []))
    node = runtimes.get('node', {})
    if node.get('manager'):
        out.add(f'runtime:{node["manager"]}')
        out.update(f'runtime:node-global:{g}' for g in node.get('globals', []))
    jvm = runtimes.get('jvm', {})
    if jvm.get('manager'):
        out.add(f'runtime:{jvm["manager"]}')
        out.update(f'runtime:java:{j}' for j in jvm.get('java', []))
        out.update(f'runtime:jvm-tool:{t}' for t in jvm.get('tools', []))
        if jvm.get('mandrel'):
            out.add('runtime:mandrel')
    if runtimes.get('python', {}).get('manager'):
        out.add(f'runtime:{runtimes["python"]["manager"]}')
    shell = _load(root, 'shell')
    if shell.get('framework'):
        fw = shell['framework']
        out.add(f'shell:{fw["name"]}')
        out.update(f'shell:{p}' for p in fw.get('custom_plugins', []))
    if shell.get('prompt'):
        out.add(f'shell:{shell["prompt"]["name"]}')
    if shell.get('history'):
        out.add(f'shell:{shell["history"]["name"]}')
    out.update(f'shell:{h}' for h in shell.get('helpers', {}).get('proxy', []))
    out.update(f'dotfile:{d["path"]}' for d in _load(root, 'dotfiles').get('managed', []))
    plugins = _load(root, 'plugins')
    out.update(f'vscode:{e}' for e in plugins.get('vscode_extensions', []))
    out.update(f'krew:{k}' for k in plugins.get('krew_plugins', []))
    return sorted(out)


if __name__ == '__main__':
    json.dump(items(), sys.stdout, indent=2)
    sys.stdout.write('\n')
