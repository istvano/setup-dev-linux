#!/usr/bin/python3 -B
"""Synthetic guest test fixture, never a production machine input generator."""
import argparse
import copy
import json
import os
from pathlib import Path
import subprocess
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--controller', action='store_true')
parser.add_argument('--packages', action='store_true')
parser.add_argument('--user-environment', action='store_true')
args = parser.parse_args()
marker = Path('/etc/linux-os-setup-test-vm')
if not marker.is_file() or marker.read_text().strip() != args.expected_vm_id:
    raise SystemExit('Refusing non-test guest')
ROOT = Path(__file__).resolve().parents[1]
config = json.loads((ROOT / 'config/standard-split.example.json').read_text())
config['example_only'] = False
config['target']['user'] = 'ws-test'
config['selection_file'] = str(ROOT / 'profiles/default.json')
config['storage']['separate_var_lib'] = False
del config['storage']['mounts']['/var/lib']
for role, serial in [('system', 'system'), ('data', 'home')]:
    config['storage']['disks'][role] = {'stable_id': '/dev/disk/by-id/virtio-linux-setup-' + serial, 'minimum_bytes': 1024**3}
observed = json.loads(subprocess.check_output(['findmnt', '--json', '--list', '--output', 'TARGET,UUID']))
for path, declaration in config['storage']['mounts'].items():
    matches = [m for m in observed['filesystems'] if m['target'] == path]
    if len(matches) != 1 or not matches[0].get('uuid'):
        raise SystemExit('Required fixture mount missing')
    declaration['filesystem_uuid'] = matches[0]['uuid']
path = ROOT / 'guest.local.json'
path.write_text(json.dumps(config, indent=2) + '\n')
path.chmod(0o600)

def run(*args, expected=0):
    result = subprocess.run([str(ROOT / 'bootstrap'), *args, '--config', str(path), '--format', 'json'], capture_output=True, text=True)
    value = json.loads(result.stdout)
    if result.returncode != expected:
        print(result.stdout)
        raise SystemExit('Guest command returned unexpected exit: ' + str(result.returncode))
    print(args[0] + ': expected exit ' + str(expected) + ', observed ' + value['outcome'])
    return value

run('plan')
run('preflight')
# Restore fixture input even if a negative assertion fails.
try:
    bad = copy.deepcopy(config)
    bad['storage']['mounts']['/home']['filesystem_uuid'] = 'intentionally-wrong-fixture-uuid'
    path.write_text(json.dumps(bad))
    run('preflight', expected=1)
    run('install', expected=1)
finally:
    path.write_text(json.dumps(config, indent=2) + '\n')
print('PASS: real Ubuntu guest config/plan/preflight and failed-guard install boundary')
if args.controller:
    tool_env = dict(os.environ, PYTHONDONTWRITEBYTECODE='1')
    tool_env['PATH'] = str(ROOT / '.workstation/venv/bin') + ':' + tool_env['PATH']
    for attempt in range(2):
        result = run('install', expected=1)
        if not any(c['id'] == 'controller-foundation' and c['status'] == 'passed' for c in result['checks']):
            raise SystemExit('Controller foundation failed')
    subprocess.run([str(ROOT / '.workstation/venv/bin/python'), '-B', str(ROOT / 'script/test')], cwd=ROOT, env=tool_env, check=True)
    subprocess.run([str(ROOT / '.workstation/venv/bin/ansible-lint'), '--offline', *[str(p) for p in sorted((ROOT / 'ansible').glob('*.yml'))]], cwd=ROOT, env=tool_env, check=True)
    result = run('install', expected=1)
    if not any(c['id'] == 'controller-foundation' and c['status'] == 'passed' for c in result['checks']):
        raise SystemExit('Controller did not remain intact after QA/lint')
    print('PASS: locked controller, two Ansible foundation applies, pinned QA and Ansible lint')
    print('Application source/role gates remain failed; no full workstation success claimed.')

