# Linux workstation implementation plan

Status: spec-driven implementation is authorized. Pure plan, standard storage preflight, locked controller, Ansible foundation and a disposable Ubuntu/GNOME VM are implemented. This document also specifies later work; see OPERATIONS.md for currently available commands and specs/README.md for feature tasks. Application roles, full workstation acceptance and production OS/data migration remain unfinished.

## Objective and scope

Configure fresh Ubuntu 26.04 LTS amd64 GNOME workstations from reusable profiles and per-machine configuration. CPU/RAM, GPU presence, disk capacities and device names must be detected or explicitly supplied; no transferred drive is required by default. [The current migration](migrations/current.md) is one example configuration. Installation must be repeatable, inspectable, recoverable after interruption and able to report incomplete work honestly.

Automate applications and settings. The user copies data using [the new-machine runbook](NEW-MACHINE.md). No automatic project transfer, home-directory cloning, credential extraction, database migration, partitioning or old-machine cleanup belongs in the workstation apply command.

Preserve [reviewed software selections](software-review.md) as raw decision evidence. Their older introductory hardware text is superseded by the confirmed target above. Use [tool selection](TOOL-SELECTION.md) for execution ownership and architecture rationale. [Confirmed decisions](DECISIONS.md) supersede older choices in the raw review.

## How reviewed choices become executable configuration

The JSON capability catalogue and structural schema are present. Each entry records: stable ID, title, purpose, source evidence, decision, profile, execution boundary, installation channel/identifier, supported OS/architecture, version policy, integrity fields where applicable, licence, conflicts, configuration owner, reboot/session needs and verification method.

Rules:

1. Explicit KEEP is included in the target workstation selection; explicit OMIT is excluded. OPTIONAL is available but disabled. REVIEW/unknown entries remain pending and visible. No optional or unresolved item becomes KEEP just because it was installed on the old machine.
2. Split grouped rows into tool IDs while preserving meaning. OBS Studio and Flameshot are retained; Kazam is not selected. Keep the overlapping editors, monitors, fonts and backup clients the user deliberately selected.
3. Interpret JetBrains OMIT from its evidence column. Thunderbird is now confirmed OPTIONAL and must not be installed by the target selection. Retain NVIDIA tooling for the confirmed RTX 4090 eGPU, and include nvtop with its retained monitor group.
4. Proposed baseline dependencies are explicit infrastructure additions, not mislabelled user KEEP selections. Mac-only integrations appear only as provenance replacement/omission mappings, never installable Linux entries. D006 and the capability matrix record the reviewed Mac additions, optional tools and explicit deferrals.
5. Existing application config does not establish active use. Inspect versions/source metadata without opening secret-bearing files. Never put private hostnames, remotes, connection definitions or inventories into the committed catalogue.
6. The target configuration is a set of approved IDs and options. Profiles organize them; selecting the target preserves every KEEP item even when it belongs to a normally optional profile. No silent exclusions due to default-profile composition.
7. Retained package unavailable on the selected OS means a visible unresolved dependency, not a successful skip. Finish unrelated implementation work while reporting the gap.

## Proposed repository layout

```text
bootstrap                      # minimal Bash launcher; plan is default
pyproject.toml / uv.lock         # isolated automation/test environment
ansible.cfg
requirements.yml               # pinned Ansible collections only
playbooks/workstation.yml
roles/                         # preflight, repositories, packages, security,
                               # docker, nvidia, virtualization, desktop,
                               # dotfiles, runtimes, editor, verification
catalogue/                     # JSON capability metadata + structural schema
profiles/                      # explicit JSON default/target selections
config/*.example.json          # single, split and transferred storage examples
locks/                         # bootstrap artifacts and selected release pins
chezmoi/                       # user configuration, no package-install hooks
vscode/extensions.list         # selected roots, exact versions
script/                        # CLI implementations and narrow helpers
tests/fixtures/                # fake home, hardware, package/service state
vm/                            # image lock, cloud-init and VM test driver
autoinstall/                   # later phase; examples/generator, no secrets
docs/                          # architecture, tools, operations, migration, tests
TASKS.md                       # unfinished work only
.github/workflows/             # pinned CI validation, added during implementation
```

