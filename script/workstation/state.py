"""Per-user installer state, kept outside the clone.

`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json` holds the
operator's choices that must outlive the repository checkout: re-cloning,
`git clean -xfd` or rebuilding the controller in `.workstation/` must not lose
them, because a lost profile choice silently turns a headless re-run into a
desktop install. setup-dev-win and setup-dev-linux-wsl keep theirs outside the
clone the same way.

One object of named keys (`profiles` today), so another stage can add its own
key without a second file. Reading and writing apply the same checks: neither
the directory nor the file may be a symlink, both must belong to the current
user, and the file must not be readable by anyone else. A state file that
exists but fails a check is an error, never an absence.
"""
import json
import os
import stat
import tempfile
from pathlib import Path

from .config import InputError, load_json, require

DIRECTORY = 'setup-dev-linux'
FILE = 'state.json'


def path():
    base = os.environ.get('XDG_STATE_HOME', '')
    # The XDG spec: a relative value is invalid and is ignored.
    if not base or not os.path.isabs(base):
        base = os.path.join(os.environ.get('HOME') or str(Path.home()), '.local', 'state')
    return Path(base) / DIRECTORY / FILE


def _check(target, mode_mask):
    """Not a symlink, owned by us, no permission bits outside the mask."""
    info = os.lstat(target)
    require(not stat.S_ISLNK(info.st_mode), 'state-unsafe; symlink')
    require(info.st_uid == os.geteuid(), 'state-unsafe; owner')
    require(stat.S_IMODE(info.st_mode) & ~mode_mask == 0, 'state-unsafe; permissions')


def _read(file):
    """The whole state object; {} when no state file exists."""
    directory = file.parent
    if not os.path.lexists(directory):
        return {}
    _check(directory, 0o700)
    require(stat.S_ISDIR(os.lstat(directory).st_mode), 'state-unsafe; not-a-directory')
    if not os.path.lexists(file):
        return {}
    _check(file, 0o600)
    try:
        value, _ = load_json(file)
    except InputError:
        raise InputError('state-unreadable') from None
    require(isinstance(value, dict) and value.get('schema_version') == 1, 'state-unreadable')
    return value


def get(key):
    """The value stored under key, or None."""
    return _read(path()).get(key)


def set(key, value):  # noqa: A001 - the module is the namespace: state.set
    """Store value under key, keeping every other key. Atomic replace, 0600."""
    file = path()
    current = _read(file)
    directory = file.parent
    if not os.path.lexists(directory):
        directory.parent.mkdir(parents=True, exist_ok=True)
        directory.mkdir(mode=0o700)
        _check(directory, 0o700)
    current = {**current, 'schema_version': 1, key: value}
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix='.state-', suffix='.json')
    try:
        with os.fdopen(descriptor, 'w') as stream:
            os.fchmod(stream.fileno(), 0o600)
            stream.write(json.dumps(current, indent=2, sort_keys=True) + '\n')
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, file)
    except BaseException:
        if os.path.lexists(temporary):
            os.unlink(temporary)
        raise
