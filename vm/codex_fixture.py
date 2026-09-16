"""Unauthenticated Codex CLI acceptance with disposable private state."""
from pathlib import Path
import os
import subprocess


def check(fixture):
    root = fixture / 'codex-cli'
    root.mkdir()
    (root / 'codex-home').mkdir()
    environment = {key: value for key, value in os.environ.items()
                   if key != 'CODEX_HOME' and not key.startswith('XDG_')}
    environment.update({
        'CODEX_HOME': str(root / 'codex-home'),
        'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_CACHE_HOME': str(root / 'cache'),
        'XDG_DATA_HOME': str(root / 'data'),
        'XDG_STATE_HOME': str(root / 'state'),
    })
    command = r'''
set -e
[[ "$(codex --version)" == 'codex-cli 0.154.0' ]]
codex --help > "$1/help.txt" 2>&1
grep -E '^  exec[[:space:]]+Run Codex non-interactively' "$1/help.txt"
nvm use --silent default
[[ "$(codex --version)" == 'codex-cli 0.154.0' ]]
nvm deactivate
sdk use java 21.0.12.1.1-ws-ms
[[ "$(codex --version)" == 'codex-cli 0.154.0' ]]
sdk use java 25.0.4.1.1-ws-tem
[[ "$(codex --version)" == 'codex-cli 0.154.0' ]]
'''
    result = subprocess.run(['zsh', '-i', '-c', command, '--', str(root)],
                            env=environment, capture_output=True, text=True, timeout=180)
    if result.returncode:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise AssertionError('Codex version/help fixture failed')
    assert 'Run Codex non-interactively' in (root / 'help.txt').read_text()
    print('PASS: Codex 0.154.0 unauthenticated version/help and stable Node/Java-switch path')
