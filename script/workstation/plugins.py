"""Editor extensions and kubectl plugins.

Both are installed by the tool that owns them — `code` for extensions, krew for
kubectl plugins — because neither publishes an artifact this repository could
pin and place itself. That is a weaker guarantee than the pinned binaries get,
and it is recorded rather than hidden: extensions install at their current
version from the Marketplace.

krew needs one step that is easy to miss. kubectl only discovers plugins named
`kubectl-<name>` on PATH, so the `krew` binary in /usr/local/bin is not reachable
as `kubectl krew`. krew has to bootstrap itself into ~/.krew, which is where the
`kubectl-*` shims live.
"""
import json
import os
import shutil
import subprocess
from pathlib import Path

from .config import ROOT, load_json

KREW_ROOT_NAME = '.krew'


class PluginError(Exception):
    """Raised when a plugin tool is missing or refuses to install."""


def manifest(root=ROOT):
    value, _ = load_json(Path(root) / 'manifest/plugins.json')
    return value


def krew_root(home):
    return Path(home) / KREW_ROOT_NAME


def krew_environment(home):
    environment = dict(os.environ)
    root = krew_root(home)
    environment['KREW_ROOT'] = str(root)
    environment['PATH'] = f"{root / 'bin'}:{environment.get('PATH', '')}"
    return environment


def run(command, home, timeout=300):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False,
                              timeout=timeout, env=krew_environment(home))
    except (OSError, subprocess.SubprocessError) as exc:
        raise PluginError(f'{command[0]}-failed-to-run') from exc


def installed_extensions(home):
    if shutil.which('code') is None:
        raise PluginError('code-not-installed')
    result = run(['code', '--list-extensions'], home)
    if result.returncode != 0:
        raise PluginError('code-could-not-list-extensions')
    return {line.strip().lower() for line in result.stdout.splitlines() if line.strip()}


def install_extensions(home, root=ROOT):
    """Install every declared extension. Returns True when anything changed."""
    declared = manifest(root)['vscode_extensions']
    if not declared:
        return False
    present = installed_extensions(home)
    changed = False
    for extension in declared:
        if extension.lower() in present:
            continue
        result = run(['code', '--install-extension', extension, '--force'], home, timeout=600)
        if result.returncode != 0:
            raise PluginError(f'extension-refused:{extension}')
        changed = True
    return changed


def installed_krew_plugins(home):
    shim = krew_root(home) / 'bin/kubectl-krew'
    if not shim.is_file():
        return None
    result = run([str(shim), 'list'], home)
    if result.returncode != 0:
        raise PluginError('krew-could-not-list-plugins')
    # krew prints a bare list of names when stdout is not a terminal and a
    # "PLUGIN VERSION" header when it is. Dropping the first line unconditionally
    # loses the alphabetically first plugin in the non-terminal case.
    names = set()
    for line in result.stdout.splitlines():
        first = line.split()[0] if line.split() else ''
        if not first or first.upper() == 'PLUGIN':
            continue
        names.add(first)
    return names


def bootstrap_krew(home):
    """krew installs itself into KREW_ROOT; only then is `kubectl krew` reachable."""
    shim = krew_root(home) / 'bin/kubectl-krew'
    if shim.is_file():
        return False
    binary = shutil.which('krew')
    if binary is None:
        raise PluginError('krew-not-installed')
    result = run([binary, 'install', 'krew'], home, timeout=600)
    if result.returncode != 0 or not shim.is_file():
        raise PluginError('krew-could-not-bootstrap-itself')
    return True


def install_krew_plugins(home, root=ROOT):
    declared = manifest(root)['krew_plugins']
    if not declared:
        return False
    changed = bootstrap_krew(home)
    shim = krew_root(home) / 'bin/kubectl-krew'
    present = installed_krew_plugins(home) or set()
    for plugin in declared:
        if plugin in present:
            continue
        result = run([str(shim), 'install', plugin], home, timeout=600)
        if result.returncode != 0:
            raise PluginError(f'krew-plugin-refused:{plugin}')
        changed = True
    return changed


# Each half is owned by a tool from a particular manifest group. Installing
# extensions without VS Code, or krew plugins without kubectl, is not a skip to
# pass over quietly — it is a request that cannot be honoured.
OWNERS = {'vscode_extensions': 'dev', 'krew_plugins': 'kubernetes'}


def selected(groups, kind):
    return groups is None or OWNERS[kind] in groups


def install(home, root=ROOT, groups=None):
    changed = False
    if selected(groups, 'vscode_extensions'):
        changed |= install_extensions(home, root)
    if selected(groups, 'krew_plugins'):
        changed |= install_krew_plugins(home, root)
    return changed


def verify(home, root=ROOT, groups=None):
    """Report which declared extensions and plugins are absent. Never repairs."""
    declared = manifest(root)
    checks = []

    extensions = declared['vscode_extensions'] if selected(groups, 'vscode_extensions') else []
    if extensions:
        try:
            present = installed_extensions(home)
        except PluginError as exc:
            checks.append({'id': 'vscode-extensions', 'status': 'deferred', 'reason': str(exc)})
        else:
            missing = sorted(e for e in extensions if e.lower() not in present)
            checks += [{'id': f'extension:{name}', 'status': 'failed', 'reason': 'not-installed'}
                       for name in missing]
            checks.append({'id': 'vscode-extensions',
                           'status': 'failed' if missing else 'passed',
                           'reason': f'{len(extensions) - len(missing)}-of-{len(extensions)}'
                                     '-extensions-installed'})

    plugins = declared['krew_plugins'] if selected(groups, 'krew_plugins') else []
    if plugins:
        try:
            present = installed_krew_plugins(home)
        except PluginError as exc:
            present, reason = None, str(exc)
        else:
            reason = 'krew-not-bootstrapped'
        if present is None:
            checks.append({'id': 'krew-plugins', 'status': 'failed', 'reason': reason})
        else:
            missing = sorted(p for p in plugins if p not in present)
            checks += [{'id': f'krew:{name}', 'status': 'failed', 'reason': 'not-installed'}
                       for name in missing]
            checks.append({'id': 'krew-plugins',
                           'status': 'failed' if missing else 'passed',
                           'reason': f'{len(plugins) - len(missing)}-of-{len(plugins)}'
                                     '-plugins-installed'})
    return checks
