# Linux workstation architecture

Status: pure bootstrap plan, live standard-layout preflight, isolated locked controller
and initial Ansible foundation are implemented, with nine approved Ubuntu CLI/shell packages, immutable user tools, NVM/Node, Go, Rust, user uv/Python, OpenCode, Codex, Cline CLI, SDKMAN/JVM and
chezmoi shell/Git files.
Remaining application roles, transfer-handoff
verification, full independent workstation verification and production OS/migration
automation remain unfinished. Feature and guest results are in TESTING.md; catalogue
selection and foundation success are not full workstation readiness.

The transfer handoff currently has strict evidence parsing, exact offline tree
comparison, a fresh-home-baseline comparator, version-2 atomic publication and
a read-only adapter that binds its paths to storage inventory. A separate root-only command adds strict
rescue/emergency-state and output-parent checks, but has not run against actual
transferred guest disks. Initial live and package-checkpoint parsing have fixtures;
checkpoint publication, guard integration and transferred-disk boot acceptance
remain unfinished, so transfer apply stays blocked.

## Sources of truth

- `catalogue/capabilities.json`: normalized decisions, installation candidates,
  behavior ownership, verification requirements and source mappings.
- `profiles/target.json`: exact confirmed personal selection, including NVIDIA.
- `profiles/default.json`: reusable selection without GPU-specific capabilities.
- `config/*.example.json`: deliberately non-executable single/split/transfer inputs.
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
operations and ordering. chezmoi owns declared user files and shell initialization;
Ansible invokes it as the selected login user and never templates the same files.
SDKMAN owns Java/Mandrel/Maven/Gradle/Kotlin; NVM owns Node. uv owns user Python and
isolated tool/controller environments, never distribution Python. Go and pnpm use
verified versioned upstream distributions; rustup manages explicitly pinned Rust
versions. Runtime installation never rewrites shell files behind chezmoi.

Editor settings merge only owned keys. Preserve unrelated extensions and settings;
verify selected root pins and actual pack/dependency children. Selected agent CLI
installations must remain usable after NVM version switching; isolate npm-delivered
CLIs in a dedicated pinned prefix rather than the active project Node prefix.
Cline's CLI-only prefix contains its exact npm wrapper and Linux binary package;
its launcher invokes the managed default Node independently of active NVM
selection and disables Cline's startup updater. The published SDK packages are
not installed by this CLI-only role.

Host apps/interactive CLIs stay on the host. Project services and GPU dependencies
stay project-owned. OpenHands is deferred/optional; when explicitly enabled, it is
a separate workstation container: one project mount,
one private state directory, loopback ports, no Docker socket or whole-home credentials.
Test VMs are disposable infrastructure; isolated lab VMs are a separate use case.

## Selection and delivery are independent

`keep` enters the personal target; `optional` is disabled; `pending` is uninstalled
until its question is answered; `omit` never becomes a top-level install. Selection
files contain explicit IDs; profiles are organizational labels, not implicit expansion.
The default differs from target only by removal of entries in the GPU profile.
`nvtop` remains selected on CPU-only machines as a retained monitor installation.

Git, Git LFS, curl, jq, ripgrep and ShellCheck have reviewed Ubuntu delivery in
[the approval registry](../catalogue/approved-delivery.json). Other selected package/extension
delivery remains unverified. Candidate URLs and identifiers are research
leads, not download authorization or proven Ubuntu package names. Before implementing
an install task, verify release/architecture support, publisher, licence classification,
dependencies, update behavior and required integrity locks. A KEEP delivery gap blocks
that capability and whole-target completion; unrelated work can continue.

`provided-by` entries (mcedit) verify an executable from another package, not a second
installation owner. Installed metadata identifies scanner-utilities as Simple Scan and
SANE utilities. Ansible owns both packages through that single capability; actual
scanner backend/hardware readiness remains unverified. Docker's containerd capability
uses its selected vendor source, not a competing distro containerd installation.

The [source ledger](../catalogue/source-review.json) records pre-build observations and
proposed artifacts independently of catalogue delivery approval. Published digests,
observed downloaded hashes and publisher-matched hashes are distinct evidence states.
No operational installer consumes this review ledger as an approved lock. Review
release-specific licences, complete trust chains and dependency pins before promotion.
The [user environment](../profiles/user-environment.json) fixes Temurin 25 as default
and the confirmed shell plugins/helpers. Exact manager candidates remain separately
subject to source and workflow validation.

