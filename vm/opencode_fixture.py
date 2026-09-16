"""Unauthenticated OpenCode CLI acceptance in disposable private XDG state."""
from pathlib import Path
import os
import subprocess


def check(fixture):
    root = fixture / 'opencode-cli'
    root.mkdir()
    environment = {key: value for key, value in os.environ.items()
                   if not key.startswith(('OPENCODE_', 'XDG_CONFIG_HOME',
                                          'XDG_CACHE_HOME', 'XDG_DATA_HOME',
                                          'XDG_STATE_HOME'))}
    environment.update({
        'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_CACHE_HOME': str(root / 'cache'),
        'XDG_DATA_HOME': str(root / 'data'),
        'XDG_STATE_HOME': str(root / 'state'),
    })
    command = r'''
set -e
[[ "$OPENCODE_DISABLE_AUTOUPDATE" == 1 ]]
[[ "$(opencode --version)" == 1.18.31 ]]
opencode --help > "$1/help.txt" 2>&1
grep -F 'opencode run' "$1/help.txt"
nvm use --silent default
[[ "$(opencode --version)" == 1.18.31 ]]
nvm deactivate
[[ "$(opencode --version)" == 1.18.31 ]]
'''
    result = subprocess.run(['zsh', '-i', '-c', command, '--', str(root)],
                            env=environment, capture_output=True, text=True, timeout=180)
    if result.returncode:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise AssertionError('OpenCode version/help fixture failed')
    assert 'opencode run' in (root / 'help.txt').read_text()
    print('PASS: OpenCode 1.18.31 unauthenticated version/help and stable NVM-switch path')
