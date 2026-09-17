# Implementation status

What works, what does not, and what is deliberately excluded. Decisions are in
[DECISIONS.md](docs/DECISIONS.md); what a new machine gets is in `manifest/`,
decided in [the inventory review](docs/INVENTORY-REVIEW.md).

Last verified 2026-09-17 by a clean VM cycle from a destroyed guest: 50 checks,
no failures. Evidence:
[TESTING.md](docs/TESTING.md#machine-manifest-and-file-migration-acceptance--2026-09-16).

## Done

Each item below has guest evidence, not just a passing unit test.

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
- **File migration.** 167.6 GB / 389,518 files planned against the real home;
  18,164 files / 4.08 GB copied into the guest and proved complete by a second
  rsync pass finding nothing outstanding.
- **Credential separation.** 2,195 source credential files compared by content
  against the guest; none arrived through the ordinary copy.
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
- **Dotfiles beyond shell and Git.** starship's configuration and its `init`
  line — the managed shell sets `ZSH_THEME=""`, so the file alone renders no
  prompt — atuin's configuration and `init`, and `.selected_editor`. A test
  asserts every file `manifest/dotfiles.json` declares is one something writes.
  `.npmrc` moved to never-managed: it carries an employer registry, an address
  and a TLS exception.
- **Editor extensions and kubectl plugins.** 17 VS Code extensions plus Cline,
  and 6 krew plugins, installed by the tools that own them. krew bootstraps
  itself into `~/.krew` first, because kubectl only finds plugins named
  `kubectl-<name>` on PATH.
- **Claude Code and Copilot CLI.** Pinned to exact npm tarballs by SHA-256 —
  which covers every file inside them — with the executable's own digest
  recorded, so replacement after install is detectable. npm is never invoked and
  no version is resolved at install time.
- **Verification covers the whole manifest.** `bootstrap verify` now checks the
  27 pinned binaries, 4 snaps and 16 repository keys alongside packages,
  runtimes, desktop settings, extensions, plugins and agents. A raw binary is
  checked against its pinned digest, not merely for presence.
- **Update reporting.** `catalogue/update-sources.json` records where all 25
  pinned versions come from; `make update/report` compares each with what
  upstream publishes and writes nothing. `make update/apply` re-pins the
  binaries, repository keys and npm agent CLIs, then runs the checks. Locks that
  carry per-file digests are named and left alone rather than swept.
- **Docker group membership.** `manifest/system.json` declares it,
  `ansible/system-groups.yml` grants it by appending, and verification tells the
  three states apart: not a member (the install did not finish), a member whose
  session predates the grant (log out and back in), and effective with the
  socket answering. Proven in the guest: deferred on first apply, passing after
  the reboot, `docker run hello-world` working without sudo.
- **Two entry points.** `justfile` and `Makefile` expose the same targets, kept
  in step by a parity test.
- Foundation, locked controller, approved-package slice, chezmoi shell/Git
  files, NVM/Node, SDKMAN/JVM, user uv/Python, OpenCode/Codex/Cline CLIs
  (carried forward, previously evidenced).

## To do

Ordered by what it blocks, not by subsystem.

### 1. Blocks trusting the result

- [ ] **VS Code extension versions are not pinned.** Unlike the binaries and the
  agent CLIs, extensions install at whatever version the Marketplace offers.
  Pinning them needs a resolver that does not exist yet, and a stale pin with no
  way to refresh it would be worse than none.

### 2. Provable only on the real machine

No VM work can close these.

- [ ] **GPU.** The `gpu` group — NVIDIA 595 open driver, matching modules and
  nvidia-container-toolkit — is excluded from VM acceptance because the guest
  has no NVIDIA hardware.
- [ ] **The desktop session.** Settings are written and read back, but nothing
  has rendered them: the guest is a server image. Appearance, keybindings, dock
  behaviour and suspend are unobserved. The manifest only *enables* extensions,
  relying on those shipped with `ubuntu-desktop`.
- [ ] **The move itself.** Rehearsed at 4 GB against real data shapes; the real
  run is 167.6 GB across 389,518 files. First boot, credential restoration and
  the [NEW-MACHINE.md](docs/NEW-MACHINE.md) checklist have not been walked.

### 3. Operational polish

Not needed to move; needed to live with the result.

- [ ] **No snapshot or rollback.** `update/report` says what would change and
  `update/apply` applies what it safely can, but nothing captures the previous
  state to return to if a refresh turns out badly.
- [ ] **Most locks are refreshed by hand.** 13 of the 25 watched sources are
  hand-curated payloads carrying per-file digests, so `update/apply` reports
  them and leaves them alone. Refreshing one means regenerating its manifest.
- [ ] **No CI.** `verify-static` runs only when someone runs it.
- [ ] **Backup destination and schedule** remain manual, with no declared
  configuration.

### 4. Recorded, no action intended

- **Dependency closure is not individually checked.** Each named package is
  checked against its declared source; the resolver's dependencies are not. The
  guarantee rests on no undeclared source being configured and APT refusing
  unsigned ones. The previous whole-transaction simulation was removed because
  python-apt's manual marking misreported conflicts a real install resolves.
- **Go and Rust roles are dormant, not removed**, by decision on 2026-09-16.
  They are unreachable: the config loader refuses to select an omitted
  capability. `locks/go.json` (3.5 MB), `locks/rust.json`, two runtime modules,
  apply scripts, playbooks, VM fixtures, tests and review docs sit unused, with
  a `rust` entry still in `catalogue/prerequisites.json`. Re-enabling means
  flipping both decisions back to `keep` and restoring them to a profile.

## Deliberately not doing

- **Automated disk transfer** (D017). Withdrawn 2026-09-16; files move by copy.
- **Host Go and Rust toolchains** (D019). That work runs in containers. The
  roles and locks remain in the repository, dormant.
- **aider** (D019). Not selected; its source and licence review stays an open gate.
- **Employer tooling and the corporate proxy.** `eph-cli` and the proxy
  configuration stay manual and private.
- **mise.** SDKMAN and NVM are selected. Do not reintroduce it.
- **OpenHands** (D014). Outside the initial installation.
