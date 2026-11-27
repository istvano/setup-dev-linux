# Linux workstation architecture

Status: pure bootstrap plan, live standard-layout preflight, isolated locked controller
and initial Ansible foundation are implemented, with the host manifest (signed third-party
APT sources, packages, snaps, pinned desktop binaries, VS Code extensions, GNOME settings),
host profiles, the firewall stage and the handoff to setup-dev-linux-wsl. The command
line — CLI tools, runtimes, shell, dotfiles, chezmoi, Docker — moved to
setup-dev-linux-wsl on 2026-11-26 ([MOVED.md](MOVED.md)). The firewall stage and the
handoff have unit-test evidence only; the guest cycle that runs them is in
[TESTING.md](TESTING.md). Remaining application roles, full independent workstation
verification and production OS automation remain unfinished. Catalogue selection and
foundation success are not full workstation readiness.

## Two repositories per Linux machine

This repository sets up the host; setup-dev-linux-wsl (`--target linux`) sets up the
command line, the same split as setup-dev-win and setup-dev-linux-wsl on Windows
(D022–D030 in [DECISIONS.md](DECISIONS.md)). Each file and package has one owner:

| Owner | Owns |
|---|---|
| setup-dev-linux (Ansible and the controller) | Third-party APT sources and keys for host applications, the NVIDIA driver, desktop packages, snaps, pinned desktop binaries, GNOME settings, VS Code extensions, UFW, OpenSnitch, the per-user state file |
| setup-dev-linux-wsl | CLI tools, runtimes (mise, uv), the shell, dotfiles and chezmoi, Docker and the `docker` group, the NVIDIA container toolkit, Claude Code's APT source |

The one shared file is `/etc/apt/keyrings/anthropic.asc`, byte-identical in both
repositories, so claude-desktop's and Claude Code's sources carry one `Signed-By`.

A run of `./bootstrap apply` is, in order:

| Stage | Runs when | What |
|---|---|---|
| `foundation` | always | Distribution assertions (`foundation.yml`) |
| `record-selection` | always | The host profiles (and an explicit SSH choice) into per-user state, before anything installs |
| `packages` | always | `repositories.yml`, `manifest-packages.yml`, `snaps.yml` with the desktop set, `binaries.yml` when a selected group has binaries |
| `system-groups` | always | `system-groups.yml` |
| `plugins` | `dev-gui` | VS Code extensions (`plugins.yml`) |
| `desktop` | `desktop` | GNOME settings (`desktop.yml`) |
| `firewall` | `firewall` | UFW and OpenSnitch (`firewall.yml`), then the UI default as the target user |
| `handoff` | not `--no-handoff`, host stages passed | Clone or update `~/workspace/setup-dev-linux-wsl`, run its `./bootstrap apply --target linux` |

`plan` lists the same stages as `stage:<id>` checks without running any.

## Host profiles and per-user state

`profiles/host.json` maps each host profile to manifest groups (`base` always); the
desktop set (`desktop,media,productivity,ai,network,dev-gui`) decides whether a run is
headless (D025). Selection order: `--profiles`, else the recorded choice, else the
default; every report carries `Profiles:` and `Profiles source:`. The record is
`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json`: one JSON object of
named keys (`profiles`; `firewall` with `allow_ssh` and `opensnitch_ui_seeded`; an
`opensnitch_seeded` left by an earlier version is ignored), directory 0700, file 0600, owner and symlink checks on every
read and write, atomic replace. A state file that exists but fails a check stops the run;
it is never treated as absent. The operator's configuration file is never rewritten.

## Firewall

UFW: deny incoming, allow outgoing, enabled; SSH (port 22, UFW's `OpenSSH` profile from
openssh-server) only with `--allow-ssh`, recorded and kept; over SSH, apply refuses until
a choice exists. With `lab`, DHCP, DNS and routing on `virbr0` for libvirt's guests.
OpenSnitch: daemon always with `firewall`, in the allow mode Ubuntu's package ships (its
configuration is never written), UI with the desktop set, whose per-user allow default
is seeded once and never rewritten (D026). Docker, installed by setup-dev-linux-wsl, writes
its own packet-filter rules ahead of UFW's, so published ports stay reachable (D027);
`verify` notes it when `docker` is present and the `firewall` profile is selected.

## Handoff

As the target user, never root: clone or update `~/workspace/setup-dev-linux-wsl`
(git and the bootstrap run without any `GIT_*` variable; origin read with
`git config --get remote.origin.url`; a foreign or dirty clone stops the run untouched), resolve `--linux-ref` with `rev-parse --verify`, `checkout --detach`
once, run `./bootstrap apply --target linux` attached to the terminal. `--profiles` is
passed only with `--cli-profiles`; `--cli-git-name`/`--cli-git-email` add
`--non-interactive`. Its exit code becomes the run's when it fails. `verify` runs its
`script/verify --target linux` as `cli:verify` (D029).

## Sources of truth

- `manifest/`: what the host installs (packages, repositories, snaps, binaries,
  GNOME settings, VS Code extensions, groups); the delivery authority (D018).
- `profiles/host.json`: host profiles, their manifest groups, the default and the
  desktop set.
