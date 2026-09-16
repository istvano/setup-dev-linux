"""GNOME settings delivery.

Settings are applied with `dconf load`, which works whether or not a session bus
is running: with one it goes through dconf-service, without one dconf writes the
user database directly. Either way the values take effect at the next login.

Applying is not the same as having applied. Every declared key is read back and
compared, so a keyfile that dconf accepted but did not store is reported as a
failure rather than as success.
"""
import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path

from .config import ROOT

MANIFEST = 'manifest/desktop.json'
# dconf prints a value's type prefix only when the type is not obvious from the
# literal. The dumped manifest values omit it, so strip it before comparing.
TYPE_PREFIXES = ('@ms ', '@as ', '@a{ss} ', '@ai ', '@ad ', '@b ', '@i ', '@s ')


class DesktopError(Exception):
    """Raised when settings cannot be applied or do not read back."""


def load_manifest(root=None):
    return json.loads((Path(root or ROOT) / MANIFEST).read_text())


def render_keyfile(settings):
    """Render declared settings as a dconf keyfile.

    Written directly rather than through a template: dconf values are arbitrary
    GVariant text and a value containing template syntax would otherwise be
    rewritten on its way to the file.
    """
    blocks = []
    for section in sorted(settings):
        lines = [f'[{section}]']
        lines += [f'{key}={settings[section][key]}' for key in sorted(settings[section])]
        blocks.append('\n'.join(lines))
    return '\n\n'.join(blocks) + '\n'


def normalise(value):
    value = (value or '').strip()
    for prefix in TYPE_PREFIXES:
        if value.startswith(prefix):
            return value[len(prefix):].strip()
    return value


def declared_keys(settings):
    for section in sorted(settings):
        for key in sorted(settings[section]):
            yield f'/{section}/{key}', settings[section][key]


def read_key(path):
    result = subprocess.run(['dconf', 'read', path], capture_output=True,
                            text=True, check=False, timeout=30)
    if result.returncode != 0:
        raise DesktopError('dconf-read-failed')
    return result.stdout.strip()


def apply(root=None, manifest=None):
    """Load the declared settings. Returns True when anything changed."""
    if shutil.which('dconf') is None:
        raise DesktopError('dconf-not-installed')
    manifest = manifest or load_manifest(root)
    settings = manifest['settings']
    if not settings:
        return False

    before = {}
    for path, _ in declared_keys(settings):
        try:
            before[path] = normalise(read_key(path))
        except DesktopError:
            before[path] = None

    keyfile = render_keyfile(settings)
    handle = tempfile.NamedTemporaryFile('w', suffix='.dconf', delete=False)
    try:
        os.chmod(handle.name, 0o600)
        handle.write(keyfile)
        handle.close()
        with open(handle.name) as stream:
            result = subprocess.run(['dconf', 'load', '/'], stdin=stream,
                                    capture_output=True, text=True,
                                    check=False, timeout=120)
        if result.returncode != 0:
            raise DesktopError('dconf-load-rejected-the-declared-settings')
    finally:
        os.unlink(handle.name)

    mismatched = []
    changed = False
    for path, expected in declared_keys(settings):
        observed = normalise(read_key(path))
        if observed != normalise(expected):
            mismatched.append(path)
        elif before.get(path) != observed:
            changed = True
    if mismatched:
        raise DesktopError(f'{len(mismatched)}-keys-did-not-read-back')
    return changed


def verify(root=None, manifest=None):
    """Report whether the live database matches what the manifest declares."""
    try:
        manifest = manifest or load_manifest(root)
    except (OSError, ValueError):
        return [{'id': 'desktop-settings', 'status': 'failed',
                 'reason': 'desktop-manifest-unreadable'}]
    settings = manifest['settings']
    if shutil.which('dconf') is None:
        return [{'id': 'desktop-settings', 'status': 'deferred',
                 'reason': 'dconf-not-installed'}]

    mismatched, unreadable, total = [], 0, 0
    for path, expected in declared_keys(settings):
        total += 1
        try:
            observed = normalise(read_key(path))
        except DesktopError:
            unreadable += 1
            continue
        if observed != normalise(expected):
            mismatched.append(path)

    checks = []
    if unreadable:
        checks.append({'id': 'desktop-settings', 'status': 'failed',
                       'reason': f'{unreadable}-of-{total}-keys-unreadable'})
    elif mismatched:
        checks.append({'id': 'desktop-settings', 'status': 'failed',
                       'reason': f'{len(mismatched)}-of-{total}-keys-differ'})
    else:
        checks.append({'id': 'desktop-settings', 'status': 'passed',
                       'reason': f'{total}-declared-keys-match'})

    # Only the enabled set belongs in enabled-extensions. An extension that is
    # installed but switched off is a choice, not a missing setting.
    expected = set(manifest.get('extensions_enabled', []))
    if expected:
        enabled = normalise(settings.get('org/gnome/shell', {}).get('enabled-extensions', ''))
        missing = sorted(e for e in expected if e not in enabled)
        wrongly_enabled = sorted(e for e in manifest.get('extensions_disabled', [])
                                 if e in enabled)
        if missing or wrongly_enabled:
            checks.append({'id': 'desktop-extensions', 'status': 'failed',
                           'reason': f'{len(missing)}-not-enabled-'
                                     f'{len(wrongly_enabled)}-enabled-but-should-not-be'})
        else:
            checks.append({'id': 'desktop-extensions', 'status': 'passed',
                           'reason': f'{len(expected)}-extensions-enabled-'
                                     f'{len(manifest.get("extensions_disabled", []))}-left-off'})
    return checks
