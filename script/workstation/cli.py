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
        parser.add_argument('command', choices=['plan', 'preflight', 'install', 'verify', 'migrate'])
        parser.add_argument('--config', required=True)
        parser.add_argument('--format', choices=['text', 'json'], default='text')
        parser.add_argument('--to', help='destination host for migrate')
        parser.add_argument('--secrets', action='store_true',
                            help='migrate credential paths instead of ordinary data')
        parser.add_argument('--dry-run', action='store_true',
                            help='preview the copy without writing to the destination')
        parser.add_argument('--manifest-groups',
                            help='comma-separated manifest groups to install')
        parser.add_argument('--rsh', help='transport command rsync should use')
        parser.add_argument('--remote-home', help='operator home path on the destination')
        parser.add_argument('--only-trees',
                            help='comma-separated subset of the declared trees to copy')
        parser.add_argument('--source-home',
                            help='home directory to copy from, when it is not the '
                                 'configured target user home on this machine')
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
        if command == 'migrate':
            if not args.to:
                raise InputError('migrate-requires-destination-host')
            import pwd
            from pathlib import Path as _Path
            from .migrate import MigrateError, migrate as run_migrate
            if args.source_home:
                home = args.source_home
            else:
                try:
                    home = pwd.getpwnam(context['config']['target']['user']).pw_dir
                except KeyError:
                    raise InputError('configured-target-user-not-present-on-this-machine')
            root = _Path(__file__).resolve().parent.parent.parent
            try:
                checks, code = run_migrate(root, home, args.to,
                                           secrets=args.secrets, dry_run=args.dry_run,
                                           rsh=args.rsh, remote_home=args.remote_home,
                                           only_trees=[t for t in (args.only_trees or '').split(',') if t])
            except MigrateError as exc:
                raise InputError(str(exc))
            emit(report(command, {0: 'passed', 1: 'failed'}[code], checks, context), fmt)
            return code

        if context['config']['example_only']:
            raise InputError('example-input-not-operational')
        if command == 'install' and os.geteuid() == 0:
            raise InputError('whole-bootstrap-root-forbidden')
        from .storage import preflight
        checks, code = preflight(context['config'])
        from .user_environment import BEHAVIORS, verify as verify_user_files
        selected_behaviors = BEHAVIORS & set(context['selected'])
        selected_tools = [context.get('user_tools', {})[i] for i in context['selected'] if i in context.get('user_tools', {})]
        if not code and command == 'install':
            from .controller import apply_foundation
            try:
                checks.append(apply_foundation(context['config'], user_tools=[r['id'] for r in selected_tools], user_environment={'selected': context['selected'], 'settings': context.get('user_settings', {})} if selected_behaviors else None, runtimes=context['selected'] if {'node', 'sdkman', 'java', 'maven', 'gradle', 'kotlin', 'mandrel', 'go', 'rust', 'uv', 'python', 'opencode', 'codex', 'cline'} & set(context['selected']) else None,
                                              manifest_groups=[g for g in (args.manifest_groups or '').split(',') if g]))
            except (OSError, subprocess.SubprocessError, tarfile.TarError):
                checks.append({'id': 'controller-foundation', 'status': 'failed', 'reason': 'controller-operation-failed-see-private-log'})
                code = 1
        if not code and command in ('install', 'verify'):
            from .packages import applied_groups, verify_packages
            manifest_groups = [g for g in (args.manifest_groups or '').split(',') if g]
            package_checks = verify_packages(groups=manifest_groups or applied_groups())
            from .artifacts import verify as verify_tools
            from pathlib import Path
            import pwd
            if selected_tools:
                package_checks.extend(verify_tools(selected_tools, Path(pwd.getpwnam(context['config']['target']['user']).pw_dir)))
            if selected_behaviors:
                package_checks.extend(verify_user_files(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected'], context.get('user_settings', {}), context.get('user_tools', {})))
            if 'node' in context['selected']:
                from .node_runtime import verify as verify_node
                package_checks.extend(verify_node(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context.get('user_tools', {}), context['selected']))
            if 'sdkman' in context['selected']:
                from .sdkman_runtime import verify as verify_sdkman
                package_checks.extend(verify_sdkman(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'java' in context['selected']:
                from .java_runtime import verify as verify_java
                package_checks.extend(verify_java(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if {'maven', 'gradle', 'kotlin'} & set(context['selected']):
                from .jvm_tools import verify as verify_jvm_tools
                package_checks.extend(verify_jvm_tools(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'mandrel' in context['selected']:
                from .mandrel_runtime import verify as verify_mandrel
                package_checks.extend(verify_mandrel(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'go' in context['selected']:
                from .go_runtime import verify as verify_go
                package_checks.extend(verify_go(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'rust' in context['selected']:
                from .rust_runtime import verify as verify_rust
                package_checks.extend(verify_rust(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if {'uv', 'python'} & set(context['selected']):
                from .python_user import verify as verify_python
                package_checks.extend(verify_python(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'opencode' in context['selected']:
                from .opencode_runtime import verify as verify_opencode
                package_checks.extend(verify_opencode(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'codex' in context['selected']:
                from .codex_runtime import verify as verify_codex
                package_checks.extend(verify_codex(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            if 'cline' in context['selected']:
                from .cline_runtime import verify as verify_cline
                package_checks.extend(verify_cline(Path(pwd.getpwnam(context['config']['target']['user']).pw_dir), context['selected']))
            from .delivery import verify as verify_delivery
            groups_now = manifest_groups or applied_groups()
            package_checks.extend(verify_delivery(groups=groups_now))
            if groups_now is None or 'ai' in groups_now:
                from .npm_cli import verify as verify_npm_cli
                import json as _json
                agents = _json.loads((Path(__file__).resolve().parents[2]
                                      / 'manifest/runtimes.json').read_text())['agents']
                home_path = Path(pwd.getpwnam(context['config']['target']['user']).pw_dir)
                for agent in agents:
                    if agent.get('delivery') == 'npm-pinned':
                        package_checks.extend(verify_npm_cli(home_path, agent['lock_id']))
            if groups_now is None or {'dev', 'kubernetes'} & set(groups_now):
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
            missing = [i for i in context['selected'] if i not in context.get('approved', {}) and i not in context.get('user_tools', {}) and i not in selected_behaviors and i not in {'node', 'sdkman', 'java', 'maven', 'gradle', 'kotlin', 'mandrel', 'go', 'rust', 'uv', 'python', 'opencode', 'codex', 'cline'} and i not in blocked and not covers(routes, i)]
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
