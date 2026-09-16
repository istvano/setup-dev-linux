"""Unauthenticated Cline CLI-only checks with disposable private runtime state."""
import os
from pathlib import Path
import subprocess


def check(fixture):
    root = fixture / 'cline-cli'
    root.mkdir()
    environment = {key: value for key, value in os.environ.items()
                   if key not in ('CLINE_DIR', 'CLINE_DATA_DIR', 'CLINE_BIN_PATH',
                                  'CLINE_WRAPPER_PATH') and not key.startswith('XDG_')}
    environment.update({
        'CLINE_DIR': str(root / 'cline-home'),
        'CLINE_DATA_DIR': str(root / 'cline-data'),
        'CLINE_NO_AUTO_UPDATE': '1',
        'CLINE_DISABLE_CLINE_PASS_NOTICE': '1',
        'CLINE_LOG_ENABLED': '0',
        'XDG_CONFIG_HOME': str(root / 'config'),
        'XDG_CACHE_HOME': str(root / 'cache'),
        'XDG_DATA_HOME': str(root / 'data'),
        'XDG_STATE_HOME': str(root / 'state'),
    })
    command = r'''
set -e
before=$(command -v cline)
[[ "$before" == "$HOME/.local/share/linux-os-setup/tools/cline/3.0.62/bin/cline" ]]
cline --version > "$1/version.txt" 2>&1
cline --help > "$1/help.txt" 2>&1
nvm use --silent default
[[ $(command -v cline) == "$before" ]]
cline --version > "$1/selected-version.txt" 2>&1
nvm deactivate >/dev/null
[[ $(command -v cline) == "$before" ]]
cline --version > "$1/deactivated-version.txt" 2>&1
sdk use java 21.0.12.1.1-ws-ms
cline --version > "$1/java-switch-version.txt" 2>&1
sdk use java 25.0.4.1.1-ws-tem
cline --version > "$1/restored-version.txt" 2>&1
'''
    result = subprocess.run(['zsh', '-i', '-c', command, '--', str(root)],
                            env=environment, capture_output=True, text=True,
                            timeout=240)
    if result.returncode:
        print(result.stdout[-2000:])
        print(result.stderr[-2000:])
        raise AssertionError('Cline version/help and runtime switching failed')
    for name in ['version', 'selected-version', 'deactivated-version',
                 'java-switch-version', 'restored-version']:
        assert '3.0.62' in (root / (name + '.txt')).read_text(), name
    help_text = (root / 'help.txt').read_text()
    assert 'auth' in help_text.lower() and 'cline' in help_text.lower()
    print('PASS: Cline 3.0.62 unauthenticated version/help and fixed path after NVM deactivation and Java switching')
