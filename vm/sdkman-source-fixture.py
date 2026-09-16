#!/usr/bin/python3 -B
"""Isolated SDKMAN source compatibility experiment, not production delivery."""
import argparse
import os
from pathlib import Path
import pwd
import shutil
import shlex
import subprocess
import sys
import tempfile
import tarfile
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'script'))
from workstation.artifacts import digest, extract_zip, validate_payload
from workstation.config import load_context, load_json, require, validate_schema
from workstation.storage import preflight

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--expected-vm-id', required=True)
parser.add_argument('--config', type=Path, required=True)
parser.add_argument('--java-review', action='store_true')
args = parser.parse_args()
require(Path('/etc/linux-os-setup-test-vm').read_text().strip() == args.expected_vm_id,
        'refusing-non-test-guest')
config = load_context(args.config)['config']
require(os.geteuid() != 0 and pwd.getpwuid(os.geteuid()).pw_name == config['target']['user'],
        'fixture-target-user-required')
require(preflight(config)[1] == 0, 'fixture-storage-preflight-failed')
lock = load_json(ROOT / 'locks/sdkman-review.json')[0]
validate_schema(lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
require([r['id'] for r in lock['artifacts']] == ['sdkman-cli', 'sdkman-native'], 'invalid-sdkman-review')
os.umask(0o077)
with tempfile.TemporaryDirectory(prefix='sdkman-source-fixture-') as temporary:
    root = Path(temporary)
    payloads = []
    for record in lock['artifacts']:
        archive = root / (record['id'] + '.zip')
        require(record['url'].startswith('https://github.com/sdkman/'), 'unapproved-sdkman-review-url')
        with urllib.request.urlopen(record['url'], timeout=60) as response, archive.open('wb') as output:
            shutil.copyfileobj(response, output)
        require(digest(archive) == record['sha256'], 'sdkman-review-digest-mismatch')
        payload = root / record['id']
        payload.mkdir()
        extract_zip(archive, payload)
        validate_payload(payload, record)
        payloads.append(payload / Path(record['entrypoint']).parts[0])
    manager = root / 'manager'
    shutil.copytree(payloads[0], manager)
    shutil.copytree(payloads[1] / 'libexec', manager / 'libexec')
    for folder in ('etc', 'var', 'ext', 'tmp', 'candidates'):
        (manager / folder).mkdir(exist_ok=True)
    for name, value in {'platform': 'linuxx64', 'candidates': 'java,maven,gradle,kotlin',
                        'version': lock['artifacts'][0]['version'],
                        'version_native': lock['artifacts'][1]['version'], 'delay_upgrade': ''}.items():
        (manager / 'var' / name).write_text(value + '\n')
    (manager / 'etc/config').write_text('''sdkman_auto_answer=true
sdkman_selfupdate_feature=false
sdkman_auto_env=false
sdkman_auto_complete=false
sdkman_healthcheck_enable=false
sdkman_native_enable=true
sdkman_insecure_ssl=false
sdkman_checksum_enable=true
''')
    # Fake local candidates test manager mechanics only; these are not Java builds.
    for version in ('ws-fixture-a', 'ws-fixture-b'):
        candidate = root / version / 'bin'
        candidate.mkdir(parents=True)
        (candidate / 'java').write_text('#!/bin/sh\nprintf "%s\\n" ' + version + '\n')
        (candidate / 'java').chmod(0o755)
    env = {k: v for k, v in os.environ.items() if not k.startswith(('SDKMAN_', 'BASH_ENV', 'ENV', 'JAVA_HOME'))}
    env.update(SDKMAN_DIR=str(manager), FIXTURE_ROOT=str(root),
               SDKMAN_CANDIDATES_API='http://127.0.0.1:1', SDKMAN_BROKER_API='http://127.0.0.1:1')
    shell = r'''
set -e
source "$SDKMAN_DIR/bin/sdkman-init.sh"
__sdkman_install_local_version java ws-fixture-a "$FIXTURE_ROOT/ws-fixture-a"
__sdkman_install_local_version java ws-fixture-b "$FIXTURE_ROOT/ws-fixture-b"
sdk version
sdk default java ws-fixture-a
source "$SDKMAN_DIR/bin/sdkman-init.sh"
test "$(java)" = ws-fixture-a
sdk use java ws-fixture-b
test "$(java)" = ws-fixture-b
test "$JAVA_HOME" = "$SDKMAN_DIR/candidates/java/ws-fixture-b"
sdk current java | grep -F "Current default java version ws-fixture-a"
test "$(realpath "$(sdk home java ws-fixture-a)")" = "$FIXTURE_ROOT/ws-fixture-a"
sdk use java ws-fixture-a
test "$(java)" = ws-fixture-a
test "$(realpath "$SDKMAN_DIR/candidates/java/current")" = "$FIXTURE_ROOT/ws-fixture-a"
'''
    for executable in ('bash', 'zsh'):
        # Fresh independent candidate state for each shell.
        if (manager / 'candidates/java').exists():
            shutil.rmtree(manager / 'candidates/java')
        subprocess.run([executable, '-f', '-c', shell], env=env, check=True, timeout=60)
    for record, payload in zip(lock['artifacts'], payloads):
        validate_payload(payload.parent, record)
    if args.java_review:
        java_lock = load_json(ROOT / 'locks/java-review.json')[0]
        validate_schema(java_lock, load_json(ROOT / 'locks/user-tools.schema.json')[0])
        require([r['id'] for r in java_lock['artifacts']] ==
                ['temurin-25', 'temurin-21', 'microsoft-25', 'microsoft-21'], 'invalid-java-review')
        java_payloads = []
        for record in java_lock['artifacts']:
            require(record['url'].startswith(('https://github.com/adoptium/', 'https://aka.ms/download-jdk/')),
                    'unapproved-java-review-url')
            archive = root / (record['id'] + '.tar.gz')
            with urllib.request.urlopen(record['url'], timeout=60) as response, archive.open('wb') as output:
                shutil.copyfileobj(response, output)
            require(digest(archive) == record['sha256'], 'java-review-digest-mismatch')
            payload = root / record['id']
            payload.mkdir()
            with tarfile.open(archive) as source:
                source.extractall(payload, filter='data')
            validate_payload(payload, record)
            java_payloads.append(payload)
        source = root / 'Hello.java'
        source.write_text('''public class Hello {
  public static void main(String[] args) {
    System.out.println(System.getProperty("java.vendor") + "|" + System.getProperty("java.version"));
  }
}
''')
        lines = ['set -e', 'source "$SDKMAN_DIR/bin/sdkman-init.sh"']
        for record, payload in zip(java_lock['artifacts'], java_payloads):
            candidate = payload / Path(record['entrypoint']).parts[0]
            lines.append('__sdkman_install_local_version java ws-' + record['id'] + ' ' + shlex.quote(str(candidate)))
        lines += ['sdk default java ws-temurin-25', 'source "$SDKMAN_DIR/bin/sdkman-init.sh"']
        for record in java_lock['artifacts']:
            version = 'ws-' + record['id']
            build = root / ('build-' + record['id'])
            build.mkdir()
            vendor = 'Eclipse Adoptium' if record['id'].startswith('temurin') else 'Microsoft'
            expected = vendor + '|' + record['version'].rsplit('-', 1)[0]
            lines += ['sdk use java ' + version,
                      'test "$JAVA_HOME" = "$SDKMAN_DIR/candidates/java/' + version + '"',
                      'javac -d ' + shlex.quote(str(build)) + ' ' + shlex.quote(str(source)),
                      'test "$(java -cp ' + shlex.quote(str(build)) + ' Hello)" = ' + shlex.quote(expected),
                      'sdk current java | grep -F "Current default java version ws-temurin-25"']
        lines += ['sdk use java ws-temurin-25', 'test "$JAVA_HOME" = "$SDKMAN_DIR/candidates/java/ws-temurin-25"']
        for key in ('JAVA_TOOL_OPTIONS', 'JDK_JAVA_OPTIONS', '_JAVA_OPTIONS', 'CLASSPATH'):
            env.pop(key, None)
        for executable in ('bash', 'zsh'):
            shutil.rmtree(manager / 'candidates/java')
            subprocess.run([executable, '-f', '-c', '\n'.join(lines)], env=env, check=True, timeout=120)
        for record, payload in zip(java_lock['artifacts'], java_payloads):
            validate_payload(payload, record)
        print('PASS: all four reviewed JDKs compile/run with expected vendor/version in Bash and Zsh; Temurin 25 default retained')
print('PASS: reviewed SDKMAN CLI/native pair, local registration/default/use/current/home in Bash and Zsh')
print('Production SDKMAN role, Maven/Gradle/Kotlin/Mandrel and workstation acceptance remain unfinished.')
