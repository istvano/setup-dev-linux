# F13 — Machine manifest

## Purpose

Reproduce this workstation's software on a fresh Ubuntu 26.04 machine from a
declarative manifest, so a new machine is built from a reviewed record rather
than from memory.

## Inputs

Two, and their precedence is fixed:

1. **This machine**, read by `script/inventory`. Ground truth for what is
   actually used.
2. **The Mac baseline** (`../mac-os-setup`), read by `script/inventory-review`.
   Contributes tools and structure this machine lacks. It is additive only: it
   never overrides an observation, and it is never a runtime dependency.

Both feed `catalogue/curation.json`, the reviewed decision record, which
renders to [docs/INVENTORY-REVIEW.md](../docs/INVENTORY-REVIEW.md).

## Contract

- `manifest/` is the single source of what a new machine gets. Nothing installs
  that is not declared there.
- Every third-party release binary carries a version, URL and SHA-256 before it
  may install. An unpinned entry is refused, not downloaded.
- Every third-party APT source declares a signing key or a Launchpad PPA.
  An unsigned source is refused.
- Ubuntu archive packages need no per-item source review. Third-party sources do.
- `install` never removes unrelated packages and never partitions or formats.
- `install` is repeatable: a second run on a correct machine changes nothing.
- `verify` reads the installed system and reports drift. It never repairs.

## Tasks

- T1 Read this machine into a raw snapshot, including packages installed
  outside APT. **Done** — `script/inventory`.
- T2 Merge with the Mac baseline into a reviewable document. **Done** —
  `script/inventory-review`, `docs/INVENTORY-REVIEW.md`.
- T3 Record the operator's decisions. **Done** — `catalogue/curation.json`,
  reviewed 2026-09-16.
- T4 Express the decisions as installable declarations. **Done** — `manifest/`.
- T5 Pin every third-party binary to a verified release. **Done** —
  `script/resolve-binaries`, `manifest/binaries.json`.
- T6 Prove no selection is lost between review and installation. **Done** —
  `script/check-manifest`.
- T7 Apply the manifest. **Done** — `ansible/repositories.yml`,
  `manifest-packages.yml`, `snaps.yml`, `binaries.yml`, `desktop.yml`.
- T8 Verify the applied result against the live system. **Done** —
  `vm/manifest_fixture.py`.
- T9 GPU delivery on physical hardware. **Unfinished** — cannot be exercised in
  a VM.
- T9b GNOME settings delivery. **Done** — `ansible/desktop.yml` via
  `workstation/desktop.py`, applied and read back in the guest. The rendered
  session remains unobserved.
- T10 Editor extensions and krew plugins. **Unfinished** — declared in
  `manifest/plugins.json`, no delivery role yet.
- T11 chezmoi delivery of the declared dotfiles beyond the existing shell/Git
  slice. **Unfinished**.

## Acceptance

| Case | Expectation |
|---|---|
| Unpinned binary | Refused before download |
| Unsigned third-party source | Refused |
| Tampered artifact | Checksum mismatch fails the install |
| Selection with no delivery | `check-manifest` fails |
| Manifest entry never selected | `check-manifest` fails |
| Second apply | No change |
| Reboot | Result survives |
| Verify on a fresh machine | Reports every absence, does not install |
| Package present but not runnable | Sampled execution check fails |

## Limits

A VM cannot prove GPU delivery, display or suspend behaviour. The guest has no
NVIDIA hardware, so the `gpu` group is excluded from VM acceptance and remains
proven only on the physical machine.
