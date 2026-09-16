#!/usr/bin/python3 -B
"""Prove the ordinary migration carried no credential material into the guest.

Two weaker checks were tried first and both were wrong. Testing that a path is
absent fails because the guest creates ~/.ssh and ~/.gnupg itself. Matching by
file name fails for the same reason: the guest has its own authorized_keys and
pubring.kbx. Scanning every file for key material fails because installed
toolchains legitimately ship test keys — Go's crypto/tls testdata, for one.

So the question asked here is the exact one that matters: did any file whose
*contents* match a credential file on the source machine arrive in the guest?
Content hashes are immune to name collisions and to innocent lookalikes.
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--home', default='/home/ws-test')
parser.add_argument('--digests-stdin', action='store_true',
                    help='read "<sha256>  <name>" lines describing source credential files')
args = parser.parse_args()

marker = Path('/etc/linux-os-setup-test-vm')
if not marker.is_file() or marker.read_text().strip() != args.expected_vm_id:
    raise SystemExit('Refusing non-test guest')

home = Path(args.home)

# Installed toolchains ship their own test keys and sample material. They are
# delivered by the installer, not by the migration, so they are not evidence.
INSTALLED = ('.local/share/linux-os-setup/', '.nvm/', '.sdkman/', '.cargo/',
             '.rustup/', '.local/share/claude/', '.codex/', '.oh-my-zsh/')
SECRET_CONTENT = re.compile(
    rb'-----BEGIN (RSA |OPENSSH |EC |DSA |PGP )?PRIVATE KEY( BLOCK)?-----')
MAX_HASH_BYTES = 8 * 1024 * 1024

source = {}
if args.digests_stdin:
    for line in sys.stdin.read().splitlines():
        digest, _, name = line.strip().partition('  ')
        if len(digest) == 64 and name:
            source[digest] = name
    # An empty file's digest matches every empty file anywhere.
    source.pop(hashlib.sha256(b'').hexdigest(), None)

failures = []
matched, keys_outside_installed, scanned = [], [], 0

for path in home.rglob('*'):
    if not path.is_file() or path.is_symlink():
        continue
    relative = str(path.relative_to(home))
    if relative.startswith(INSTALLED) or relative.startswith('.workstation/'):
        continue
    try:
        size = path.stat().st_size
        if size == 0 or size > MAX_HASH_BYTES:
            continue
        data = path.read_bytes()
    except OSError:
        continue
    scanned += 1
    digest = hashlib.sha256(data).hexdigest()
    if digest in source:
        matched.append(f'{relative} (source {source[digest]})')
    if SECRET_CONTENT.search(data[:4096]):
        keys_outside_installed.append(relative)

if matched:
    failures.append(f'{len(matched)} files match credential files on the source: '
                    + ', '.join(sorted(matched)[:10]))
if keys_outside_installed:
    failures.append(f'{len(keys_outside_installed)} files contain private key material: '
                    + ', '.join(sorted(keys_outside_installed)[:10]))

if failures:
    for failure in failures:
        print('FAIL: ' + failure)
    raise SystemExit(f'{len(failures)} credential leak checks failed')
print(f'PASS: no credential material reached the guest through the ordinary migration '
      f'({scanned} files scanned against {len(source)} source credential digests)')