- `catalogue/capabilities.json`: normalized decisions, installation candidates,
  behavior ownership, verification requirements and source mappings.
- `profiles/target.json`: exact confirmed personal selection, including NVIDIA.
- `profiles/default.json`: reusable selection without GPU-specific capabilities.
- `config/*.example.json`: deliberately non-executable single/split inputs.
- `docs/DECISIONS.md`: user decisions and policy; later decisions supersede raw review.
- `docs/software-review.md`: immutable original evidence, hashed in the catalogue.
- `docs/CAPABILITY-MATRIX.md`: human-readable catalogue/mapping projection.

Mac provenance is commit `3134472` (full hash in catalogue). Mac profile declarations,
including commented options, are evidence of capability, not authorization to install.
Mac-only tokens exist only in provenance mappings, never as Linux installation entries.
No runtime command reads the Mac checkout. Port focused configuration with provenance;
do not copy its package hooks or its platform-specific instructions.

## Execution ownership

Ansible owns packages, privileged files, services, group membership, GNOME session
operations, the desktop files the host owns, and ordering. uv owns the isolated
controller environment, never distribution Python. This repository does not run
chezmoi: setup-dev-linux-wsl owns it on the machine (one source, one state file),
together with every command-line tool, runtime, the shell and Docker.

Editor settings merge only owned keys. Preserve unrelated extensions and settings;
verify selected root pins and actual pack/dependency children.

Host GUI applications stay on the host. Project services and GPU dependencies stay
project-owned. Test VMs are disposable infrastructure; isolated lab VMs are a
separate use case.

## Selection and delivery are independent

`keep` enters the personal target; `optional` is disabled; `pending` is uninstalled
until its question is answered; `omit` never becomes a top-level install. Selection
files contain explicit IDs; profiles are organizational labels, not implicit expansion.
The default differs from target only by removal of entries in the GPU profile.
`nvtop` remains selected on CPU-only machines as a retained monitor installation.

[The approval registry](../catalogue/approved-delivery.json) records reviewed Ubuntu
delivery; it is empty since the archive command-line tools it covered (Git, Git LFS, curl,
jq, ripgrep, ShellCheck, zsh) moved to setup-dev-linux-wsl. Selected package/extension
delivery remains unverified. Candidate URLs and identifiers are research
leads, not download authorization or proven Ubuntu package names. Before implementing
an install task, verify release/architecture support, publisher, licence classification,
dependencies, update behavior and required integrity locks. A KEEP delivery gap blocks
that capability and whole-target completion; unrelated work can continue.

`provided-by` entries verify an executable from another package, not a second
installation owner. Installed metadata identifies scanner-utilities as Simple Scan and
SANE utilities. Ansible owns both packages through that single capability; actual
scanner backend/hardware readiness remains unverified.

The [source ledger](../catalogue/source-review.json) records pre-build observations and
proposed artifacts independently of catalogue delivery approval. Published digests,
observed downloaded hashes and publisher-matched hashes are distinct evidence states.
No operational installer consumes this review ledger as an approved lock. Review
release-specific licences, complete trust chains and dependency pins before promotion.
Runtimes, the shell and its plugins, and user configuration are setup-dev-linux-wsl's
(see [MOVED.md](MOVED.md)); this repository no longer runs chezmoi.

D013 selects reviewed current stable tool versions, including major upgrades, with
project adaptations as needed. Resolve exact stable inputs during review; do not
implement floating latest downloads or silent major updates. Supported-channel packages retain their declared source policy.
No existing projects are available for compatibility testing (D015). Initial acceptance
uses synthetic fixtures; it must not report actual project compatibility as passed.

Manual capabilities record readiness work; selecting them never runs credential
restoration, schedules backups or moves data. Optional DDC/MCP/AI requirements do not
block the initial target. Hardware checks only apply to selected features.

## JSON input and validation contract

Catalogue, selections and machine inputs use JSON; Ansible playbooks remain YAML.
Structural schemas are included. The distribution-Python standard-library loader and
semantic validator are shared by bootstrap plan/preflight/apply/verify and static QA.
Development schema validation is separate from the dependency-free bootstrap path.
Do not create a second shell parser or an independently interpreted selection list.

All workstation commands require `--config PATH`. Resolve `selection_file` relative
to the configuration file. Explicit input always wins: without `--profiles` the recorded
host profiles apply, else the default, and every report says which
(`Profiles source:`). No environment or default config silently overrides explicit input. Parse strictly:
reject duplicate JSON keys, unknown fields/IDs, duplicate selected IDs, contradictory
features, and unsupported schema versions. Reject pending/omit IDs. The committed default/target selections contain no optional
IDs; another machine may explicitly select optional IDs in its private selection file.
Never enable optional capabilities by implicit profile expansion.

Structural example validation permits null capacity and REPLACE placeholders for
review only. Every example has `example_only: true`; install must reject it. Operational
inputs require false, a real existing non-root target user, explicit positive minimum
capacities, non-placeholder distinct stable disk identities and verified UUIDs.