Keep local configuration, `.venv`, generated inventories, logs, VM disks, tokens, backups and installer seeds out of Git. Document default private output locations and permissions. No runtime dependency on a checkout of the Mac repository: port focused templates/helpers with recorded provenance, not a symlink or wholesale fork.

## Per-machine configuration contract

Generic examples use system/data disk roles and placeholder identifiers, never source-specific device paths or assumed enumeration order. Disk identity resolution must be explicit and read-only: validate uniqueness, capacity, distinct devices for split layout and mount-role consistency. A device name is an observation, not an identity. Swapping Linux discovery order must not change which physical disk an installer may modify.

Create standard single-disk and standard split-disk examples plus a separate transferred-disk migration example. Keep personal hardware selections and real identifiers out of reusable defaults. GPU support is selected per machine; no NVIDIA profile is required for CPU-only setup. Generic here means reusable within the declared Ubuntu amd64 support boundary, not an untested promise of all Linux distributions/architectures.

## Optional storage-transfer mode

The planned configuration has `storage.mode: standard` by default, with `storage.mode: transferred-ssd` explicitly selected for the current migration. Disk layout is a separate per-machine selection. Both layouts have separate /boot, / and /home filesystems, plus EFI for UEFI boot. On one SSD, all three are on that disk and /var/lib is an ordinary directory on root. On two SSDs, /boot and / are on the configured system disk, while /home and an optionally selected separate /var/lib filesystem are on the configured data disk. The labels SSD 1/SSD 2 in this plan refer to these roles, not kernel discovery order. A separate /var/lib mount is optional in the schema, enabled for the planned two-disk machines and disabled for a single-disk machine. Standard installations can use either layout without importing an old drive. Do not detect a second SSD and assume transfer mode.

In standard mode, post-install setup verifies only the configured layout and proceeds without any old-drive identity, source-state inventory or transfer handoff. It does not partition or format disks. The later OS-install workflow provisions only explicitly selected disks using the machine's declared layout.

In transferred-ssd mode, preserve the data drive, verify its stable identity and prepared /home and /var/lib mounts, and require fresh-target handoff evidence before any bootstrap installation write, including APT prerequisites and managed-home logging. Matching mount UUIDs alone do not prove preparation. A missing drive or incomplete handoff fails visibly; never switch automatically to standard mode or write substitute service data onto root when a separate /var/lib mount is required. In the single-disk layout, /var/lib on root is explicitly correct and must pass verification.

Three non-operational JSON examples are present: standard single, standard split, and transferred split. P1 validates their operational equivalents and rejects example/placeholder input for install. Keep actual disk identities/UUIDs in private local configuration. No fresh install requires the historical NTFS partition or a 2 TB second disk.

## Planned operator commands

| Command | Contract |
|---|---|
| `./bootstrap plan --config PATH` | Validate target/options; list sources, packages, services, privilege changes, unresolved choices and manual steps. No sudo, installs, downloads or dotfile changes. Works before Ansible exists using minimal distribution facilities. |
| `./bootstrap install --config PATH` | Install verified automation prerequisites, run Ansible with scoped privilege, apply user state and record a redacted result. Prompt only for required secrets/privilege/input not supplied. |
| `./script/plan --check --config PATH` | Rich Ansible/chezmoi preview once dependencies exist; explicitly identify operations check mode cannot assess. |
| `./script/verify --config PATH` | Inspect package/config/service state; fail required unmet conditions. Report manual/session/hardware checks separately. Never install missing software. |
| `./script/desktop apply --config PATH` | Apply deferred GNOME settings in the actual user session, with backup/diff/readback. |
| `./script/update-report --config PATH` | Read-only report of installed/declared versions, source support, update availability and expiring pins. |
| `./script/update --config PATH` | Apply explicit reviewed candidates after revalidation, back up owned config and verify; no tracked pin edits, atomic rollback promise or OS major upgrade. |
| `./script/snapshot --config PATH` | Private local inventory, redacted by default. Never collect secret values. |
| `./script/test` | Strict local static/fixture gate. Required missing tool is a failure with remediation, not a green skip. |
| `./script/test-install` | Disposable-guest installation, reboot, rerun and verification; refuses non-test targets. |

