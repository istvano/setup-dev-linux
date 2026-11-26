"""Public commands: no implicit config, consistent outcomes, no secret-bearing errors."""
import argparse
import json
import os
import subprocess
import sys
import tarfile
from .config import InputError, load_context


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError('invalid-command-line')


def report(command, status, checks, context=None):
    return {'report_version': 1, 'command': command, 'outcome': status,
            'provenance': context['provenance'] if context else None,
            'workstation_ready': False, 'checks': checks}


def emit(result, fmt):
    if fmt == 'json':
        print(json.dumps(result, sort_keys=True))
    else:
        print(result['command'] + ': ' + result['outcome'])
        for check in result['checks']:
            print(check['id'] + ': ' + check['status'] + ' — ' + check['reason'])
        print('This result does not establish full workstation readiness.')


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fmt = 'json' if '--format=json' in argv or any(argv[i:i+2] == ['--format', 'json'] for i in range(len(argv))) else 'text'
    command = 'input'
    context = None
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('command', choices=['plan', 'preflight', 'install', 'verify'])
        parser.add_argument('--config', required=True)
        parser.add_argument('--format', choices=['text', 'json'], default='text')
        parser.add_argument('--manifest-groups',
                            help='comma-separated manifest groups to install')
        args = parser.parse_args(argv)
        command, fmt = args.command, args.format
        context = load_context(args.config)
        if command == 'plan':
            checks = [{'id': 'input', 'status': 'passed', 'reason': 'example-preview-only' if context['config']['example_only'] else 'configuration-valid'}]
            for i in context['selected']:
                e = context['entries'][i]
                state = 'blocked-source' if e['delivery']['status'] == 'unverified' else 'planned'
                checks.append({'id': i, 'status': state, 'reason': e['owner'] + ':' + (e['delivery']['channel'] or e['boundary'])})
            checks.append({'id': 'apply', 'status': 'unimplemented', 'reason': 'installation-roles-not-yet-implemented'})
            emit(report(command, 'passed', checks, context), fmt)
            return 0
        if context['config']['example_only']:
            raise InputError('example-input-not-operational')
        if command == 'install' and os.geteuid() == 0:
            raise InputError('whole-bootstrap-root-forbidden')
        from .storage import preflight
        checks, code = preflight(context['config'])
        manifest_groups = [g for g in (args.manifest_groups or '').split(',') if g]
        if not code and command == 'install':
            from .controller import apply_foundation
            try:
                checks.append(apply_foundation(context['config'], manifest_groups=manifest_groups))
            except (OSError, subprocess.SubprocessError, tarfile.TarError):
                checks.append({'id': 'controller-foundation', 'status': 'failed', 'reason': 'controller-operation-failed-see-private-log'})
                code = 1
        if not code and command in ('install', 'verify'):
            from .packages import applied_groups, verify_packages
            from pathlib import Path
            import pwd
            package_checks = verify_packages(groups=manifest_groups or applied_groups())
            from .delivery import verify as verify_delivery
            from .system import verify as verify_system
            groups_now = manifest_groups or applied_groups()
            package_checks.extend(verify_system(context['config']['target']['user'],
                                                groups=groups_now))
            package_checks.extend(verify_delivery(groups=groups_now))
            if groups_now is None or 'dev-gui' in groups_now:
                from .plugins import verify as verify_plugins
                package_checks.extend(verify_plugins(
                    Path(pwd.getpwnam(context['config']['target']['user']).pw_dir),
                    groups=groups_now))
            if 'desktop' in (manifest_groups or applied_groups() or ['desktop']):
                from .desktop import verify as verify_desktop
                package_checks.extend(verify_desktop())
            checks.extend(package_checks)
            # The manifest is the delivery authority: what it installs is approved
            # by its own pinning and signing rules, checked by script/check-manifest.
            # The catalogue gate still applies to everything it does not deliver.
            from .manifest import covers, delivered, load as load_manifest
            try:
                routes = delivered(load_manifest())
            except (OSError, ValueError, KeyError):
                routes = {}
            blocked = [i for i in context['selected']
                       if context['entries'][i]['delivery']['status'] == 'unverified'
                       and not covers(routes, i)]
            # Nothing attempts to install these: they are selected but no role
            # delivers them yet. "deferred" says that honestly and still keeps the
            # overall outcome at incomplete, which is not a pass.
            checks.extend({'id': i, 'status': 'deferred', 'reason': 'delivery-not-implemented'}
                          for i in blocked)
            missing = [i for i in context['selected'] if i not in context.get('approved', {}) and i not in blocked and not covers(routes, i)]
            checks.extend({'id': i, 'status': 'deferred', 'reason': 'capability-role-verification-not-yet-implemented'} for i in missing)
            code = 1 if any(c['status'] == 'failed' for c in package_checks) else (3 if blocked or missing or any(c['status'] == 'deferred' for c in package_checks) or not context['selected'] else 0)
        outcome = {0: 'passed', 1: 'failed', 2: 'invalid', 3: 'incomplete'}[code]
        emit(report(command, outcome, checks, context), fmt)
        return code
    except InputError as exc:
        emit(report(command, 'invalid', [{'id': 'input', 'status': 'failed', 'reason': str(exc)}], context), fmt)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        emit(report(command, 'failed', [{'id': 'runtime', 'status': 'failed', 'reason': 'inspection-or-runtime-error'}], context), fmt)
        return 1
