# Confirmed project decisions

User-confirmed decisions, 2026-09-12. These supersede conflicting proposals and older hardware/selection notes in the preserved software-review.md. They guide future implementation; no host installation, group modification or disk operation has been performed.

## D001 — Target and automation scope

Initial supported OS: Ubuntu 26.04 LTS amd64 with GNOME. Machine-specific hardware and optional features are configuration inputs; the first target machine is recorded in [its own note](migrations/current.md). Automate applications and settings; data restoration stays operator-run, following [the new-machine runbook](NEW-MACHINE.md).

## D002 — Privileged Docker group

Use rootful Docker Engine with the selected workstation user in the privileged `docker` group. This access model is explicitly selected and requires no additional design approval. Add supplementary membership without replacing existing groups, verify socket group/permissions and test non-sudo access after a fresh login. Group access is root-equivalent; do not add unrelated accounts, loosen socket permissions, expose a TCP daemon socket or pass the socket into general-purpose agent containers.

## D003 — SDKMAN and NVM

Use SDKMAN for Java distributions, Maven and selected JVM tools, and NVM for Node.js. Preserve project version selection and existing vendor/native-image requirements. Do not migrate these workflows to mise; mise is not part of the selected baseline. uv remains responsible for Python environments and the isolated automation toolchain.