Unknown arguments and conflicting choices fail closed. Installer logs distinguish failed, deferred, skipped-optional and passed outcomes. A pending required desktop/GPU action prevents a claim that the whole workstation is ready. Use `--format json` for versioned reports identifying config/selection digests and catalogue revision. Exit 0 complete, 1 failed, 2 invalid/missing input or bootstrap prerequisite, 3 incomplete; never wait for input without a TTY. All workstation commands require the same explicit config. See [architecture](ARCHITECTURE.md) for precedence and read-only boundaries.

## Implementation milestones

| Phase | Work and deliverables | Depends on | Exit evidence |
|---|---|---|---|
| P0 — Decisions/catalogue | Normalize all reviewed rows; reconcile portable Mac tools; write Linux AGENTS.md, architecture and initial ADRs; validate candidate package channels/licences | Existing documents | Every row maps to explicit decisions or a named unresolved question; no KEEP tool lost |
| P1 — Bootstrap foundation | Implement shared strict JSON validation, source-free plan, pre-write storage guard, trust bootstrap, pinned toolchain, initial independent verifier/reporting and CI | P0 selection/contracts and foundation delivery evidence | Clean Ubuntu guest reaches automation environment; unsupported OS/options and bad digest fail without applying |
| P2 — Packages/security | Repositories and package roles; core CLI and selected desktop apps; permissions, AppArmor/UFW/security-update policy; backups and conflict handling | P1 | Approved channels only, no mixed release, required binaries installed; second unchanged run reconciles cleanly |
| P3 — User environment | Port selected chezmoi files; preserve shell customizations; Git/signing config; runtime/vendor mapping; extension roots; GNOME/Remmina integration | P2 | Clean user plus existing-file fixture pass; runtime version tests and desktop settings readback pass |
| P4 — Containers/GPU/lab | Native Docker; loopback substrate; NVIDIA host/toolkit roles; GPU checks; selected VM tooling and isolated lab definition | P2; user integration from P3 | CPU container tests pass in VM; required eGPU tests pass on physical target or remain explicitly unverified |
| P5 — Operations/migration | Complete update report, snapshot and recovery operations; extend existing verification; align the new-machine runbook with retained software and discovered workloads | P3–P4 | Scripts do not transfer data; synthetic restore exercise succeeds; operator guide names remaining exact workload steps |
| P6 — Fresh-machine acceptance | Full selected install on pristine guest, reboot, repeat, interruption/drift/recovery and negative tests | P5 | Test evidence meets completion criteria below with no hidden skips |
| P7 — OS-install automation | Ubuntu Autoinstall template/generator, verified image, unencrypted layout with explicit disk mapping and protected seed handling | P6 | Destructive workflow succeeds only in disposable VM; explicit target checks reject ambiguous disk choices |
| P8 — Physical acceptance | Install on new workstation, guided manual restoration, target hardware checks and final readiness report | P6; P7 if blank-disk route chosen | Every required workflow verified; if transferring storage, old-system recovery backup retained through physical-drive cutover |

P0–P6 produce the primary deliverable: automated configuration of an already-installed Ubuntu Desktop. P7 extends it to OS installation; it must not delay delivering or weaken the safer post-install path. Source/licence/pin gates are resolved before each dependent role; unresolved application delivery does not prevent foundation work. No dates are promised before the package-source and hardware checks establish actual constraints.

### P1 bootstrap specifics

Require distribution Python and standard storage-inspection utilities for the initial read-only guard; if missing, return remediation without attempting an install. Run shared input/platform/user/mount/handoff validation before any managed writes. Only after it passes, provision missing venv/APT bindings through signed Ubuntu packages. Obtain uv through its reviewed version/digest lock without executing a downloaded installer. Create a repository-local managed Python environment compatible with the chosen ansible-core and linters, and sync strictly from uv.lock. Point managed-host Ansible modules to the distribution interpreter for APT bindings; keep the controller environment separate. Test this split on the actual Ubuntu release.

Never run the whole bootstrap as root. Capture the target user/home before privilege escalation. Require enough disk space/network and a supported release/architecture. Scope become to system tasks and use handlers for relevant service restarts. Record reboot requirements and resume by rerunning state reconciliation, not by trusting a stale done marker.