if args.packages:
    import http.server
    import tempfile
    import threading
    selection = ROOT / 'package-selection.local.json'
    selection.write_text(json.dumps({'schema_version': 1, 'id': 'package-fixture',
                                    'description': 'Disposable approved package acceptance',
                                    'capability_ids': ['curl', 'git', 'git-lfs', 'jq', 'ripgrep', 'shellcheck']}))
    selection.chmod(0o600)
    package_config = copy.deepcopy(config)
    package_config['selection_file'] = str(selection)
    try:
        path.write_text(json.dumps(package_config))
        run('install')
        run('install')
        import re
        recap = (ROOT / '.workstation/foundation.log').read_text()
        changes = re.findall(r'localhost\s+:.*?changed=(\d+)', recap)
        assert changes and all(int(n) == 0 for n in changes), 'Second apply changed managed state'
        run('verify')
        controller = ROOT / '.workstation'
        parked = ROOT / '.workstation-verification-fixture'
        assert not parked.exists()
        controller.rename(parked)
        try:
            run('verify')
            assert not controller.exists(), 'Verification recreated the controller'
        finally:
            parked.rename(controller)
        with tempfile.TemporaryDirectory(prefix='workstation-package-fixture-') as directory:
            working = Path(directory)
            subprocess.run(['git', 'init', '--quiet', directory], check=True)
            (working / 'fixture.json').write_text('{"message":"package workflow passed"}\n')
            subprocess.run(['git', '-C', directory, 'add', 'fixture.json'], check=True)
            diff = subprocess.check_output(['git', '-C', directory, 'diff', '--cached', '--name-only'], text=True)
            assert diff.strip() == 'fixture.json'
            subprocess.run(['git', '-C', directory, 'lfs', 'install', '--local'], check=True)
            payload = b'synthetic large-file workflow\n' * 100
            pointer = subprocess.check_output(['git', 'lfs', 'clean', '--', 'fixture.bin'], cwd=directory, input=payload)
            assert b'version https://git-lfs.github.com/spec/v1' in pointer
            restored = subprocess.check_output(['git', 'lfs', 'smudge', '--', 'fixture.bin'], cwd=directory, input=pointer)
            assert restored == payload
            found = subprocess.check_output(['rg', '--files-with-matches', 'package workflow passed', directory], text=True)
            assert str(working / 'fixture.json') in found.splitlines()
            missing = subprocess.run(['rg', 'absent-fixture-needle', directory], capture_output=True)
            assert missing.returncode == 1
            good = subprocess.run(['shellcheck', '-'], input='#!/bin/sh\nvalue="two words"\nprintf "%s\\n" "$value"\n', text=True, capture_output=True)
            assert good.returncode == 0, good.stdout
            bad_shell = subprocess.run(['shellcheck', '--format=json', '-'], input='#!/bin/sh\nvalue="two words"\necho $value\n', text=True, capture_output=True)
            assert bad_shell.returncode == 1 and any(d['code'] == 2086 for d in json.loads(bad_shell.stdout))
            class Handler(http.server.SimpleHTTPRequestHandler):
                def __init__(self, *values, **kwargs):
                    super().__init__(*values, directory=directory, **kwargs)
                def log_message(self, *values):
                    pass
            with http.server.ThreadingHTTPServer(('127.0.0.1', 0), Handler) as server:
                thread = threading.Thread(target=server.serve_forever, daemon=True)
                thread.start()
                try:
                    body = subprocess.check_output(['curl', '--noproxy', '*', '--fail', '--silent',
                                                   'http://127.0.0.1:' + str(server.server_port) + '/fixture.json'])
                    result = subprocess.check_output(['jq', '-r', '.message'], input=body)
                    assert result.strip() == b'package workflow passed'
                finally:
                    server.shutdown()
                    thread.join()
        subprocess.run(['sudo', '-n', 'apt-get', 'remove', '-y', 'jq'], check=True)
        drift = run('verify', expected=1)
        assert any(c['id'] == 'jq' and c['status'] == 'failed' for c in drift['checks'])
        absent = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', 'jq'], capture_output=True, text=True)
        assert absent.stdout != 'installed', 'Verification repaired the missing package'
        run('install')
        run('verify')
        print('PASS: approved packages apply twice, Git/LFS/curl/jq/ripgrep/ShellCheck workflows, read-only missing-package failure and recovery')
    finally:
        path.write_text(json.dumps(config, indent=2) + '\n')


