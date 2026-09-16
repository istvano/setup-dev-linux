#!/usr/bin/python3 -B
"""Prepare a GNOME session only in the dedicated disposable test guest."""
import argparse
import configparser
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.config import load_context
from workstation.storage import preflight

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--config', required=True)
parser.add_argument('--install', action='store_true', help='provision Ubuntu desktop packages from the guest OS repositories')
args = parser.parse_args()
if os.geteuid() != 0 or Path('/etc/linux-os-setup-test-vm').read_text().strip() != args.expected_vm_id:
    raise SystemExit('Refusing non-test target or unprivileged fixture setup')
context = load_context(args.config)
if context['config']['example_only'] or preflight(context['config'])[1] != 0:
    raise SystemExit('Guest storage preflight failed')
if args.install:
    env = dict(os.environ, DEBIAN_FRONTEND='noninteractive')
    subprocess.run(['apt-get', 'update'], env=env, check=True)
    subprocess.run(['apt-get', 'install', '-y', 'ubuntu-desktop-minimal'], env=env, check=True)
path = Path('/etc/gdm3/custom.conf')
if not path.exists():
    raise SystemExit('GNOME display manager missing; provision the desktop fixture first')
backup = path.with_name('custom.conf.linux-setup-test-backup')
if not backup.exists():
    shutil.copyfile(path, backup)
    backup.chmod(0o600)
config = configparser.ConfigParser()
config.optionxform = str
config.read(path)
if not config.has_section('daemon'):
    config.add_section('daemon')
config['daemon']['AutomaticLoginEnable'] = 'true'
config['daemon']['AutomaticLogin'] = context['config']['target']['user']
with path.open('w') as output:
    config.write(output)
subprocess.run(['systemctl', 'set-default', 'graphical.target'], check=True)
subprocess.run(['systemctl', 'restart', 'gdm3'], check=True)
print('Configured automatic GNOME login for the disposable fixture user only')
