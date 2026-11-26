# Implemented operator commands

Current scope: configuration/preview, standard-layout storage preflight, isolated
controller, Ansible foundation and the host manifest (repositories, packages, snaps,
pinned desktop binaries, VS Code extensions, GNOME settings). Command-line tools,
runtimes, the shell and Docker are installed by setup-dev-linux-wsl
([MOVED.md](MOVED.md)). Remaining application roles and full workstation readiness
are unfinished. Feature contracts and dependency order are in [specs](../specs/README.md).

| Command | Current behavior |
|---|---|
| `./bootstrap plan --config PATH [--profiles LIST] --format json` | Prints the `Profiles:` line and the stages the selection runs. Pure standard-library preview; examples allowed and labelled; no downloads/sudo/writes |
| `./bootstrap preflight --config PATH --format json` | Live platform/user/disk/mount checks and the host prerequisites `gpg` and `git`; examples rejected; no writes |
| `./bootstrap apply --config PATH [--profiles LIST] [--allow-ssh \| --no-allow-ssh] --format json` | `install` is an alias. Guard first, target user only, verified uv/Python archives and frozen controller graph, Ansible foundation and selected approved packages; reports remaining source/role failures |
| `./bootstrap verify --config PATH [--profiles LIST] [--allow-ssh \| --no-allow-ssh] --format json` | Checks the recorded profiles (`~/.local/state/setup-dev-linux/state.json`, or under `$XDG_STATE_HOME`) unless given. Read-only preflight, approved package state and declared source/implementation gaps; no controller sync or repair |
| `./script/test` | Strict static and behavioral suite in the existing Python environment |
| `./script/test-vm` | Copy reviewed repository sources to the dedicated guest and test foundation behavior |
| `./script/test-vm --controller` | Additionally acquire the isolated controller, apply foundation twice and run pinned QA/lint in the guest |
| `./script/test-vm --controller --reboot` | Verify a real guest reboot and repeat the foundation acceptance |

Firewall: the `firewall` profile runs `ansible/firewall.yml` (UFW default deny incoming, allow
outgoing, enabled; OpenSnitch from the Ubuntu archive, enabled, `DefaultAction` `allow` in
`/etc/opensnitchd/default-config.json`; its UI only with the desktop set). Incoming SSH is allowed
only with `--allow-ssh`. The choice is recorded as `firewall.allow_ssh` in the per-user
`state.json` (not in your config file); later runs without a flag reuse it, `--no-allow-ssh`
turns it off and removes the `OpenSSH` rule. `verify` reads `ufw status verbose` through
`sudo -n` (run `sudo -v` first, otherwise that check is `deferred`). Docker's published ports
bypass UFW; `verify` prints a notice when `docker` is present. Switching OpenSnitch to deny is
a later, manual decision.

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
