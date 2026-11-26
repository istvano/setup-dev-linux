# Implemented operator commands

Current scope: configuration/preview, standard-layout storage preflight, isolated
controller, Ansible foundation and the host manifest (repositories, packages, snaps,
pinned desktop binaries, VS Code extensions, GNOME settings). Command-line tools,
runtimes, the shell and Docker are installed by setup-dev-linux-wsl
([MOVED.md](MOVED.md)). Remaining application roles and full workstation readiness
are unfinished. Feature contracts and dependency order are in [specs](../specs/README.md).

| Command | Current behavior |
|---|---|
| `./bootstrap plan --config PATH [--profiles LIST] [--no-handoff \| --cli-profiles LIST] [--linux-ref REF] --format json` | Prints the `Profiles:` line and the stages the selection runs, ending with `stage:handoff`, and the first-run `hint:` line when setup-dev-linux-wsl has recorded no profile choice. Pure standard-library preview; examples allowed and labelled; no downloads/sudo/writes |
| `./bootstrap preflight --config PATH --format json` | Live platform/user/disk/mount checks and the host prerequisites `gpg` and `git`; examples rejected; no writes |
| `./bootstrap apply --config PATH [--profiles LIST] [--allow-ssh \| --no-allow-ssh] [--no-handoff \| --cli-profiles LIST] [--linux-ref REF] --format json` | `install` is an alias. Guard first, target user only, verified uv/Python archives and frozen controller graph, Ansible foundation and selected approved packages; reports remaining source/role failures; then the handoff to setup-dev-linux-wsl unless `--no-handoff` |
| `./bootstrap verify --config PATH [--profiles LIST] [--allow-ssh \| --no-allow-ssh] [--no-handoff] --format json` | Checks the recorded profiles (`~/.local/state/setup-dev-linux/state.json`, or under `$XDG_STATE_HOME`) unless given. Read-only preflight, approved package state and declared source/implementation gaps, then setup-dev-linux-wsl's `script/verify --target linux` as `cli:verify` unless `--no-handoff`; no controller sync or repair |
| `./script/test` | Strict static and behavioral suite in the existing Python environment |
| `./script/test-vm` | Copy reviewed repository sources to the dedicated guest and test foundation behavior |
| `./script/test-vm --controller` | Additionally acquire the isolated controller, apply foundation twice and run pinned QA/lint in the guest |
| `./script/test-vm --controller --reboot` | Verify a real guest reboot and repeat the foundation acceptance |

Firewall: the `firewall` profile runs `ansible/firewall.yml` (UFW default deny incoming, allow
outgoing, enabled; OpenSnitch from the Ubuntu archive, enabled, `DefaultAction` `allow` in
`/etc/opensnitchd/default-config.json`; its UI only with the desktop set, whose per-user
`~/.config/opensnitch/settings.conf` gets `[global] default_action=1` only when absent, with
a backup before any edit). Allow mode is seeded once (`firewall.opensnitch_seeded` and
`firewall.opensnitch_ui_seeded` in `state.json`) and never rewritten, so switching to deny
sticks; after that, re-runs and the handoff may prompt. `verify` reports the daemon and UI
modes as notices. Over SSH without `--allow-ssh`, apply warns on stderr and adds a
`firewall:ssh-closing` notice. Incoming SSH is allowed
only with `--allow-ssh`. The choice is recorded as `firewall.allow_ssh` in the per-user
`state.json` (not in your config file); later runs without a flag reuse it, `--no-allow-ssh`
turns it off and removes the `OpenSSH` rule. `verify` reads `ufw status verbose` through
`sudo -n` (run `sudo -v` first, otherwise that check is `deferred`). Docker's published ports
bypass UFW; `verify` prints a notice when `docker` is present. Switching OpenSnitch to deny is
a later, manual decision.

Handoff: the last apply stage, run only when the host stages succeeded (host verify findings
are reported but do not hold it back). As the target user, never root, it clones
`https://github.com/istvano/setup-dev-linux-wsl` into `~/workspace/setup-dev-linux-wsl` or
updates that clone, fetches, resolves `--linux-ref` (default `main`; `origin/<ref>`, else a tag
or commit) with `git rev-parse --verify`, checks it out once with `checkout --detach`, then runs
`./bootstrap apply --target linux` attached to the terminal (it prompts for the git identity).
It stops, naming the directory and changing nothing, when that directory is not a git clone,
when its `remote.origin.url` is another repository, or when tracked files have local changes;
an unknown ref stops with `unknown ref`. `--profiles LIST` is passed only with
`--cli-profiles LIST`: setup-dev-linux-wsl refuses a list that disagrees with its recorded
choice, so re-runs pass none. When it has recorded no choice and `--cli-profiles` is absent,
plan prints a `hint:` line, and apply prints it before the host stages and again just before
the bootstrap (whose first run installs its default without asking and records it). The line
names `core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp` (plus `gpu-nvidia` with the `gpu`
profile), the set this repository installed before, says to interrupt and re-run apply with
`--cli-profiles` to get it on this run, and names the record
(`${XDG_CONFIG_HOME:-~/.config}/chezmoi/chezmoi.toml`). Once recorded, setup-dev-linux-wsl
refuses a different `--cli-profiles`; change `[data] profiles` in that file instead, then
re-run. Ctrl-C during apply (a host stage or the bootstrap) prints one line, emits the report
with an `interrupted` check and exits 130; re-running is safe. A failed handoff fails the run with
setup-dev-linux-wsl's exit code (a `handoff` check, outcome `failed`); re-running is safe. In
JSON mode its programs' output goes to standard error so the report stays the only standard
output. `apply` does not run `cli:verify` itself: that bootstrap ends with its own verify.

