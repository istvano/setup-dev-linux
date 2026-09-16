#!/usr/bin/python3 -B
"""Read private proxy JSON for the shell; never evaluate code or print error values."""
import json
import os
from pathlib import Path
import stat
import sys
from urllib.parse import urlsplit

KEYS = ('http_proxy', 'https_proxy', 'all_proxy', 'no_proxy')


def read_settings(path):
    with os.fdopen(os.open(path, os.O_RDONLY | os.O_NOFOLLOW), 'rb') as stream:
        info = os.fstat(stream.fileno())
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.geteuid() or info.st_mode & 0o077:
            raise ValueError('private settings required')
        raw = stream.read(65537)
    if len(raw) > 65536:
        raise ValueError('oversized settings')
    def unique(pairs):
        result = {}
        for key, value in pairs:
            if key in result:
                raise ValueError('duplicate setting')
            result[key] = value
        return result
    settings = json.loads(raw, object_pairs_hook=unique)
    if not isinstance(settings, dict) or set(settings) != set(KEYS):
        raise ValueError('invalid settings')
    for key, value in settings.items():
        if not isinstance(value, str) or any(ord(c) < 32 or ord(c) == 127 for c in value):
            raise ValueError('invalid proxy value')
        if key != 'no_proxy' and value:
            url = urlsplit(value)
            url.port  # Validate an explicitly supplied port without connecting.
            if url.scheme not in ('http', 'https', 'socks5', 'socks5h') or not url.hostname:
                raise ValueError('invalid proxy URL')
    return settings


if __name__ == '__main__':
    try:
        settings = read_settings(sys.argv[1])
        values = [settings[key] for key in KEYS]
        sys.stdout.buffer.write(('\0'.join(values + ['OK'])).encode())
    except (OSError, ValueError, IndexError, UnicodeError):
        print('Proxy settings unavailable or invalid; require an owned private JSON file.', file=sys.stderr)
        raise SystemExit(1)
