# Implementation status

What works, what does not, and what is deliberately excluded. Decisions are in
[DECISIONS.md](docs/DECISIONS.md); what a new machine gets is in `manifest/`,
decided in [the inventory review](docs/INVENTORY-REVIEW.md).

Last verified 2026-09-17 by a clean VM cycle from a destroyed guest: 50 checks,
no failures. Evidence:
[TESTING.md](docs/evidence-log.md#machine-manifest-acceptance--2026-09-16).

## Done

Each item below has guest evidence, not just a passing unit test. The evidence
predates the host refactor (2026-11-26), when this repository still installed the
command line; the counts below include items setup-dev-linux-wsl now installs
([MOVED.md](docs/MOVED.md)). A host-only guest cycle has not been run yet.

- **Manifest delivery.** 87/87 APT packages for the twelve installed groups,
  27/27 pinned release binaries and 4/4 snaps installed on a pristine Ubuntu
  26.04 guest in 685s, verified by reading the installed system. 9 sampled
  binaries confirmed to run.
- **Signed sources.** 16 third-party APT repositories, each key normalised to a
  binary keyring and verified against a recorded fingerprint before use.
  Vendor packages that self-register a source are handled without breaking APT.
- **Pinned artifacts.** Every third-party binary carries a version, URL and
  SHA-256; unpinned entries are refused before download.
- **Repeatable apply.** Second apply after a reboot changed nothing; all
  verification groups passed again.
- **Coverage gate.** `script/check-manifest` fails when a reviewed selection has
  no delivery, when something unselected would install, or when a binary or
  repository key is unpinned.
- **GNOME settings.** 71 declared dconf keys across 27 sections applied and
  read back in the guest, extensions enabled exactly as declared (5 on, 2
  deliberately off), surviving a reboot and a second apply. `bootstrap verify`
  reports drift in them.
- **One package path.** `manifest/packages.json` is the only source of what
  installs. Every candidate is checked against the source the manifest declares
  — Ubuntu archive in a release pocket, or the declared repository's host — and
  each repository-sourced package is pinned to that host so a later upgrade
  cannot switch it. This caught google-cloud-cli silently replacing `kubectl`.
  `bootstrap verify` checks all 94 declared packages.
- **Editor extensions.** 17 VS Code extensions plus Cline, installed by `code`.
- **Verification covers the whole manifest.** `bootstrap verify` checks the
  pinned binaries, snaps and repository keys alongside packages, desktop
  settings and extensions. A raw binary is
  checked against its pinned digest, not merely for presence.
- **Update reporting.** `catalogue/update-sources.json` records where the
  host's pins come from (binaries, repository keys, controller); `make
  update/report` compares each with what upstream publishes and writes nothing.
  `make update/apply` re-pins the binaries and repository keys, then runs the
  checks.
- **Two entry points.** `justfile` and `Makefile` expose the same targets, kept
  in step by a parity test.
- Foundation and locked controller (carried forward, previously evidenced).

## To do

Ordered by what it blocks, not by subsystem.

### 1. Blocks trusting the result

- [ ] **Run the two-repository VM cycle.** `just vm clean-cycle` now applies the
  host with the firewall and hands off to setup-dev-linux-wsl
  (`tests/test_vm_harness.py` pins what it runs), but it has not run: it needs a
  Linux machine with KVM and network access. Then walk the manual items of the
  checklist in [TESTING.md](docs/TESTING.md#vm-acceptance-checklist): OpenSnitch UI
  autostart, UFW with a libvirt guest on virbr0, Ctrl-C during the bootstrap (exit
  130), and an interactive first run. Until then the firewall stage and the handoff
  have unit-test evidence only.
- [ ] **Headless selections have no guest evidence.** `--profiles gpu,firewall`
  runs no desktop, snap or VS Code stage in the unit tests; no guest cycle has
  run a headless selection (`script/test-manifest-vm --groups firewall,lab`
  is one).
- [ ] **VS Code extension versions are not pinned.** Unlike the binaries,
  extensions install at whatever version the Marketplace offers.
  Pinning them needs a resolver that does not exist yet, and a stale pin with no
  way to refresh it would be worse than none.

### 2. Provable only on the real machine

No VM work can close these.

- [ ] **GPU.** The `gpu` group — NVIDIA 595 open driver and matching modules —
  is excluded from VM acceptance because the guest
  has no NVIDIA hardware.
- [ ] **The desktop session.** Settings are written and read back, but nothing
  has rendered them: the guest is a server image. Appearance, keybindings, dock
  behaviour and suspend are unobserved. The manifest only *enables* extensions,
  relying on those shipped with `ubuntu-desktop`.
- [ ] **The first real install.** A fresh Ubuntu 26.04 install on the physical
  machine, `apply` with the handoff, and the [NEW-MACHINE.md](docs/NEW-MACHINE.md)
  steps, including credentials and data restored by hand, have not been walked.

### 3. Operational polish

Not needed to set up the machine; needed to live with the result.

- [ ] **No snapshot or rollback.** `update/report` says what would change and
  `update/apply` applies what it safely can, but nothing captures the previous
  state to return to if a refresh turns out badly.
- [ ] **No CI.** `verify-static` runs only when someone runs it.
- [ ] **Backup destination and schedule** remain manual, with no declared
  configuration.

### 4. Recorded, no action intended

- **Dependency closure is not individually checked.** Each named package is
  checked against its declared source; the resolver's dependencies are not. The
  guarantee rests on no undeclared source being configured and APT refusing
  unsigned ones. The previous whole-transaction simulation was removed because
  python-apt's manual marking misreported conflicts a real install resolves.

## Deliberately not doing

- **Moving disks or files between machines** (D017). Withdrawn 2026-09-16 and
  removed entirely 2026-11-26; fresh installs only.
- **Command-line tools, runtimes, the shell, dotfiles, chezmoi and Docker.**
  setup-dev-linux-wsl installs them (`--target linux`); see
  [MOVED.md](docs/MOVED.md). Removed from this repository 2026-11-26.
- **Employer tooling and the corporate proxy.** `eph-cli` and the proxy
  configuration stay manual and private.
