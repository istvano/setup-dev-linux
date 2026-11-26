"""What the VM harness asks the guest to run, in one place (controller ruling RB11).

Pure: builds commands and reads reports; runs nothing. vm/manifest_fixture.py
(the clean cycle) and vm/guest-foundation.py (the foundation suite) use it,
and tests/test_vm_harness.py pins it on any host, since the guest can only be
booted on a Linux machine with KVM.

The clean cycle applies the way the operator does: explicit host profiles,
then the handoff to setup-dev-linux-wsl. The guest has no terminal, so the
first apply passes --cli-profiles and a throwaway git identity, which makes
setup-dev-linux-wsl's bootstrap run with --non-interactive. The harness
reaches the guest over SSH, so whenever the firewall profile is selected the
first apply passes --allow-ssh (apply refuses over SSH without a choice).

The re-run passes none of these, nor --profiles: both repositories then use
what they recorded, which is the re-run path an operator takes, and
rerun_findings checks that the report says so.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'script'))
from workstation.handoff import FORMER_CLI_PROFILES  # noqa: E402

# Every host profile except gpu: the guest has no NVIDIA hardware.
CLEAN_CYCLE_PROFILES = 'desktop,media,productivity,ai,network,lab,dev-gui,firewall'
# Throwaway, for the disposable guest only. example.invalid never resolves.
GUEST_IDENTITY = ('VM Test', 'ws-test@example.invalid')
# The foundation suite's controller check: the smallest host run there is (the
# base group and the firewall stage), SSH kept open, no handoff.
CONTROLLER_ONLY_ARGS = ['apply', '--profiles', 'firewall', '--allow-ssh', '--no-handoff']
HANDOFF_MODES = (None, 'first', 'again')


def apply_command(bootstrap, config, profiles, *, handoff):
    """The apply the clean cycle runs.

    handoff: None (host only), 'first' (non-interactive, with the former
    command-line set) or 'again' (no --profiles, no --allow-ssh, no list, no
    identity: every choice comes from what the first apply recorded).
    """
    if handoff not in HANDOFF_MODES:
        raise ValueError('handoff must be one of ' + repr(HANDOFF_MODES))
    command = [str(bootstrap), 'apply', '--config', str(config), '--format', 'json']
    if handoff == 'again':
        return command
    command += ['--profiles', profiles]
    if 'firewall' in profiles.split(','):
        command.append('--allow-ssh')
    if handoff is None:
        command.append('--no-handoff')
    else:
        command += ['--cli-profiles', FORMER_CLI_PROFILES,
                    '--cli-git-name', GUEST_IDENTITY[0],
                    '--cli-git-email', GUEST_IDENTITY[1]]
    return command


def rerun_findings(report, profiles):
    """What is wrong with a re-run's apply report, as messages; [] when nothing is.

    The re-run passed no --profiles and no --allow-ssh, so the report must say
    the profiles came from the record and are the ones the first apply chose,
    and, with the firewall, that SSH stayed allowed by the recorded choice.
    """
    findings = []
    summary = report.get('profiles') or {}
    if summary.get('source') != 'recorded':
        findings.append(f"profiles source is {summary.get('source')}, expected recorded")
    if summary.get('selected') != list(profiles):
        findings.append(f"profiles {summary.get('selected')} are not the recorded {list(profiles)}")
    if 'firewall' in profiles:
        choice = next((c for c in report.get('checks', [])
                       if c.get('id') == 'firewall:ssh-choice'), None)
        reason = choice.get('reason') if choice else None
        if reason != 'allow-ssh-true-recorded':
            findings.append(f'firewall:ssh-choice is {reason}, expected allow-ssh-true-recorded')
    return findings


def verify_command(bootstrap, config, profiles, *, handoff):
    """bootstrap verify; with the handoff it ends with setup-dev-linux-wsl's verify."""
    command = [str(bootstrap), 'verify', '--config', str(config), '--format', 'json',
               '--profiles', profiles]
    if not handoff:
        command.append('--no-handoff')
    return command


def apt_findings(text):
    """The lines of `apt-get update` / `apt-get check` output that are not clean.

    A warning or an error is a finding; so is the Signed-By conflict two sources
    for one URI produce (claude-desktop registers its own source, and
    setup-dev-linux-wsl adds Anthropic's for Claude Code).
    """
    return [line for line in text.splitlines()
            if line.startswith(('W:', 'E:')) or 'Conflicting values set for option Signed-By' in line]


def check_passed(report, check_id):
    return any(c.get('id') == check_id and c.get('status') == 'passed'
               for c in report.get('checks', []))