Semantic storage rules: single requires only system disk, no separate /var/lib and
/home on system. Split requires distinct system/data disks, /home on data and optional
/var/lib on data. /boot/efi, /boot and / are always on system. Required mount UUIDs must
be distinct and resolve to the configured physical role. Split standard may omit a separate /var/lib.
GPU feature none forbids GPU-profile IDs; nvidia requires both NVIDIA capabilities.

## Bootstrap ordering and read-only boundary

1. Use distribution `/usr/bin/python3` and standard `lsblk`/`findmnt` facilities to
   load/validate config and inspect platform, target user, disk identities and mounts.
   If these prerequisites are absent, return remediation; do not install them first.
2. Before APT, environment creation, logging to managed home, or any other managed
   write, verify every required mount. On failure, report to
   stdout/stderr only. A matching mountpoint without physical identity is insufficient.
3. After the guard passes, install missing venv/APT bindings through signed Ubuntu
   packages, verify pinned uv/controller inputs, sync locked controller dependencies,
   and invoke Ansible with distribution Python for host APT modules.
4. Check the host prerequisites `gpg` and `git` on the system path; a missing one
   fails with `prerequisite:<program>` before any write.
5. Run the selection's host stages (packages, snaps, binaries, groups, VS Code
   extensions, GNOME settings, firewall) and collect independent verification and
   manual/session/hardware outcomes.
6. Hand off to setup-dev-linux-wsl, unless `--no-handoff`, once the host stages passed.

`bootstrap plan` never downloads, invokes sudo, installs, writes caches/logs, or creates
an environment. It reports unreadable/unassessed hardware instead of acquiring privilege.
`verify` and update-report never repair/sync state or trigger an install.
Use the existing interpreter/environment directly with bytecode writes disabled;
`uv run --locked` alone does not meet that boundary. Rich Ansible check mode may need
temporary controller state and scoped read privilege; label those separately and never
claim it has the pure bootstrap preview's zero-write contract.

## Commands and outcomes

Plan, apply, rich preview, verify, desktop apply, update-report, update and snapshot
all consume the same explicit config. Test-suite commands are repository-scoped;
test-install additionally requires test-target identity and guest configuration.
Text output is default; `--format json` writes a versioned redacted report to stdout.
Reports include command, config digest, catalogue revision, selection digest, aggregate
outcome, per-capability status/reason and required next steps; exclude config contents,
secrets, private identities and disk serials. No implicit report-file writes for preview.

| Exit | Meaning |
|---|---|
| 0 | Requested operation/check completed; all assessed required conditions passed |
| 1 | Failed operation or required verification, including selected delivery failure |
| 2 | Invalid/missing input, unsupported platform/schema or missing bootstrap prerequisite |
| 3 | Incomplete manual/session/reboot/hardware requirement or required unassessed check |
| 130 | Interrupted (Ctrl-C) during a host stage or the handoff; one line, no traceback; re-running is safe |

A missing host prerequisite (`gpg`, `git`) fails preflight with exit 1. When the handoff
fails, the run exits with setup-dev-linux-wsl's exit code and outcome `failed`; the
`handoff` check carries it, so an exit of 2 or 3 there is not this table's meaning.

Invalid input stops before execution (2). For collected outcomes, failures take
precedence over incomplete; optional-disabled is not a failure. Successful preview
never means installed readiness. Reports retain passed, failed, deferred and
skipped-optional distinctions. Noninteractive commands never wait on prompts; supplied
config/privilege must suffice, otherwise return missing-input or incomplete status.

Recorded choices live in the target user's
`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json` (directory 0700, file
0600). The controller environment and its private log are under the clone's ignored
`.workstation/` (0700; the log 0600).
Backups may contain sensitive configuration: private locally, never committed. Snapshot
is an explicit private output operation, redacted by default, never secret extraction.

## Updates and recovery

update-report queries upstream read-only and reports installed/declared/candidate
versions, supported channels and pin expiry. Missing network/source data is unassessed,
not 'up to date'. Applying an update requires an explicit reviewed candidate set bound
to config/selection and installed state. Revalidate immediately before mutation; stale
candidates require a new review. Do not edit tracked pins or perform OS major upgrades
inside workstation update. Pin changes are separate repository changes with validation.

APT supported-security-channel and documented Snap/app refresh policies may advance
versions; verification checks allowed sources/policies rather than treating every newer
version as drift. Exact pinned artifacts/extensions do require the declared version.
No automatic extension update may silently defeat selected root pins. Record which
apps refresh outside the reviewed update flow and test the relevant effective settings.

Back up owned configuration before replacement and preserve restoration instructions.
Package changes across APT/Snap/upstream managers are not atomic. Report partial updates;
document package repair/reinstall or restore from independent backup where needed.
Do not promise that restoring configuration rolls back binaries or package databases.

## Implementation gates

P1 creates shared validation/reporting and the initial independent verifier. P2–P4 add
verification with each role, including negative drift checks. P5 completes update,
snapshot and recovery operations; it does not introduce verification for the first time.
P6 proves pristine post-install configuration. P7 adds OS installation; P8 proves
selected physical workflows. [Testing specification](TESTING.md) defines acceptance.
