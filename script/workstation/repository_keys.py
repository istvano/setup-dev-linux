"""Normalise and verify third-party APT signing keys.

APT decides how to read a keyring from its file extension, so a binary key
saved with an .asc name is ignored and its repository is then treated as
unsigned — a silent downgrade rather than an error. Every key is therefore
converted to binary form under a .gpg name, and checked against the fingerprint
the manifest records before it is trusted.
"""
import re
import subprocess
from pathlib import Path

ARMOUR_HEADER = b'-----BEGIN PGP'
FINGERPRINT = re.compile(r'^[0-9A-F]{40}$')


class KeyError_(Exception):
    """Raised when key material is unusable or is not the recorded key."""


def is_armoured(data):
    return data.lstrip()[:len(ARMOUR_HEADER)] == ARMOUR_HEADER


def to_binary(data):
    """Return binary keyring bytes for armoured or already-binary input."""
    if not is_armoured(data):
        return data
    result = subprocess.run(['gpg', '--batch', '--yes', '--dearmor'],
                            input=data, capture_output=True, check=False)
    if result.returncode != 0 or not result.stdout:
        raise KeyError_('key-material-not-valid-openpgp')
    return result.stdout


def fingerprint(data):
    """Primary key fingerprint of binary keyring bytes."""
    result = subprocess.run(
        ['gpg', '--show-keys', '--with-colons', '--with-fingerprint', '-'],
        input=data, capture_output=True, check=False)
    if result.returncode != 0:
        raise KeyError_('key-material-not-readable')
    for line in result.stdout.decode('utf-8', 'replace').splitlines():
        if line.startswith('fpr:'):
            value = line.split(':')[9]
            if FINGERPRINT.match(value):
                return value
    raise KeyError_('key-material-has-no-fingerprint')


def install_key(source, destination, expected):
    """Place a verified binary keyring. Returns True when the file changed."""
    data = to_binary(Path(source).read_bytes())
    observed = fingerprint(data)
    if expected:
        if not FINGERPRINT.match(expected):
            raise KeyError_('recorded-fingerprint-malformed')
        if observed != expected:
            raise KeyError_('key-fingerprint-mismatch')
    destination = Path(destination)
    if destination.is_symlink():
        raise KeyError_('unsafe-keyring-path')
    if destination.is_file() and destination.read_bytes() == data:
        return False
    destination.write_bytes(data)
    destination.chmod(0o644)
    return True
