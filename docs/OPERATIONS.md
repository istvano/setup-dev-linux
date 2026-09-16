# Implemented operator commands

Current scope: configuration/preview, standard-layout storage preflight, isolated
controller, Ansible foundation, nine approved APT packages, immutable user tools,
chezmoi shell/Git files, NVM/Node, pnpm, Go, Rust, user uv/Python, OpenCode,
Codex, Cline CLI, SDKMAN, four selected JDKs, Maven, Gradle, Kotlin and Mandrel. Remaining
selected agent CLIs, application roles and full
workstation readiness are unfinished. Feature contracts and dependency order are in [specs](../specs/README.md).

| Command | Current behavior |
|---|---|
| `./bootstrap plan --config PATH --format json` | Pure standard-library preview; examples allowed and labelled; no downloads/sudo/writes |
| `./bootstrap preflight --config PATH --format json` | Live platform/user/disk/mount checks; examples rejected; no writes |
| `./bootstrap install --config PATH --format json` | Guard first, target user only, verified uv/Python archives and frozen controller graph, Ansible foundation and selected approved packages; reports remaining source/role failures |
| `./bootstrap verify --config PATH --format json` | Read-only preflight, approved package state and declared source/implementation gaps; no controller sync or repair |
| `sudo ./script/produce-transfer-handoff --config PATH --fresh-home PATH [--fresh-var-lib PATH] --format json` | Maintenance-only home-baseline and optional exact-`/var/lib` evidence publication; requires isolated rescue/emergency mode, exact transferred mounts and private output parents; does not enable bootstrap yet |
| `./script/test` | Strict static and behavioral suite in the existing Python environment |
| `./script/test-vm` | Copy reviewed repository sources to the dedicated guest and test foundation behavior |
| `./script/test-vm --controller` | Additionally acquire the isolated controller, apply foundation twice and run pinned QA/lint in the guest |
| `./script/test-vm --controller --packages` | Also test the six core CLI package workflows, repeat apply, missing-package drift and explicit recovery |
| `./script/test-vm --controller --packages --user-environment` | Also test shell/Git files, private backups, Node/pnpm, Go, Rust, user Python/uv, OpenCode, Codex, Cline CLI and SDKMAN/JVM synthetic workflows, selection and drift |
| `./script/test-vm --java-review` | Isolated four-JDK source/SDKMAN compile-run experiment; production role acceptance uses `--user-environment` |
| `./script/test-vm --sdkman-review` | Isolated source-pair experiment; does not install the production SDKMAN/JVM role |
| `./script/test-vm --controller --user-environment --reboot` | Verify a real guest reboot and repeat all currently implemented runtime/user acceptance; other application roles remain unfinished |

`install` currently **cannot report full success for the selected workstation**.
Controller success followed by exit 1 identifies selected source approvals still
missing; approved selected packages may have installed successfully. A private selection
containing only implemented capabilities with their required private settings can pass its operation, while `workstation_ready` remains
false because whole-workstation acceptance is unfinished. Other missing role
implementation is incomplete (exit 3). Invalid inputs use exit 2. Never run install
on the physical workstation merely to see what happens; use pure plan/preflight.

Use private, non-example configuration copied from a declared storage layout. Supply
real target-user and stable by-id disk identities, capacities and filesystem UUIDs.
Do not commit that input. Standard split with /var/lib on root is implemented.
Transferred-drive inputs remain incomplete until fresh-target evidence verification
is implemented; a receipt path alone cannot enable installation.

The handoff producer is intentionally separate from `bootstrap`. It runs only as
root after the operator has mounted the reviewed layout, retained a fresh
target-home baseline on the system root, retained a fresh `/var/lib` source there
when that separate mount is selected, and isolated the installed target into
rescue or emergency mode. It never copies, mounts, formats or stops services.
Its successful redacted report proves evidence publication only. Do not use it
for a production cutover until the live verifier and transferred-disk boot suite
recorded in F02-T6c/d are complete.

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
