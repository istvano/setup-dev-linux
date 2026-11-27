"""Editor extensions for the host VS Code.

Extensions are installed by `code` itself, because the Marketplace publishes no
artifact this repository could pin and place. That is a weaker guarantee than
the pinned binaries get, and it is recorded rather than hidden: extensions
install at their current version from the Marketplace.

kubectl plugins (krew) are command-line tools and belong to setup-dev-linux-wsl.
"""
import shutil
import subprocess
from pathlib import Path

from .config import ROOT, load_json

# VS Code is installed by the dev-gui group. Installing extensions without it is
# not a skip to pass over quietly: it is a request that cannot be honoured.
OWNER = 'dev-gui'


class PluginError(Exception):
    """Raised when VS Code is missing or refuses an extension."""


def manifest(root=ROOT):
    value, _ = load_json(Path(root) / 'manifest/plugins.json')
    return value


def run(command, timeout=300):
    try:
        return subprocess.run(command, capture_output=True, text=True, check=False,
                              timeout=timeout)
    except (OSError, subprocess.SubprocessError) as exc:
        raise PluginError(f'{command[0]}-failed-to-run') from exc


def installed_extensions(home=None):
    if shutil.which('code') is None:
        raise PluginError('code-not-installed')
    result = run(['code', '--list-extensions'])
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
        result = run(['code', '--install-extension', extension, '--force'], timeout=600)
        if result.returncode != 0:
            raise PluginError(f'extension-refused:{extension}')
        changed = True
    return changed


def capability_ids(root=ROOT):
    """The catalogue ids (`extension-<id>`) of the declared extensions.

    verify() checks each of these, so the report does not also list them as
    capabilities nothing delivers (D035).
    """
    return {'extension-' + e.lower() for e in manifest(root)['vscode_extensions']}


def selected(groups):
    return groups is None or OWNER in groups


def install(home, root=ROOT, groups=None):
    return install_extensions(home, root) if selected(groups) else False


def verify(home, root=ROOT, groups=None):
    """Report which declared extensions are absent. Never repairs."""
    extensions = manifest(root)['vscode_extensions'] if selected(groups) else []
    if not extensions:
        return []
    try:
        present = installed_extensions(home)
    except PluginError as exc:
        return [{'id': 'vscode-extensions', 'status': 'deferred', 'reason': str(exc)}]
    missing = sorted(e for e in extensions if e.lower() not in present)
    checks = [{'id': f'extension:{name}', 'status': 'failed', 'reason': 'not-installed'}
              for name in missing]
    checks.append({'id': 'vscode-extensions',
                   'status': 'failed' if missing else 'passed',
                   'reason': f'{len(extensions) - len(missing)}-of-{len(extensions)}'
                             '-extensions-installed'})
    return checks
