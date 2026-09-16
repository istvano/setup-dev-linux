# Linux workstation repository instructions

## What this repository is

A declarative record of this workstation and an installer that reproduces it on
a fresh Ubuntu 26.04 machine, plus a file migration for moving between
machines. `manifest/` is the single source of truth for what gets installed.

## Current state

Implemented and exercised in a disposable Ubuntu 26.04 guest: the bootstrap
plan/preflight/install/verify contract, the locked Ansible controller, third-party
repository configuration, manifest package and snap installation, pinned
release-binary installation with checksum verification, NVM/Node, SDKMAN/JVM,
user uv/Python, OpenCode/Codex/Cline CLIs, chezmoi shell and Git files, and the
file migration with its completeness proof.

Unfinished work is recorded in TASKS.md and nowhere else. Do not describe
unfinished work as done, and never equate static or fixture success with a
working workstation. GPU delivery and the GNOME desktop session are unproven:
the test guest has no NVIDIA hardware and runs a server image.

## Settled decisions

Ubuntu 26.04 LTS amd64/GNOME only. The repository is reusable; personal disk
identities, capacities, accounts and GPU hardware never become generic defaults.
D001–D016 and the capability matrix supersede stale Mac/raw-review proposals.

Decided 2026-09-16, in review with the operator:

- **Automated disk transfer is withdrawn.** No receipts, witnesses or machine
  binding. Files move by copy over SSH; see `specs/F14-file-migration.md`.
- **The manifest is decided by review, not inference.** `catalogue/curation.json`
  records each decision; `docs/INVENTORY-REVIEW.md` renders it.
- **Source review applies to third-party sources only.** Ubuntu archive packages
  install without a per-item review record.
- **Host Go and Rust toolchains are omitted.** That work runs in containers.
  The roles and locks remain, dormant. Do not reintroduce them into a profile.
- **SDKMAN owns every JVM installation**, including Gradle and Kotlin. No JVM
  tooling comes from APT.
- **starship replaces the oh-my-zsh agnoster theme.**
- SDKMAN and NVM remain selected; do not reintroduce mise. Rootful Docker-group
  membership for the selected user is authorised. No target disk encryption.

## Implementation boundaries

- Ansible owns system changes and sequencing; chezmoi owns declared user files.
  No competing file owners, package-install hooks or recursive bootstrap calls.
- Distribution Python for the initial loader/guard and managed-host APT modules.
  Keep the controller and user runtime environments separate.
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
- `migrate` never deletes on the destination, excludes credentials from the
  ordinary copy, and proves completeness rather than assuming it.
- Preserve unrelated user configuration; back up replacements privately. Never
  copy histories, credentials or whole application profiles into committed
  configuration.
- Containers use loopback-only published ports.
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
(`make vm/clean-cycle`), which
destroys the guest, rebuilds it from the verified image, applies the manifest,
verifies what landed, rehearses the migration, reboots and applies again.

When the manifest changes, re-run `script/check-manifest`: it is what stops a
reviewed selection from silently failing to reach installation.

Add behavioural checks for changed guarantees. Fixture-only tests do not
observe real filesystem or permission behaviour — the sealed-payload rename bug
in `python_user.py` passed every fixture test and failed on a live machine.

State which checks ran, what remains unverified, and any unresolved source or
workload prerequisites.

Do not commit, push, reset or discard unrelated work unless asked. Keep private
inputs, inventories, seeds, logs, backups and VM images out of Git.