### P3 runtime and desktop specifics

Use NVM for Node and SDKMAN for Java/Mandrel/Maven/Gradle/Kotlin, as explicitly requested. Add Go/pnpm through verified versioned upstream distributions and Rust through pinned rustup/toolchains. Keep all selected agent CLIs independent of active project runtime switching. Use reviewed current stable versions (D013), retain Temurin 25 as default and Java 21/25 Microsoft/Temurin project choices, and test Mandrel/Maven/Node/uv with synthetic fixtures because no current projects exist (D015). Pin manager installation inputs and control self-update behavior; chezmoi owns shell initialization. Do not install mise as a replacement. A version needed only by an old project remains project-selected rather than silently becoming a global default.

Do not let either tool replace the whole VS Code settings file without preserving unrelated user settings. Pin extension roots and report pack children; omit extensions only when selected, never uninstall unsolicited. Preserve zsh custom functions through reviewed templates, not copied histories. Atuin stays local unless user selects synchronization. Implement supported telemetry opt-outs, Firefox/Chrome personal/work profile launchers, directory-specific private Git identity and Git LFS filters; signing stays disabled until a key is supplied.

Retain reviewed Linux VS Code extension families and selected agent integrations; validate Linux pins independently of historical Mac versions. Apply narrow GNOME settings with prior-value backup. Validate screenshot/recording tools under Wayland and the selected portals. For Remmina, prove one installation channel, required plugins, profile path and keyring behavior using throwaway connections. Do not restore real connection secrets in tests.

### P4 GPU and container specifics

Use the approved Ubuntu NVIDIA packaging path and document a tested driver branch; do not reproduce the old workstation's driver number or kernel package set blindly. Verify module/kernel compatibility, Secure Boot state and whether any MOK enrolment is actually needed. Do not disable Secure Boot or authorize arbitrary Thunderbolt devices to make tests green. Firmware/enclosure/security prompts remain explicit hardware steps.

Support the expected eGPU being disconnected: install selected software where safe, but report the required GPU check as pending. Distinguish intentional CPU-only operation from a failed required GPU. Test `nvidia-smi` and a pinned GPU container, then a small selected compute workload. Detect available memory; do not size VRAM workloads from system RAM capacity. Do not assume hotplug works safely under load.

The rootful daemon uses the privileged docker group for the selected workstation user, as authorized. Add membership without replacing existing groups and report the required logout/login; test non-sudo Docker access from the new session. Do not weaken socket permissions or give unselected users access.

Docker owns a shared network and rebuildable registry/build caches only; databases/queues/Kubernetes clusters remain project-owned. Detect route/subnet collisions before creating networks. Bind published ports explicitly to loopback, restrict daemon access and test actual exposure. No general-purpose agent container gets Docker socket or full-home credentials. OpenHands is deferred and optional (D014); future explicit enablement requires one project mount, private state and loopback-only ports. Install no shared stateful service stack.

### P7 installer specifics

Branch OS-install planning by selected storage mode. Standard mode validates the per-machine layout and explicitly selected installation disks, and needs no transferred drive or migration handoff. The default example must work on a fresh single-disk machine with separate /boot, / and /home, plus EFI; /var/lib remains on root. A split system/data example puts /boot and / on SSD 1 and /home plus separate /var/lib on SSD 2, and may provision a fresh second disk only when explicitly selected.

Transferred-ssd mode was withdrawn on 2026-09-16 (D017): there is no drive handoff, and the installer never partitions or formats any disk. Files move by copy, specified in [F14](../specs/F14-file-migration.md) and performed with [the new-machine runbook](NEW-MACHINE.md). The target machine's own hardware and storage facts are recorded in [the machine record](migrations/current.md), as one example and not a requirement.

Both modes use a verified official image, explicit disk identity/capacity checks and private generated seeds. No universal device-name erase default. Installer identity/password material stays private. Reuse the same workstation bootstrap after OS installation. Test standard installation on an empty disk, and transferred-ssd installation with a populated synthetic second disk that must remain unchanged by the installer.