Chezmoi owns shell initialization. Install manager artifacts through reviewed, pinned inputs; vendor bootstrap scripts must not independently rewrite managed shell files. SDKMAN documents noninteractive installation controls and a self-update setting; configure these deliberately, while still verifying fetched code before execution. [SDKMAN installation](https://sdkman.io/install/)

NVM supports per-user, per-shell operation and manual installation. Use its reviewed pinned release rather than a floating installer. [NVM documentation](https://github.com/nvm-sh/nvm/blob/master/README.md)

## D004 — Thunderbird optional, not installed

The user clarified `OPTUINAK` as OPTIONAL. Exclude Thunderbird from the target install. Do not uninstall it from the current machine or delete its mail/profile. Optional recovery guidance can remain in the migration document.

## D005 — Configurable disk roles and optional transfer

The repository is reusable across machines. Device names, CPU/RAM capacities, GPU models, historical partitions and the existence of a transferred drive are not universal requirements. [The machine record](migrations/current.md) keeps those facts separate.

Select a layout and assign roles through per-machine configuration:

| Layout | System role | Data role | /var/lib |
|---|---|---|---|
| Single disk | EFI, separate /boot, / and /home | Not required | Ordinary directory on / |
| Split system/data | EFI, separate /boot and / | /home and optionally a separate /var/lib filesystem | Separate when selected; otherwise directory on / |

A separate /var/lib filesystem is optional. It is selected for the user's two-disk machines and disabled for the single-disk layout. Missing a separate mount is not drift when the selected layout keeps /var/lib on root. Swap is a file on root; its size and any hibernation requirement depend on the machine.

System/data are logical roles, not enumeration order. Never hardcode /dev/nvme0n1 or /dev/nvme1n1, infer a role from a partition number, or assume NVMe rather than another supported block-device transport. Match each required role against explicit, private stable disk identifiers and validate actual capacity/filesystem state. Reject ambiguous identities or the same physical disk assigned to both roles in a split layout. Configure mounts with verified filesystem UUIDs, stored only in private machine input.

The planned configuration separates layout, whether /var/lib has its own filesystem, and transfer mode:

- `storage.mode: standard` is the reusable default. There is no source-drive requirement, migration state or transfer handoff. Post-install apply validates the selected existing layout; it never partitions disks.
- `storage.mode: transferred-ssd` is optional. Explicitly identify the preserved data disk and affected mount roles. Before full apply, require manual preparation of those selected mounts. Never format or repartition a transferred disk, reclaim its unused partitions, or import old OS state automatically. Missing or unprepared required storage fails visibly; no automatic mode fallback.
- The current migration selects transferred-ssd plus split system/data and separate /var/lib. A fresh two-disk installation selects standard plus split layout. A fresh single-disk installation selects standard plus single layout and /var/lib on root. No mode is inferred from merely detecting a second disk.

These keys describe a planned schema, not a working interface. Actual capacities and identifiers belong to local configuration. No target disk encryption is selected. Standard OS installation, when implemented, uses only explicitly selected installation disks. Transfer mode preserves the identified data disk even if Linux enumerates it before the system disk. Verify this using synthetic disks with swapped discovery order.

User data migration stays manual. Test all three normal scenarios and their missing/ambiguous-disk failure cases. Never require an old NTFS partition, a particular disk size or the original workstation to complete a standard fresh install.

## D006 — Confirmed workstation selection

User-confirmed during plan review, 2026-09-12. The initial target adds the portable Mac
CLI/validation/backup set, full Kubernetes tool set and six krew plugins, Ghostty/VS Code/
Zed/Neovim and terminal font, Codex/Claude Code/OpenCode/Cline/aider/OpenHands, Go/Rust/pnpm/
Gradle/Kotlin, AWS/Azure/OpenTofu/Terragrunt/terraform-docs, QEMU/KVM/libvirt/virt-manager,
and OpenVPN/NetworkManager integration. [Capability matrix](CAPABILITY-MATRIX.md) lists
all exact IDs; `profiles/target.json` explicitly selects every KEEP entry.

Carry over supported telemetry opt-outs, personal/work browser separation and Git
identity, Git LFS filters and local-only Atuin. Preserve reviewed extension families and
selected agent integrations. Preserve unrelated user configuration. Do not copy Mac
runtime defaults or package hooks. SDKMAN/NVM remain selected; mise remains excluded.

Optional and disabled: Google Cloud CLI, Granted, Quickemu, LM Studio, MCP review/policy,
DDC switching, document/diagram tools, extra security scanners, SQLite/DuckDB and other
unselected optional Mac capabilities. Pending/uninstalled: Cilium, Hubble, kubelogin,
fish, Copilot, desktop wrappers, eph tools, Aviatrix and Tailscale. No model downloads,
cluster creation, backup scheduling, credential restoration or VPN profile import is
authorized by package selection. Installed metadata subsequently identified the retained
scanner group as Simple Scan and SANE utilities; physical backend/workflow verification
remains required. See [source review](SOURCE-REVIEW.md).

## D007 — JSON and shared command contracts

Catalogue and machine/selection input use JSON, parsed with distribution Python before
Ansible or uv exists. Ansible playbooks remain YAML. Structural schemas and example
inputs are now present; shared strict semantic runtime validation is P1 work. All
workstation commands require `--config PATH`; no implicit last-used/default selection.
Reject example/placeholder input for installation. Report config, selection and catalogue
provenance with text or `--format json`. Exit 0 complete, 1 failed, 2 invalid/missing
input or prerequisite, 3 incomplete manual/session/reboot/hardware. Noninteractive
execution must never wait for input. [Architecture](ARCHITECTURE.md) defines details.

## D008 — Storage preflight before all installation writes

The mount/identity/handoff guard runs before APT prerequisites, environment creation,
managed-home logs or other managed writes. Matching UUID alone does not prove that old
/var/lib was replaced by the fresh target's state. Require private offline comparison
and handoff evidence tied to target and mounts, then recheck actual state every run.
Do not require a stale initial dpkg checksum after legitimate package updates. Standard
single-disk /var/lib-on-root is valid; transfer evidence is not a generic prerequisite.

## D009 — Verification and update boundaries

Introduce the report format and independent verifier in P1. Add verification with every
role; P5 completes operations rather than introducing verification. Read-only commands
never install, repair or implicitly synchronize environments. Reviewed update candidates
are explicit and revalidated; repository pin changes are separate from workstation
updates. Verify declared update policy: allowed supported-channel refresh differs from
wrong-source or exact-pin drift. Configuration backup is not atomic package rollback.

## D010 — P0 delivery readiness

Normalized selection and structural validation do not assert package/source availability.
Catalogue candidates explicitly retain unverified delivery/licence/version/integrity
fields. Verify these before dependent install tasks, record source failures and block
selected readiness honestly. No invented pins, silent source substitutions or assumed
Linux compatibility from Mac metadata. Physical and workload-specific requirements
remain gates for their dependent phases, not blockers to catalogue/specification work.

## D011 — Java default and project runtimes

The user explicitly selected **Temurin 25 as the default**, superseding the observed
Temurin 21 default on the current machine. Keep SDKMAN ownership and Microsoft/Temurin
21 and 25 available for explicit project selection. Do not change the default when
installing an additional distribution. Preserve the observed Mandrel 25.0.0.1.r25
compatibility requirement until native-image project validation supports a change.
Maven 3.9.11 and the Node 22 line are retained compatibility candidates, not permission
to copy old Mac pins. Exact source/hash resolution remains a delivery gate.

## D012 — Retained shell customizations

The user confirmed the plugins **git, zsh-autosuggestions and zsh-syntax-highlighting**
and the helpers **proxyon/proxyoff**. Both external Zsh plugins are KEEP in the target
and reusable default. Oh My Zsh supplies the git plugin; do not create a second owner.
Chezmoi owns shell initialization and helper definitions; Ansible owns package delivery.
Load each plugin once, with syntax highlighting last. Preserve unrelated shell content
and privately back up replaced files. Framework/manager installers must not rewrite it.

Proxy settings come from private local input with no committed endpoint, username or
password. Missing settings must produce an actionable failure; never assume a public
proxy. Define how proxyoff restores prior environment values and test repeated on/off
cycles without exposing credentials in output. Do not copy shell history or old secret
function bodies. [User environment](../profiles/user-environment.json) records these
confirmed preferences for implementation review; it is not a workstation command input.

## D013 — Reviewed current stable versions

The user selected **move tools to reviewed current stable versions and adapt projects
as needed**. Prefer stable releases available at the explicit release review, including
major upgrades. Exclude previews and release candidates. Older installed versions are
inventory evidence, not compatibility pins: this supersedes D011's preservation
language for Mandrel, Maven and Node. Temurin 25 remains the explicitly selected Java
default, with reviewed stable patches within that line and the selected Java project
variants available through SDKMAN.

The source ledger is a dated observation, not a floating latest installer. Recheck
current releases, Linux support, licences, integrity and dependencies before locking
exact artifacts. For Ubuntu/vendor supported channels, use stable supported packages
from their reviewed source; this decision does not require replacing distribution
packages merely to chase a newer upstream release. Retain D009's explicit update
review and tracked-pin boundaries; no unattended major-upgrade policy is introduced.

Record migration requirements and test representative projects against the new tools.
Project adaptation is the chosen direction; actual edits to other repositories need
a defined project scope and their normal review. No project changes or build execution
are performed by this decision. D014 and D015 resolve the subsequent OpenHands and
project-inventory questions.

## D014 — OpenHands deferred

The user deferred OpenHands from the first usable workstation and retained it in the
backlog. Its catalogue decision is OPTIONAL, excluded from both committed selections.
This supersedes its initial KEEP selection in D006. Its unresolved Linux OCI source,
digest and isolation requirements do not block the initial target. Before explicit
future enablement, verify the official image and one-project/private-state operation
without Docker-socket or whole-home mounts. The inspected agent-canvas desktop release
does not establish the selected Linux container's availability.

## D015 — No existing compatibility projects

The user reports no current projects to test. Do not request project paths again or
claim compatibility with existing workloads. Plan disposable synthetic fixtures for
Java/Maven, native-image, Node/pnpm and selected infrastructure tools, exercising their
basic workflows without production credentials or resources. Actual project migration
tests are deferred until projects exist; their absence does not block the initial
synthetic acceptance suite. Mandrel remains selected under D013's stable-release policy;
the observed old version is not a required compatibility target.

## D016 — Spec-driven implementation and disposable Ubuntu testing

The user authorized implementation, first organized into features and tasks, and
requested a Linux VM on the selected OS for end-to-end testing. Follow
[specs](../specs/README.md): define each feature's behavior and negative acceptance
cases before implementing it, then record actual fixture/guest evidence.

Use dedicated disposable Ubuntu 26.04 amd64 QEMU/KVM infrastructure with GNOME,
synthetic disks, isolated test credentials and loopback-only SSH. The Mac workflow's
bootstrap/operator-script split and VM lifecycle are reference patterns; no Linux
runtime dependency on that repository is introduced. This authorization supersedes
the previous pre-build stop, and does not authorize applying the workstation installer
to the physical host, formatting physical disks or moving production data.

## D017 — Automated disk transfer withdrawn; files move by copy

The user withdrew the automated transferred-disk design on 2026-09-16: "I do not
need automated migration". The receipt, witness, machine-binding, exact-tree
comparison and package-checkpoint work built for it is removed, along with the
`transferred-ssd` storage mode and the `handoff_receipt` configuration field.

Files move by an rsync copy over SSH between the old and new machines, specified
in [F14](../specs/F14-file-migration.md). Nothing partitions, formats or mounts
disks. Completeness is proved by a second rsync pass finding nothing outstanding,
not by a marker file.

The `storage-handoff` capability is retained, repurposed as "Manual file
migration". The physical-drive transfer option in the storage layouts is gone.

## D018 — The manifest is the delivery authority

What a new machine installs is declared in `manifest/`, decided by operator
review recorded in `catalogue/curation.json` and rendered to
[the inventory review](INVENTORY-REVIEW.md). Two inputs feed it, with fixed
precedence: this workstation as observed by `script/inventory`, and the Mac
baseline as an additive contributor that never overrides an observation and is
never a runtime dependency.

A capability the manifest delivers does not additionally need a per-item
delivery-approval record, because the manifest enforces what that record
existed to provide: archive packages come from the signed Ubuntu archive,
third-party repositories pin their signing-key fingerprint, and release
binaries pin a version and SHA-256. The catalogue gate still applies to
anything the manifest does not deliver, reported as deferred rather than
failed, because nothing attempts to install it.

`script/check-manifest` fails when a reviewed selection has no delivery, when
the manifest would install something never selected, or when a binary or
repository key is unpinned.

## D019 — Selection changes of 2026-09-16

Decided in review with the operator:

- **Host Go and Rust toolchains omitted.** "Running go and rust etc should be
  done using a docker container." Their roles and locks remain in the
  repository, dormant. Do not reintroduce them into a profile.
- **SDKMAN owns every JVM installation**, including Gradle and Kotlin. No JVM
  tooling comes from APT.
- **starship replaces the oh-my-zsh agnoster theme** as the shell prompt.
- **aider is not selected**; its source and licence review stays an open gate.
- **kubectl comes from the pkgs.k8s.io repository only**; the duplicate binary
  in `/usr/local/bin` is not reproduced.
- **azure-cli comes from packages.microsoft.com**, replacing the Jammy-built
  package installed on the current machine.
- **nvidia-container-toolkit is installed**, not merely configured.
- Employer tooling (`eph-cli`) and the corporate proxy configuration are not
  reproduced by this repository; they stay manual and private.

## D020 — `~/.ssh/authorized_keys` is never copied

Found during the guest migration rehearsal on 2026-09-16: the secrets pass
replaced the destination's `authorized_keys` with the source's, which revoked
the key the copy was running over and locked the operator out of the machine
mid-transfer.

The secrets pass therefore never copies `~/.ssh/authorized_keys`. Access to the
new machine is established before the migration starts, and any further
authorized keys are added there by hand.