if args.user_environment:
    import tempfile
    home = Path.home()
    with tempfile.TemporaryDirectory(prefix='user-environment-fixture-', dir=ROOT) as temporary:
        fixture = Path(temporary)
        identities = []
        for scope in ['personal', 'work']:
            directory = fixture / scope
            directory.mkdir()
            subprocess.run(['git', 'init', '--quiet', str(directory)], check=True)
            identities.append({'scope': scope, 'directory': str(directory), 'name': scope + ' Fixture', 'email': scope + '@example.invalid'})
        private = fixture / 'settings.local.json'
        private.write_text(json.dumps({'schema_version': 1, 'identities': identities}))
        private.chmod(0o600)
        selection = fixture / 'selection.local.json'
        selected = ['curl', 'git', 'git-lfs', 'jq', 'ripgrep', 'shellcheck', 'zsh', 'zsh-autosuggestions',
                    'zsh-syntax-highlighting', 'chezmoi', 'oh-my-zsh', 'nvm', 'node', 'pnpm', 'sdkman', 'java', 'maven', 'gradle', 'kotlin', 'mandrel', 'uv', 'python', 'opencode', 'codex', 'cline', 'shell-integration', 'git-identity', 'git-lfs-filters']
        selection.write_text(json.dumps({'schema_version': 1, 'id': 'user-files-fixture', 'description': 'Synthetic user files', 'capability_ids': selected}))
        selection.chmod(0o600)
        user_config = copy.deepcopy(config)
        user_config.update(selection_file=str(selection), user_settings_file=str(private))
        zshrc = home / '.zshrc'
        retained = '# user-environment fixture: unrelated content retained\n'
        if retained not in zshrc.read_text():
            with zshrc.open('a') as output:
                output.write(retained)
        try:
            path.write_text(json.dumps(user_config))
            run('install')
            run('install')
            run('verify')
            sdk_version = subprocess.check_output(['zsh', '-i', '-c', 'sdk version'], text=True)
            assert 'script: 5.23.0' in sdk_version and 'native: 0.7.35' in sdk_version
            java_project = fixture / 'java-project'
            java_project.mkdir()
            java_source = java_project / 'Hello.java'
            java_source.write_text('public class Hello { public static void main(String[] a) { System.out.println(System.getProperty("java.vendor") + "|" + System.getProperty("java.version")); } }\n')
            java_shell = r'''set -e
[[ "$JAVA_HOME" == "$SDKMAN_DIR/candidates/java/current" ]]
[[ "$(java -version 2>&1)" == *"Temurin"* ]]
for item in '25.0.4.1.1-ws-tem|Eclipse Adoptium|25.0.4.1' '21.0.12.1.1-ws-tem|Eclipse Adoptium|21.0.12.1' '25.0.4.1.1-ws-ms|Microsoft|25.0.4.1' '21.0.12.1.1-ws-ms|Microsoft|21.0.12.1'; do
    candidate="${item%%|*}"
    expected="${item#*|}"
    sdk use java "$candidate"
    [[ "$JAVA_HOME" == "$SDKMAN_DIR/candidates/java/$candidate" ]]
    javac -d "$1" "$1/Hello.java"
    [[ "$(java -cp "$1" Hello)" == "$expected" ]]
    sdk current java | grep -F 'Current default java version 25.0.4.1.1-ws-tem'
done
sdk use java 25.0.4.1.1-ws-tem
'''
            subprocess.run(['zsh', '-i', '-c', java_shell, '--', str(java_project)], check=True, capture_output=True)
            java_current = home / '.local/share/linux-os-setup/sdkman/candidates/java/current'
            subprocess.run(['zsh', '-i', '-c', 'sdk default java 21.0.12.1.1-ws-tem'], check=True, capture_output=True)
            old_default = os.readlink(java_current)
            run('verify', expected=1)
            assert os.readlink(java_current) == old_default
            run('install')
            run('verify')
            java_backups = list((home / '.local/state/linux-os-setup/java-default-backups').glob('*.json'))
            assert any(json.loads(p.read_text()) == {'kind': 'symlink', 'target': old_default} for p in java_backups)
            assert all(not p.stat().st_mode & 0o077 for p in java_backups)
            print('PASS: four installed JDK compile/run and selection, Temurin 25 default and private drift recovery')
            from jvm_build_fixture import check as check_jvm_builds
            check_jvm_builds(fixture)
            from jvm_build_fixture import check_native
            check_native(fixture)
            # Go and Rust are omitted from the selection (D019): host toolchains
            # are not installed and the config loader refuses to select an omitted
            # capability. The roles and their fixtures stay in the repository, so
            # this runs again as soon as either is selected.
            if {'go', 'rust'} & set(selected):
                from go_build_fixture import check as check_go_build
                check_go_build(fixture)
                go_version = home / '.local/share/linux-os-setup/tools/go/go1.27.1/go/VERSION'
                go_original = go_version.read_bytes()
                go_version.write_bytes(go_original + b'\ndeliberate-go-drift\n')
                run('verify', expected=1)
                run('install', expected=1)
                assert go_version.read_bytes() != go_original
                go_version.write_bytes(go_original)
                run('verify')
                print('PASS: Go full-payload drift fails verification and refuses replacement')
                from rust_build_fixture import check as check_rust_build
                check_rust_build(fixture)
                rust_root = home / '.local/share/linux-os-setup/rust/1.29.1-1.98.1'
                rustc = rust_root / 'rustup/toolchains/1.98.1-x86_64-unknown-linux-gnu/bin/rustc'
                rustc_original = rustc.read_bytes()
                rustc.write_bytes(rustc_original + b'\ndeliberate-rust-drift\n')
                run('verify', expected=1)
                run('install', expected=1)
                assert rustc.read_bytes() != rustc_original
                rustc.write_bytes(rustc_original)
                run('verify')
                settings = rust_root / 'rustup/settings.toml'
                settings_original = settings.read_text()
                settings.write_text(settings_original.replace(
                    '1.98.1-x86_64-unknown-linux-gnu',
                    'nightly-x86_64-unknown-linux-gnu'))
                run('verify', expected=1)
                assert 'nightly-x86_64-unknown-linux-gnu' in settings.read_text()
                settings.write_text(settings_original)
                run('verify')
                print('PASS: Rust toolchain/default drift fails verification and refuses payload replacement')
            else:
                print('SKIP: Go and Rust fixtures — both capabilities are omitted')
            from python_build_fixture import check as check_python_build
            check_python_build(fixture)
            run('verify')
            python_root = home / '.local/share/linux-os-setup/tools/python/3.14.7+20260901'
            sysconfig = python_root / 'cpython-3.14.7-linux-x86_64-gnu/lib/python3.14/_sysconfigdata__linux_x86_64-linux-gnu.py'
            original = sysconfig.read_bytes()
            sysconfig.chmod(0o644)
            sysconfig.write_bytes(original + b'\n# deliberate Python payload drift\n')
            run('verify', expected=1)
            run('install', expected=1)
            assert sysconfig.read_bytes() != original
            sysconfig.write_bytes(original)
            sysconfig.chmod(0o444)
            run('verify')
            print('PASS: generated Python prefix/content drift fails without repair; explicit fixture restore')
            from opencode_fixture import check as check_opencode
            check_opencode(fixture)
            opencode_binary = home / '.local/share/linux-os-setup/tools/opencode/1.18.31/opencode'
            opencode_original = opencode_binary.read_bytes()
            opencode_binary.write_bytes(opencode_original + b'\ndeliberate-opencode-drift\n')
            run('verify', expected=1)
            run('install', expected=1)
            assert opencode_binary.read_bytes() != opencode_original
            opencode_binary.write_bytes(opencode_original)
            run('verify')
            print('PASS: OpenCode source-payload drift fails verification without repair; explicit fixture restore')
            from codex_fixture import check as check_codex
            check_codex(fixture)
            codex_binary = home / '.local/share/linux-os-setup/tools/codex/0.154.0/codex'
            codex_original = codex_binary.read_bytes()
            codex_binary.write_bytes(codex_original + b'\ndeliberate-codex-drift\n')
            run('verify', expected=1)
            run('install', expected=1)
            assert codex_binary.read_bytes() != codex_original
            codex_binary.write_bytes(codex_original)
            run('verify')
            print('PASS: Codex source-payload drift fails verification without repair; explicit fixture restore')
            from cline_fixture import check as check_cline
            check_cline(fixture)
            cline_root = home / '.local/share/linux-os-setup/tools/cline/3.0.62'
            for name in ['node_modules/@cline/cli-linux-x64/bin/cline',
                         'node_modules/@cline/cli-linux-x64/cline-hub/webview/index.html',
                         'bin/cline']:
                target = cline_root / name
                original = target.read_bytes()
                target.write_bytes(original + b'\ndeliberate-cline-drift\n')
                run('verify', expected=1)
                run('install', expected=1)
                assert target.read_bytes() != original
                target.write_bytes(original)
                run('verify')
            print('PASS: Cline binary/asset/launcher drift fails without repair; explicit fixture restore')
            subprocess.run(['sudo', '-n', 'apt-get', 'remove', '-y', 'g++'], check=True)
            native_drift = run('verify', expected=1)
            # Mandrel and Rust both declare g++ as a prerequisite; only the
            # selected ones can be expected to report it missing.
            for capability in [c for c in ('mandrel', 'rust') if c in selected]:
                assert any(c['id'] == capability and c['status'] == 'failed'
                           for c in native_drift['checks']), capability
            absent = subprocess.run(['dpkg-query', '-W', '-f=${db:Status-Status}', 'g++'], capture_output=True, text=True)
            assert absent.returncode != 0 or absent.stdout != 'installed'
            run('install')
            run('verify')
            print('PASS: missing shared native prerequisite fails verification for every selected\n      capability that declares it, without repair; explicit apply restores it')
            maven_current = home / '.local/share/linux-os-setup/sdkman/candidates/maven/current'
            maven_current.unlink()
            maven_current.symlink_to('missing-fixture')
            run('verify', expected=1)
            assert os.readlink(maven_current) == 'missing-fixture'
            run('install')
            run('verify')
            tool_backups = list((home / '.local/state/linux-os-setup/jvm-tool-default-backups').glob('*.json'))
            assert any(json.loads(p.read_text()) == {'candidate': 'maven', 'kind': 'symlink', 'target': 'missing-fixture'} for p in tool_backups)
            assert all(not p.stat().st_mode & 0o077 for p in tool_backups)
            print('PASS: JVM tool default drift detected without repair and explicit reapply retained private backup')
            sdk_source = home / '.local/share/linux-os-setup/sdkman/src/sdkman-use.sh'
            sdk_original = sdk_source.read_bytes()
            try:
                sdk_source.write_bytes(sdk_original + b'\n# deliberate SDKMAN drift\n')
                run('verify', expected=1)
                run('install', expected=1)
                assert sdk_source.read_bytes() != sdk_original
            finally:
                sdk_source.write_bytes(sdk_original)
            run('verify')
            controller = ROOT / '.workstation'
            parked = ROOT / '.workstation-user-verification-fixture'
            assert not parked.exists()
            controller.rename(parked)
            try:
                run('verify')
                assert not controller.exists()
            finally:
                parked.rename(controller)
            assert retained in zshrc.read_text()
            assert zshrc.read_text().count('# BEGIN linux-os-setup managed include') == 1
            import re
            assert all(int(n) == 0 for n in re.findall(r'localhost\s+:.*?changed=(\d+)', (ROOT / '.workstation/foundation.log').read_text()))
            for identity in identities:
                for key in ['name', 'email']:
                    actual = subprocess.check_output(['git', '-C', identity['directory'], 'config', '--get', 'user.' + key], text=True).strip()
                    assert actual == identity[key]
            directory = Path(identities[0]['directory'])
            subprocess.run(['git', '-C', str(directory), 'lfs', 'track', '*.bin'], check=True)
            payload = b'round trip through configured LFS filters\n' * 100
            (directory / 'fixture.bin').write_bytes(payload)
            subprocess.run(['git', '-C', str(directory), 'add', '.gitattributes', 'fixture.bin'], check=True)
            pointer = subprocess.check_output(['git', '-C', str(directory), 'show', ':fixture.bin'])
            assert b'https://git-lfs.github.com/spec/v1' in pointer
            (directory / 'fixture.bin').unlink()
            subprocess.run(['git', '-C', str(directory), 'checkout-index', '-f', 'fixture.bin'], check=True)
            assert (directory / 'fixture.bin').read_bytes() == payload
            shell = '[[ $_WORKSTATION_SHELL_LOADED == 1 ]] && (( $+functions[proxyon] && $+functions[proxyoff] && $+functions[_zsh_autosuggest_start] && $+functions[_zsh_highlight] )) && [[ $plugins == git ]]'
            subprocess.run(['zsh', '-i', '-c', shell], check=True, capture_output=True)
            from_node = fixture / 'node-project'
            from_node.mkdir()
            dependency = from_node / 'dependency'
            dependency.mkdir()
            (dependency / 'package.json').write_text(json.dumps({'name': 'local-fixture-dependency', 'version': '1.0.0', 'main': 'index.js'}))
            (dependency / 'index.js').write_text('module.exports = 42;\n')
            (from_node / 'package.json').write_text(json.dumps({'name': 'node-workflow-fixture', 'version': '1.0.0', 'private': True,
                'scripts': {'test': 'node --test test.cjs', 'build': 'node build.cjs'}, 'dependencies': {'local-fixture-dependency': 'file:./dependency'}}))
            (from_node / 'test.cjs').write_text("const test = require('node:test'); const assert = require('node:assert/strict'); test('local dependency', () => assert.equal(require('local-fixture-dependency'), 42));\n")
            (from_node / 'build.cjs').write_text("require('node:fs').writeFileSync('built.txt', String(require('local-fixture-dependency')));\n")
            node_lock = json.loads((ROOT / 'locks/node.json').read_text())['artifacts'][0]
            (from_node / '.nvmrc').write_text(node_lock['version'] + '\n')
            node_shell = 'cd "$1" && nvm use --silent && [[ $(nvm current) == "$2" ]] && nvm exec --silent "$2" node --version && npm install --offline --ignore-scripts --no-audit --no-fund && npm test && npm run build && nvm deactivate >/dev/null && nvm use --silent default && [[ $(node --version) == "$2" ]]'
            subprocess.run(['zsh', '-i', '-c', node_shell, '--', str(from_node), node_lock['version']], check=True, capture_output=True)
            assert (from_node / 'built.txt').read_text() == '42'
            assert (from_node / 'package-lock.json').is_file()
            alias = home / '.local/share/linux-os-setup/nvm/alias/default'
            alias.write_text('v0.0.0\n')
            run('verify', expected=1)
            assert alias.read_text() == 'v0.0.0\n'
            run('install')
            run('verify')
            saved_defaults = list((home / '.local/state/linux-os-setup/node-default-backups').glob('*'))
            assert any(p.read_text() == 'v0.0.0\n' and not p.stat().st_mode & 0o077 for p in saved_defaults)
            print('PASS: offline local Node/npm test/build, nvm exec/project selection and default drift recovery with private backup')
            pnpm_project = fixture / 'pnpm-project'
            pnpm_project.mkdir()
            import shutil
            shutil.copytree(dependency, pnpm_project / 'dependency')
            for name in ['package.json', 'test.cjs', 'build.cjs']:
                shutil.copyfile(from_node / name, pnpm_project / name)
            pnpm_shell = 'cd "$1" && pnpm install --offline --ignore-scripts && pnpm install --offline --frozen-lockfile --ignore-scripts && pnpm test && pnpm run build && before=$(command -v pnpm) && nvm deactivate >/dev/null && [[ $(command -v pnpm) == "$before" ]] && [[ $(pnpm --version) == 12.4.1 ]] && nvm use --silent default'
            subprocess.run(['zsh', '-i', '-c', pnpm_shell, '--', str(pnpm_project)], check=True, capture_output=True)
            assert (pnpm_project / 'built.txt').read_text() == '42'
            assert (pnpm_project / 'pnpm-lock.yaml').is_file()
            print('PASS: pnpm offline local install/frozen lock/test/build and executable retained after NVM deactivation')
            proxy = fixture / 'proxy.local.json'
            proxy.write_text(json.dumps(dict(http_proxy='http://127.0.0.1:12345', https_proxy='http://127.0.0.1:12345', all_proxy='', no_proxy='localhost')))
            proxy.chmod(0o600)
            shell = r'''source "$1"
export WORKSTATION_PROXY_SETTINGS="$2"
unset http_proxy https_proxy all_proxy no_proxy HTTP_PROXY HTTPS_PROXY ALL_PROXY NO_PROXY
http_proxy=original
export HTTP_PROXY=exported-original
no_proxy=''
proxyoff || exit 11
proxyon || exit 12
[[ $http_proxy == http://127.0.0.1:12345 && $HTTP_PROXY == $http_proxy ]] || exit 13
proxyon || exit 14
WORKSTATION_PROXY_SETTINGS="$2.missing"
proxyon && exit 15
[[ $http_proxy == http://127.0.0.1:12345 ]] || exit 16
proxyoff || exit 17
[[ $http_proxy == original && $HTTP_PROXY == exported-original && $parameters[http_proxy] != *export* && $parameters[HTTP_PROXY] == *export* ]] || exit 18
[[ ! -v https_proxy && -v no_proxy && -z $no_proxy ]] || exit 19
proxyoff || exit 20
'''
            subprocess.run(['zsh', '-f', '-c', shell, '--', str(home / '.config/linux-os-setup/proxy.zsh'), str(proxy)], check=True, capture_output=True)
            managed = home / '.config/linux-os-setup/shell.zsh'
            original = managed.read_text()
            managed.write_text(original + '# deliberate managed-file drift\n')
            run('verify', expected=1)
            assert managed.read_text() != original
            run('install')
            run('verify')
            backups = list((home / '.local/state/linux-os-setup/user-files').glob('backup-*/manifest.json'))
            assert backups and all(not p.stat().st_mode & 0o077 for p in backups)
            import hashlib
            restored_backup = False
            for manifest_path in backups:
                for item in json.loads(manifest_path.read_text()):
                    raw = (manifest_path.parent / item['file']).read_bytes()
                    assert hashlib.sha256(raw).hexdigest() == item['sha256']
                    if item['path'] == '.config/linux-os-setup/shell.zsh' and b'deliberate managed-file drift' in raw:
                        managed.write_bytes(raw)
                        managed.chmod(item['mode'])
                        restored_backup = True
                        break
                if restored_backup:
                    break
            assert restored_backup
            run('verify', expected=1)
            run('install')
            run('verify')
            sys.path.insert(0, str(ROOT / 'script'))
            from workstation.artifacts import destination, registry
            catalogue = json.loads((ROOT / 'catalogue/capabilities.json').read_text())
            tools = registry({e['id']: e for e in catalogue['capabilities']})
            omz = destination(home, tools['oh-my-zsh']) / Path(tools['oh-my-zsh']['entrypoint']).parent / 'README.md'
            original_artifact = omz.read_bytes()
            try:
                omz.write_bytes(original_artifact + b'\nmodified artifact fixture\n')
                run('verify', expected=1)
                run('install', expected=1)
                assert omz.read_bytes() != original_artifact
            finally:
                omz.write_bytes(original_artifact)
            run('verify')
            print('PASS: private backup restoration and immutable artifact failure without replacement')
            print('PASS: retained user content, repeat apply, Git scopes/LFS payload, shell plugins/proxy transitions and read-only drift/recovery')
        finally:
            path.write_text(json.dumps(config, indent=2) + '\n')