Ubuntu documents desktop provisioning with Autoinstall; the Landscape integration is optional infrastructure not selected for this project. [Ubuntu provisioning documentation](https://ubuntu.com/landscape/docs/how-to-guides/ubuntu-installer/provision-a-workstation/)

## Validation design

| Layer | Required checks | Limit |
|---|---|---|
| Static/config | JSON schemas and shared semantics, duplicate/conflicting sources, exact KEEP selection coverage, invalid args, lock completeness, YAML/Ansible/shell/CI lint, secret scanning, Linux-only paths | Cannot prove install behavior |
| Fixtures | Pure plan writes nothing; storage guard precedes APT/home/venv/log writes; reject correctly mounted old /var/lib without fresh-target evidence; home-file collision backups; deferred sessions; wrong/missing hardware; broken digest; failed packages; interrupted run; negative verifier states | Mocks are not package/driver validation |
| Ubuntu system VM | Pristine install with systemd, sudo and real packages; reboot; strict suite; rerun; Docker build/Compose and network exposure; verify intentional drift fails | No physical eGPU/display proof |
| Ubuntu Desktop VM/session | User dotfiles, editor startup/config parse, GNOME readback, Remmina plugins/keyring with throwaway values, portals where available | Hardware capture/display behavior still needs target |
| Physical target | RTX 4090 enumeration/driver/container compute; eGPU connected/disconnected boot; sleep/wake; actual monitor DDC switching when selected; network/audio; representative dev workflow | Must record observed results, not infer from vendor support |
| Manual data restore | Synthetic ordinary-file and chosen database/VM restore examples; user performs real restoration | No automated access to production secrets/data |

Test the selected target profile in full, plus a minimal bootstrap profile and targeted feature combinations (GPU absent, session absent, existing config, standard single-disk storage with /var/lib on root, standard two-disk storage with required separate /var/lib, transferred-ssd present/missing/unprepared). Do not promise every distribution or combinatorial matrix. CI is static/fixture validation unless it explicitly runs full VMs. VM network access and nested virtualization requirements must be detected. Prefer a disposable guest with direct kernel container support; no Mac-style nested container VM is needed.

Second-run idempotency means no undesired package/file/service changes. Known refresh/read-only tasks are reported separately, not hidden by forcing zero change counts. After a failure, a rerun must converge without deleting user data. Verification must fail when an intentionally wrong port binding, missing package, unapproved source or changed owned setting is introduced.

## Completion criteria

- Every explicit KEEP entry is installed and verified, or completion is blocked by a clearly recorded unresolved dependency. No OMIT application is installed as a top-level selection; unavoidable dependency conflicts are exposed before apply.
- A pristine Ubuntu Desktop becomes configured through one documented entry point, with only specified privilege, reboot/session, identity and hardware interventions.
- Standard mode installs successfully without any transferred drive. Transferred-ssd mode preserves existing data and fails on missing/unprepared required mounts.
- A second run is safe and converges. Backups and recovery instructions exist for all owned configuration replacement paths.
- Required CI/static/fixture and VM checks pass without silent skips. Required physical checks are separately recorded before claiming target readiness.
- Docker/Compose and retained Kubernetes workflows work, ports satisfy policy, and any selected required GPU profile passes its verification workload. CPU-only configurations require no NVIDIA hardware; the current migration additionally validates its RTX 4090.
- Manual migration remains under operator control; no production data/secrets appear in Git, plans, logs or test artifacts.
- README, architecture, decisions, tools, operations and testing docs describe implemented behavior. TASKS contains only unfinished work.

## Remaining dependent gates

The [capability matrix](CAPABILITY-MATRIX.md) and D006 settle the baseline. Do not reopen
those choices as merely pending. Catalogue candidate delivery/licence/pins still need
validation before package roles. Scanner names and shell preferences are settled.
Current stable runtime inputs, synthetic native-image checks and the Docker credential
helper still need delivery/workflow evidence before dependent readiness checks. Explicitly pending applications stay
uninstalled; optional profiles stay disabled. Hardware identity/capacity, enclosure/link,
monitor paths and workload-specific backup/restore procedures remain local inputs.

P1 introduces verification; subsequent roles deliver their own checks. Follow the
[architecture contracts](ARCHITECTURE.md) and [testing specification](TESTING.md). P0
static validation does not claim that installer, package, desktop or hardware checks pass.
