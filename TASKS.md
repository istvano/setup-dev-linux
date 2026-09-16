# Implementation status

What works, what does not, and what is deliberately excluded. Decisions are in
[DECISIONS.md](docs/DECISIONS.md); what a new machine gets is in `manifest/`,
decided in [the inventory review](docs/INVENTORY-REVIEW.md).

Last verified 2026-09-16 by a clean VM cycle from a destroyed guest. Evidence:
[TESTING.md](docs/TESTING.md#machine-manifest-and-file-migration-acceptance--2026-09-16).

## Done

Each item below has guest evidence, not just a passing unit test.

- **Manifest delivery.** 84/84 APT packages, 27/27 pinned release binaries and
  4/4 snaps installed on a pristine Ubuntu 26.04 guest in 794s, verified by
  reading the installed system. 9 sampled binaries confirmed to run.
- **Signed sources.** 16 third-party APT repositories, each key normalised to a
  binary keyring and verified against a recorded fingerprint before use.
  Vendor packages that self-register a source are handled without breaking APT.
- **Pinned artifacts.** Every third-party binary carries a version, URL and
  SHA-256; unpinned entries are refused before download.
- **Repeatable apply.** Second apply after a reboot changed nothing; all
  verification groups passed again.
- **File migration.** 168.1 GB / 389,426 files planned against the real home;
  18,162 files / 4.08 GB copied into the guest and proved complete by a second
  rsync pass finding nothing outstanding.
- **Credential separation.** 16,939 guest files hashed against 784 source
  credential digests; none arrived through the ordinary copy.
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
  the whole resolver transaction, dependencies included, must stay within
  declared sources and remove nothing. `bootstrap verify` checks all 94.
- **Two entry points.** `justfile` and `Makefile` expose the same targets, kept
  in step by a parity test.
- Foundation, locked controller, approved-package slice, chezmoi shell/Git
  files, NVM/Node, SDKMAN/JVM, user uv/Python, OpenCode/Codex/Cline CLIs
  (carried forward, previously evidenced).

## To do

### Declared but never applied

- [ ] **Editor extensions and krew plugins.** `manifest/plugins.json` declares
  17 VS Code extensions plus Cline and 6 krew plugins. No role installs them.
- [ ] **chezmoi dotfiles beyond shell and Git.** `manifest/dotfiles.json`
  declares 9 managed files; delivery covers shell and Git only. The starship
  and atuin configs are declared and undelivered — and starship is now the
  selected prompt (D019), so a new machine gets the binary without its config.
- [ ] **Agent CLIs `claude` and `copilot`.** Declared in
  `manifest/runtimes.json` with no lock and no install role.

### Verification gaps

- [ ] **`bootstrap verify` does not check binaries, snaps or repositories.** It
  verifies the 94 manifest packages (each from its declared source), user tools,
  runtimes and desktop settings. It does **not** verify the 27 pinned binaries,
  4 snaps or 16 repositories — only the VM fixture (`vm/manifest_fixture.py`)
  does. A clean `verify` therefore still does not mean the machine matches the
  manifest.
- [ ] **GPU.** The `gpu` group — NVIDIA 595 open driver, matching modules,
  nvidia-container-toolkit — is excluded from VM acceptance because the guest
  has no NVIDIA hardware. Unproven until the physical machine.
- [ ] **Desktop session.** The settings are written and read back, but nothing
  has rendered them: the guest is a server image with no GNOME session, so
  appearance, keybindings, dock behaviour and suspend are unobserved. The
  manifest also only *enables* extensions — it installs none, relying on those
  that ship with `ubuntu-desktop`.
- [ ] **Docker group membership.** Installed, but fresh-login group access is
  not verified.

### Superseded, still load-bearing

- [ ] **Dependencies are not individually checked against declared sources.**
  Each named package is, but the resolver's dependency closure is not: the
  guarantee rests on no undeclared source being configured and APT refusing
  unsigned ones. The previous whole-transaction simulation was removed because
  python-apt's manual marking misreported conflicts that a real install
  resolves.

- [ ] **Go and Rust roles are dormant, not removed.** Kept by decision on
  2026-09-16. They are unreachable — the config loader refuses to select an
  omitted capability — so `locks/go.json` (3.5 MB), `locks/rust.json`, the two
  runtime modules, apply scripts, playbooks, VM fixtures, tests and review docs
  sit unused, along with a `rust` entry in `catalogue/prerequisites.json`.
  Re-enabling means flipping both decisions back to `keep` and restoring them to
  a profile. Two places already assumed they were selected and had to be gated.

### Operations

- [ ] **update / update-report / snapshot.** `script/resolve-binaries` and
  `script/resolve-repository-keys` re-pin and detect key drift, but nothing
  reports what a re-pin *would* change before it is applied, and there is no
  snapshot or rollback.
- [ ] **CI.** No automated run of `verify-static`.
- [ ] **Backup destination and schedule.** Manual by design; no declared
  configuration.

### The move itself

- [ ] **Physical machine-to-machine migration.** Rehearsed in the VM against
  real data shapes at 4 GB; not yet run against the new workstation.
- [ ] **Credential and identity restoration.** Manual by design; the checklist
  in [NEW-MACHINE.md](docs/NEW-MACHINE.md) has not been walked end to end.
- [ ] **First boot on the new machine.** Nothing here has run on real hardware.

## Deliberately not doing

- **Automated disk transfer** (D017). Withdrawn 2026-09-16; files move by copy.
- **Host Go and Rust toolchains** (D019). That work runs in containers. The
  roles and locks remain in the repository, dormant.
- **aider** (D019). Not selected; its source and licence review stays an open gate.
- **Employer tooling and the corporate proxy.** `eph-cli` and the proxy
  configuration stay manual and private.
- **mise.** SDKMAN and NVM are selected. Do not reintroduce it.
- **OpenHands** (D014). Outside the initial installation.
