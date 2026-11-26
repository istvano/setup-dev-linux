# Linux workstation repository instructions

## What this repository is

The Linux host repository: a declarative record of this workstation's host and an
installer that reproduces it on a fresh Ubuntu 26.04 machine, then hands off to
setup-dev-linux-wsl (`--target linux`) for the command line. Fresh installs only:
nothing is copied from another machine. `manifest/` is the single source of truth
for what the host gets.

## Current state

This repository sets up the Linux host: the OS layer, drivers, desktop
applications, GNOME settings, snaps, VS Code and its extensions, zed, obsidian and
the firewall (UFW, OpenSnitch). The command line (CLI tools, runtimes, shell,
dotfiles, chezmoi, Docker, kubectl plugins) belongs to setup-dev-linux-wsl;
docs/MOVED.md records where each item went. Do not reintroduce command-line
installers here; `tests/test_host_only.py` refuses them. Decisions D022–D030 in
docs/DECISIONS.md describe the host role, profiles, firewall and handoff.

Implemented and exercised in a disposable Ubuntu 26.04 guest (before the host
refactor): the bootstrap plan/preflight/apply/verify contract, the locked Ansible
controller, third-party repository configuration, manifest package and snap
installation and pinned release-binary installation with checksum verification.
Implemented with unit-test evidence only: host profiles, the per-user state file,
the firewall stage and the handoff; the VM cycle that exercises them has not run.

Unfinished work is recorded in TASKS.md and nowhere else. Do not describe
unfinished work as done, and never equate static or fixture success with a
working workstation. GPU delivery and the GNOME desktop session are unproven:
the test guest has no NVIDIA hardware and runs a server image.

## Settled decisions

Ubuntu 26.04 LTS amd64/GNOME only. The repository is reusable; personal disk
identities, capacities, accounts and GPU hardware never become generic defaults.
D001–D016 and the capability matrix supersede stale Mac/raw-review proposals.

Decided 2026-09-16, in review with the operator:

- **No file or disk movement.** No machine binding and no file copy (removed
  2026-11-26).
- **The manifest is decided by review, not inference.** `catalogue/curation.json`
  records each decision; `docs/INVENTORY-REVIEW.md` renders it.
- **Source review applies to third-party sources only.** Ubuntu archive packages
  install without a per-item review record.
- **The command line moved to setup-dev-linux-wsl** (2026-11-26): runtimes,
  shell, dotfiles, Docker and its group, the NVIDIA container toolkit. This
  repository no longer runs chezmoi. No target disk encryption.

## Implementation boundaries

- Ansible owns system changes, sequencing and the desktop files the host owns.
  No competing file owners, package-install hooks or recursive bootstrap calls.
- Distribution Python for the initial loader/guard and managed-host APT modules.
  Keep the controller environment isolated from the operator's tools.
- Verify storage before APT prerequisites, environments, logs or managed-home
  writes. Post-install apply never partitions, formats or moves production data.
- Run user tools as the explicit target user, never by changing HOME under sudo.
  Scope privilege to system tasks; never run the whole bootstrap as root.
- Pure preview never downloads, uses sudo, writes caches or syncs environments.
  Verification reports drift independently and never repairs it.
- All commands take an explicit `--config PATH` and emit consistent redacted
  outcomes. Missing tools and required failures are never successful skips.
- Every third-party binary is pinned to a version, URL and SHA-256 before it may
  install; every third-party APT source declares a signing key or PPA. No
  curl-pipe-shell. Ubuntu archive packages need neither.
- Preserve unrelated user configuration; back up replacements privately. Never
  copy histories, credentials or whole application profiles into committed
  configuration.
- Containers this repository publishes (none today) bind their ports to loopback.
  Containers run through setup-dev-linux-wsl's Docker keep Docker's default: by the
  operator's choice their published ports stay reachable from the network, ahead
  of UFW (D027 in docs/DECISIONS.md).
- Credentials, VPN profiles, backup destinations, data restoration and physical
  hardware interventions remain manual. Report incomplete requirements honestly.

## Validation

For catalogue, manifest, schema, selection or workflow changes:

```bash
python3 -B script/check-catalogue    # catalogue, schemas, selections, generated docs
python3 -B script/check-manifest     # every selection delivered, every binary pinned
python3 -B -m unittest discover -s tests
```

or `just verify-static`. Guest acceptance is `just vm clean-cycle`
(`make vm/clean-cycle`), which destroys the guest, rebuilds it from the verified
image, applies the host and hands off to setup-dev-linux-wsl (network required),
verifies both, reboots and applies again. It needs Linux with KVM; on any other
host, test harness changes with `tests/test_vm_harness.py` and say the guest run is
still owed. The manual checklist is in docs/TESTING.md.

When the manifest changes, re-run `script/check-manifest`: it is what stops a
reviewed selection from silently failing to reach installation.

Add behavioural checks for changed guarantees. Fixture-only tests do not
observe real filesystem or permission behaviour — a sealed-payload rename bug in
the former user-Python role passed every fixture test and failed on a live machine.

State which checks ran, what remains unverified, and any unresolved source or
workload prerequisites.

Do not commit, push, reset or discard unrelated work unless asked. Keep private
inputs, inventories, seeds, logs, backups and VM images out of Git.
