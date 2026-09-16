"""Copy operator data to a new workstation over SSH.

This moves files. It never partitions, formats or mounts anything, and it never
deletes on the destination: a tree that exists on the target is updated, not
replaced. Credential-bearing paths are excluded from the ordinary copy and move
only under the explicit secrets command.

Completeness is proved rather than assumed. After copying, the same rsync runs
again in dry-run mode; a byte-complete copy has nothing left to transfer, so any
remaining item is reported as a failure.
"""
import json
import shutil
import subprocess
from pathlib import Path

RSYNC_BASE = ['--archive', '--hard-links', '--acls', '--xattrs', '--partial']


class MigrateError(Exception):
    """Raised for input the operator must correct before copying."""


def load_plan(root, home, only_trees=None):
    """Resolve which declared trees exist. only_trees narrows the copy to a
    subset of the manifest, which the guest rehearsal uses to move a bounded
    amount of real data; it can never widen it beyond what the manifest declares."""
    manifest = json.loads((Path(root) / 'manifest/migrate.json').read_text())
    home = Path(home)
    declared = manifest['trees']
    if only_trees:
        unknown = sorted(set(only_trees) - set(declared))
        if unknown:
            raise MigrateError('tree-not-declared-in-manifest:' + ','.join(unknown))
        declared = [name for name in declared if name in only_trees]
    present, absent = [], []
    for name in declared:
        (present if (home / name).exists() else absent).append(name)
    return {'manifest': manifest, 'present': present, 'absent': absent, 'home': home}


def exclude_arguments(manifest):
    return [f'--exclude={pattern}' for pattern in manifest['exclude_patterns']]


def secret_arguments(manifest):
    """Keep credential paths out of the ordinary copy."""
    excluded = list(manifest['secrets']['trees']) + list(manifest['secrets']['paths'])
    return [f'--exclude={path}' for path in excluded]


def build_command(plan, destination, *, secrets=False, dry_run=False, itemize=False, rsh=None):
    manifest = plan['manifest']
    if secrets:
        sources = [str(plan['home'] / name) for name in manifest['secrets']['trees']
                   if (plan['home'] / name).exists()]
        sources += [str(plan['home'] / path) for path in manifest['secrets']['paths']
                    if (plan['home'] / path).exists()]
        # The destination's own authorized_keys is what grants access to it.
        # Overwriting it revokes the key this copy is running over.
        excludes = [f'--exclude={path}' for path in manifest['secrets'].get('never_copy', [])]
    else:
        sources = [str(plan['home'] / name) for name in plan['present']]
        excludes = exclude_arguments(manifest) + secret_arguments(manifest)
    if not sources:
        raise MigrateError('nothing-to-copy')

    command = ['rsync', *RSYNC_BASE, *excludes]
    if rsh:
        command += ['--rsh', rsh]
    if dry_run:
        command.append('--dry-run')
    command.append('--itemize-changes' if itemize else '--info=stats2')
    command += sources
    command.append(destination)
    return command


def parse_destination(target, home, remote_home=None):
    """Return the rsync destination for a target given as host or user@host.

    The destination path is the operator's home on the target machine, which is
    not always spelled the same as it is here.
    """
    if ':' in target:
        raise MigrateError('destination-must-be-host-not-path')
    if not target or target.startswith('-'):
        raise MigrateError('invalid-destination-host')
    return f'{target}:{remote_home or home}/'


def pending_items(output):
    """Transfers rsync still considers outstanding, from --itemize-changes."""
    pending = []
    for line in output.splitlines():
        if not line or line.startswith(('sending', 'sent ', 'total ', 'cannot ')):
            continue
        # Itemised lines start with the change flags, e.g. ">f+++++++++".
        if len(line) > 11 and line[0] in '<>ch.*' and ' ' in line:
            if not line.startswith('.'):  # "." means no change is needed
                pending.append(line.split(' ', 1)[1])
    return pending


def run(command, capture=False):
    try:
        result = subprocess.run(command, text=True, check=False,
                                capture_output=capture, timeout=None)
    except (OSError, subprocess.SubprocessError) as exc:
        raise MigrateError('rsync-failed-to-start') from exc
    return result


def migrate(root, home, target, *, secrets=False, dry_run=False, rsh=None,
            remote_home=None, only_trees=None):
    """Copy the selected trees and prove the copy landed complete."""
    if shutil.which('rsync') is None:
        raise MigrateError('rsync-not-installed')
    plan = load_plan(root, home, only_trees)
    destination = parse_destination(target, home, remote_home)
    checks = []

    if plan['absent'] and not secrets:
        checks.append({'id': 'migrate-sources', 'status': 'deferred',
                       'reason': 'declared-trees-absent:' + ','.join(sorted(plan['absent']))})

    command = build_command(plan, destination, secrets=secrets, dry_run=dry_run, rsh=rsh)
    result = run(command)
    if result.returncode != 0:
        checks.append({'id': 'migrate-copy', 'status': 'failed',
                       'reason': f'rsync-exit-{result.returncode}'})
        return checks, 1
    if dry_run:
        checks.append({'id': 'migrate-copy', 'status': 'passed', 'reason': 'preview-only-no-writes'})
        return checks, 0
    checks.append({'id': 'migrate-copy', 'status': 'passed',
                   'reason': f"copied-{len(plan['present'])}-trees" if not secrets
                             else 'copied-credential-paths'})

    # Prove completeness: a second pass must find nothing left to send.
    verify = build_command(plan, destination, secrets=secrets, dry_run=True, itemize=True, rsh=rsh)
    confirmation = run(verify, capture=True)
    if confirmation.returncode != 0:
        checks.append({'id': 'migrate-verify', 'status': 'failed',
                       'reason': f'verification-rsync-exit-{confirmation.returncode}'})
        return checks, 1
    outstanding = pending_items(confirmation.stdout or '')
    if outstanding:
        checks.append({'id': 'migrate-verify', 'status': 'failed',
                       'reason': f'{len(outstanding)}-paths-not-transferred'})
        return checks, 1
    checks.append({'id': 'migrate-verify', 'status': 'passed',
                   'reason': 'second-pass-found-nothing-outstanding'})
    return checks, 0