D013 selects reviewed current stable tool versions, including major upgrades, with
project adaptations as needed. Explicit runtime choices such as Temurin 25 still apply.
Historical Node/Maven/Mandrel versions in source observations are not mandatory pins.
Resolve exact stable inputs during review; do not implement floating latest downloads
or silent major updates. Supported-channel packages retain their declared source policy.
No existing projects are available for compatibility testing (D015). Initial acceptance
uses synthetic fixtures; it must not report actual project compatibility as passed.

Manual capabilities record readiness work; selecting them never runs credential
restoration, schedules backups or moves data. Optional DDC/MCP/AI requirements do not
block the initial target. Hardware checks only apply to selected features.

## JSON input and validation contract

Catalogue, selections and machine inputs use JSON; Ansible playbooks remain YAML.
Structural schemas are included. The distribution-Python standard-library loader and
semantic validator are shared by bootstrap plan/preflight/install/verify and static QA.
Development schema validation is separate from the dependency-free bootstrap path.
Do not create a second shell parser or an independently interpreted selection list.

All workstation commands require `--config PATH`. Resolve `selection_file` relative
to the configuration file; resolve private receipt paths the same way. No environment,
last-run state or default config silently overrides explicit input. Parse strictly:
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
be distinct and resolve to the configured physical role. Transfer requires split layout,
a data disk and a private receipt for affected mounts. Standard requires no receipt.
The personal transfer example selects separate /var/lib; split standard may omit it.
GPU feature none forbids GPU-profile IDs; nvidia requires both NVIDIA capabilities.

## Bootstrap ordering and read-only boundary

1. Use distribution `/usr/bin/python3` and standard `lsblk`/`findmnt` facilities to
   load/validate config and inspect platform, target user, disk identities and mounts.
   If these prerequisites are absent, return remediation; do not install them first.
2. Before APT, environment creation, logging to managed home, or any other managed
   write, verify every required mount and transfer handoff. On failure, report to
   stdout/stderr only. A matching mountpoint without physical identity is insufficient.
3. After the guard passes, install missing venv/APT bindings through signed Ubuntu
   packages, verify pinned uv/controller inputs, sync locked controller dependencies,
   and invoke Ansible with distribution Python for host APT modules.
4. Apply user configuration as the target user, reconcile selected runtimes and roles,
   and collect independent verification and manual/session/hardware outcomes.

`bootstrap plan` never downloads, invokes sudo, installs, writes caches/logs, or creates
an environment. It reports unreadable/unassessed hardware instead of acquiring privilege.
`verify` and update-report never repair/sync state or trigger runtime auto-install.
Use the existing interpreter/environment directly with bytecode writes disabled;
`uv run --locked` alone does not meet that boundary. Rich Ansible check mode may need
temporary controller state and scoped read privilege; label those separately and never
claim it has the pure bootstrap preview's zero-write contract.

## Transfer handoff evidence

The operator works offline/live, keeps independent backups, preserves the old tree,
and copies the fresh target's own /var/lib into a clean destination. Before mounting
it for normal boot, compare that destination to the fresh source, including dpkg state,
permissions, ACLs/xattrs and service ownership. Record private evidence tying the
comparison to the target installation, disk/UUID, time and intended mount roles.

Before first apply, verify this evidence plus current mount identities and package
state consistency with the fresh OS. An old /var/lib mounted at the correct UUID is
not proof of preparation. After packages legitimately change, do not compare against a
stale pre-install dpkg checksum: recheck current mounts and OS/package consistency,
while retaining original handoff evidence. Never trust a done marker alone.
Missing required filesystems must fail boot/mount activation and setup; no `nofail`
fallback for required /home or /var/lib. Never create replacement service data on root.
No handoff is needed for standard installs or /var/lib-on-root single-disk layouts.

## Commands and outcomes

Plan, install, rich preview, verify, desktop apply, update-report, update and snapshot
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

Invalid input stops before execution (2). For collected outcomes, failures take
precedence over incomplete; optional-disabled is not a failure. Successful preview
never means installed readiness. Reports retain passed, failed, deferred and
skipped-optional distinctions. Noninteractive commands never wait on prompts; supplied
config/privilege must suffice, otherwise return missing-input or incomplete status.

After preflight, managed outputs use the target user's XDG state directory under
`linux-os-setup` (default `~/.local/state/linux-os-setup`), directories 0700, files 0600.
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