`apply` currently **cannot report full success for the selected workstation**.
Controller success followed by exit 1 identifies selected source approvals still
missing; approved selected packages may have installed successfully. A private selection
containing only implemented capabilities with their required private settings can pass its operation, while `workstation_ready` remains
false because whole-workstation acceptance is unfinished. Other missing role
implementation is incomplete (exit 3). Invalid inputs use exit 2. Never run apply
on the physical workstation merely to see what happens; use pure plan/preflight.

Use private, non-example configuration copied from a declared storage layout. Supply
real target-user and stable by-id disk identities, capacities and filesystem UUIDs.
Do not commit that input. Standard split with /var/lib on root is implemented.

## Disposable VM

The dedicated guest is Ubuntu 26.04 amd64, initially an official cloud image with
Ubuntu GNOME packages added for desktop testing. Image signature and checksum
verification use [the image lock](../vm/ubuntu-image.lock.json). It has a 64 GiB
system overlay, 24 GiB synthetic home disk, 8 GiB RAM and 4 vCPUs. Actual files grow
with use; these are fixture sizes, not generic workstation defaults.

```bash
./script/vm fetch
./script/vm prepare
./script/vm start
./script/vm status
./script/vm ssh 'cloud-init status'
./script/test-vm --controller
./script/vm screenshot
./script/vm stop
```

Host sandbox access may require tool approval for KVM/process visibility and loopback
SSH. No sudo/host package installation is needed with the currently available QEMU
tools. There is no implicit destroy/reset operation. Private VM keys, seeds, known-host
pins, serial logs and screenshots live in ignored `vm/state`; disks are in ignored
`vm/disks`. SSH binds only 127.0.0.1:22226. No production credentials or physical disks
are shared. The guest has a dedicated passwordless-sudo test user.
Its copied repository/controller lives under `/var/tmp` to survive reboot. SSH
readiness may be retried; failed post-reboot acceptance commands are not retried.

`vm/desktop-fixture.py` provisions GNOME and automatic login only after checking the
dedicated guest identity and storage preflight. It is test-image preparation, not a
production role. GNOME login/visual confirmation does not prove editor, portal, keyring
or physical hardware workflows. Golden-image cloning and full-install test lifecycle
remain unfinished.

## Controller integrity and recovery

[bootstrap.json](../locks/bootstrap.json) binds exact uv/Python archive and executable
hashes to [pyproject.toml](../pyproject.toml) and [uv.lock](../uv.lock). Downloaded
archives are checked before extraction; unsafe tar paths/links fail. Reused runtime
files and symlinks are checked against archive contents. Source builds during uv sync
are disabled. The environment and private tool log are under ignored `.workstation`.

Changed/corrupt archives, runtime files or locks fail visibly; there is no automatic
overwrite/repair of those integrity failures. Inspect private `.workstation/foundation.log`
for a failed sync/playbook. A normal rerun rechecks storage and integrity. Editing
dependency declarations requires an explicit lock refresh and new review, not a
workstation update that silently changes tracked pins.

## Keeping versions current

Before a deployment, find out what has moved:

```bash
make update/report        # or: just update report
```

It writes nothing. Every pinned version is compared with what upstream
publishes, and each row is one of:

| Status | Meaning |
|---|---|
| `current` | The pin is the published release |
| `update-available` | Upstream has moved on |
| `run-its-resolver` | Refreshed by its own resolver; `update/apply` runs it |
| `no-feed` | No version index exists to check against |
| `unreachable` | The check could not run — network, or a changed API |

Then apply what can be applied:

```bash
make update/apply         # or: just update apply
```

This re-pins the third-party release binaries (zed, obsidian), re-records the
repository signing keys, and then runs the catalogue check, the manifest check and
the tests. A bad pin fails there rather than on a machine.

### What `update/apply` does not touch

The controller's own toolchain in `locks/bootstrap.json` has no feed and is
listed so the gap stays visible: it is changed deliberately rather than on a sweep.
Command-line tools and runtimes are setup-dev-linux-wsl's to refresh.

VS Code extension versions are not pinned; they install at whatever the
Marketplace offers.

### After applying

```bash
make verify-static        # catalogue, manifest coverage, tests
make vm/clean-cycle       # destroy the guest, rebuild, apply, verify, reboot, repeat
```

Only then deploy. A refresh that has not been through the guest cycle has not
been tested — the pins changed, and nothing has installed them.

### GitHub rate limits

Checking every pinned version takes more than GitHub's **60 unauthenticated
requests an hour**: the report alone makes about fifteen, and re-pinning the 27
binaries makes one per tool. Without a token a full refresh runs out partway
and reports sources as unreachable that are merely unasked.

Supply a token and the limit becomes 5000 an hour:

```bash
GITHUB_TOKEN=... make update/apply
```

`gh auth token` is used when the environment has none — but a token kept in a
keyring the session cannot read comes back stale, and GitHub answers a stale
token with 403 rather than ignoring it. Both tools retry unauthenticated in
that case, so a bad token degrades to the ordinary limit instead of failing.

If you see `github-rate-limited-or-forbidden`, either wait for the hour to roll
over or export a working token.

### In a pipeline

```bash
python3 -B script/update-report --fail-on-update
```

Exits non-zero when anything is out of date or could not be checked, so a
scheduled job can tell you without anyone running it by hand.
