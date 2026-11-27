"""Host programs the installer needs before it can install anything.

gpg checks every third-party signing key against its recorded fingerprint, so
a missing gpg would stop the repositories stage after the controller sync.
git clones setup-dev-linux-wsl for the command-line handoff. Both are looked up
on the system path only, the one a privileged step sees: a copy under the
operator's home does not count.
"""
import shutil

SYSTEM_PATH = '/usr/sbin:/usr/bin:/sbin:/bin'

# Program -> the Ubuntu package that provides it.
PREREQUISITES = {'gpg': 'gnupg', 'git': 'git'}


def check_prerequisites(which=shutil.which):
    """(checks, code): one passed check, or a failed check per missing program."""
    missing = [name for name in PREREQUISITES if which(name, path=SYSTEM_PATH) is None]
    if not missing:
        return [{'id': 'prerequisites', 'status': 'passed',
                 'reason': '-and-'.join(PREREQUISITES) + '-present'}], 0
    return [{'id': f'prerequisite:{name}', 'status': 'failed',
             'reason': f'missing-install-package-{PREREQUISITES[name]}'}
            for name in missing], 1
