"""Public commands: no implicit config, consistent outcomes, no secret-bearing errors."""
import argparse
import json
import os
import subprocess
import sys
import tarfile
from .config import InputError, load_context, require


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise InputError('invalid-command-line')


def report(command, status, checks, context=None, selection=None):
    result = {'report_version': 1, 'command': command, 'outcome': status,
              'provenance': context['provenance'] if context else None,
              'workstation_ready': False, 'checks': checks}
    if selection:
        result['profiles'] = selection
    return result


def emit(result, fmt):
    if fmt == 'json':
        print(json.dumps(result, sort_keys=True))
    else:
        if result.get('profiles'):
            # The line is setup-dev-win's wording; the source says whether it
            # came from --profiles, the recorded choice or the default.
            print(result['profiles']['line'])
            print('Profiles source: ' + result['profiles']['source'])
        print(result['command'] + ': ' + result['outcome'])
        for check in result['checks']:
            print(check['id'] + ': ' + check['status'] + ' — ' + check['reason'])
        print('This result does not establish full workstation readiness.')


def stage_checks(selection):
    """What apply would run for this selection, stage by stage."""
    from .controller import host_stages
    checks = []
    for stage, playbooks, _ in host_stages(selection):
        if stage == 'record-selection':
            continue
        checks.append({'id': 'stage:' + stage, 'status': 'planned',
                       'reason': ','.join(playbooks)})
    return checks


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    fmt = 'json' if '--format=json' in argv or any(argv[i:i+2] == ['--format', 'json'] for i in range(len(argv))) else 'text'
    command = 'input'
    context = None
    summary = None
    try:
        parser = Parser(description=__doc__)
        parser.add_argument('command', choices=['plan', 'preflight', 'apply', 'install', 'verify'])
        parser.add_argument('--config', required=True)
        parser.add_argument('--format', choices=['text', 'json'], default='text')
        parser.add_argument('--profiles',
                            help='comma-separated host profiles (default: the choice '
                                 'recorded in ~/.local/state/setup-dev-linux/state.json, '
                                 'else profiles/host.json "default")')
        parser.add_argument('--manifest-groups', help='former name of --profiles')
        ssh = parser.add_mutually_exclusive_group()
        ssh.add_argument('--allow-ssh', dest='allow_ssh', action='store_const', const=True,
                         default=None,
                         help='firewall profile: allow incoming SSH (UFW OpenSSH); recorded '
                              'in per-user state and kept on later runs')
        ssh.add_argument('--no-allow-ssh', dest='allow_ssh', action='store_const', const=False,
                         help='firewall profile: do not allow incoming SSH; removes the '
                              'rule and records the choice')
        args = parser.parse_args(argv)
        command, fmt = args.command, args.format
        if command == 'install':
            print('install is now apply; running apply', file=sys.stderr)
            command = 'apply'
        if args.manifest_groups is not None:
            require(args.profiles is None, 'use-profiles-or-manifest-groups-not-both')
            print('--manifest-groups is now --profiles', file=sys.stderr)
            args.profiles = args.manifest_groups
        from . import profiles
        catalogue = profiles.load()
        chosen, source = profiles.select(args.profiles, catalogue)
        selection = profiles.resolve(chosen, catalogue)
        summary = profiles.summary(chosen, source, catalogue)
        context = load_context(args.config)
        # Resolved before anything changes: an unreadable record stops the run
        # rather than defaulting to "no SSH" on a machine reached over SSH.
        allow_ssh, ssh_source = False, 'default'
        if 'firewall' in selection['stages'] and command in ('apply', 'verify'):
            from . import firewall
            allow_ssh, ssh_source = firewall.resolve_allow_ssh(args.allow_ssh)

        from .manifest import delivering_groups, load as load_manifest
        owners = delivering_groups(load_manifest())

        def scoped(ids):
            """Selected capabilities that belong to the chosen profiles."""
            return [i for i in ids
                    if profiles.in_scope(i, context['entries'][i], selection, catalogue, owners)]

        if command == 'plan':
            checks = [{'id': 'input', 'status': 'passed', 'reason': 'example-preview-only' if context['config']['example_only'] else 'configuration-valid'}]
            for i in scoped(context['selected']):
                e = context['entries'][i]
                state = 'blocked-source' if e['delivery']['status'] == 'unverified' else 'planned'
                checks.append({'id': i, 'status': state, 'reason': e['owner'] + ':' + (e['delivery']['channel'] or e['boundary'])})
            checks.extend(stage_checks(selection))
            emit(report(command, 'passed', checks, context, summary), fmt)
            return 0
        if context['config']['example_only']:
            raise InputError('example-input-not-operational')
        if command == 'apply' and os.geteuid() == 0:
            raise InputError('whole-bootstrap-root-forbidden')
        from .storage import preflight
        from . import host
        checks, code = preflight(context['config'])
        prerequisite_checks, prerequisite_code = host.check_prerequisites()
        checks.extend(prerequisite_checks)
        code = code or prerequisite_code
        groups = selection['groups']
        if not code and command == 'apply':
            from .controller import apply_foundation
            try:
                checks.append(apply_foundation(
                    context['config'], selection=selection, allow_ssh=allow_ssh,
                    allow_ssh_explicit=args.allow_ssh is not None))
            except (OSError, subprocess.SubprocessError, tarfile.TarError):
                checks.append({'id': 'controller-foundation', 'status': 'failed', 'reason': 'controller-operation-failed-see-private-log'})
                code = 1
        if not code and command in ('apply', 'verify'):
            from .packages import verify_packages
            from pathlib import Path
            import pwd
            package_checks = verify_packages(groups=groups)
            from .delivery import verify as verify_delivery
            from .system import verify as verify_system
            package_checks.extend(verify_system(context['config']['target']['user'],
                                                groups=groups))
            package_checks.extend(verify_delivery(groups=groups,
                                                  repositories=selection['repositories']))
            # A headless selection demands no VS Code and no GNOME settings.
            if 'dev-gui' in chosen:
                from .plugins import verify as verify_plugins
                package_checks.extend(verify_plugins(
                    Path(pwd.getpwnam(context['config']['target']['user']).pw_dir),
                    groups=groups))
            if 'desktop' in chosen:
                from .desktop import verify as verify_desktop
                package_checks.extend(verify_desktop())
            if 'firewall' in selection['stages']:
                package_checks.append({'id': 'firewall:ssh-choice', 'status': 'passed',
                                       'reason': f'allow-ssh-{str(allow_ssh).lower()}-{ssh_source}'})
                package_checks.extend(firewall.verify(allow_ssh, desktop=selection['desktop']))
            checks.extend(package_checks)
            # The manifest is the delivery authority: what it installs is approved
            # by its own pinning and signing rules, checked by script/check-manifest.
            # The catalogue gate still applies to everything it does not deliver.
            from .manifest import covers, delivered, load as load_manifest
            try:
                routes = delivered(load_manifest())
            except (OSError, ValueError, KeyError):
                routes = {}
            selected = scoped(context['selected'])
            blocked = [i for i in selected
                       if context['entries'][i]['delivery']['status'] == 'unverified'
                       and not covers(routes, i)]
            # Nothing attempts to install these: they are selected but no role
            # delivers them yet. "deferred" says that honestly and still keeps the
            # overall outcome at incomplete, which is not a pass.
            checks.extend({'id': i, 'status': 'deferred', 'reason': 'delivery-not-implemented'}
                          for i in blocked)
            missing = [i for i in selected if i not in context.get('approved', {}) and i not in blocked and not covers(routes, i)]
            checks.extend({'id': i, 'status': 'deferred', 'reason': 'capability-role-verification-not-yet-implemented'} for i in missing)
            code = 1 if any(c['status'] == 'failed' for c in package_checks) else (3 if blocked or missing or any(c['status'] == 'deferred' for c in package_checks) or not context['selected'] else 0)
        outcome = {0: 'passed', 1: 'failed', 2: 'invalid', 3: 'incomplete'}[code]
        emit(report(command, outcome, checks, context, summary), fmt)
        return code
    except InputError as exc:
        emit(report(command, 'invalid', [{'id': 'input', 'status': 'failed', 'reason': str(exc)}], context, summary), fmt)
        return 2
    except (OSError, ValueError, KeyError, TypeError, RecursionError):
        emit(report(command, 'failed', [{'id': 'runtime', 'status': 'failed', 'reason': 'inspection-or-runtime-error'}], context, summary), fmt)
        return 1
