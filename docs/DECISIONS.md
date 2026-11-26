# Confirmed project decisions

User-confirmed decisions, 2026-09-12. These supersede conflicting proposals and older hardware/selection notes in the preserved software-review.md. They guide future implementation; no host installation, group modification or disk operation has been performed.

D022–D030 (2026-11-26) make this the Linux host repository. They supersede D002, D003,
D012, D017 and D020, and the command-line, Docker and disk-transfer parts of D005,
D006, D008, D011, D013 and D019. The earlier entries are kept as they were written.

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
function bodies. `profiles/user-environment.json` recorded these confirmed preferences
for implementation review (removed 2026-11-26 with the command line, which
setup-dev-linux-wsl now owns; see [MOVED.md](MOVED.md)).

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

Applied to `catalogue/source-review.json` on 2026-09-17: records are kept for
third-party sources only — 54 of the previous 151. The 97 dropped were Ubuntu
archive packages, where a per-item record repeated what the archive signature
already establishes. A capability delivered by another (`provided-by`) follows
its provider. `check-catalogue` enforces the scope in both directions: a
third-party source without a record fails, and so does a record for an archive
package.

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

## D021 — Source review completed, 2026-09-17

All 54 third-party review records are accepted; every licence is classified in
`catalogue/capabilities.json` from observed evidence with a recorded digest.
49 are free licences; 5 are conditional and are accepted for personal use on
this workstation only:

| Capability | Licence | Constraint |
|---|---|---|
| `claude-code` | Anthropic commercial terms | No redistribution right granted |
| `extension-anthropic.claude-code` | Anthropic commercial terms | No redistribution right granted |
| `extension-openai.chatgpt` | OpenAI terms of use | No redistribution right granted |
| `extension-ms-vscode-remote.remote-containers` | Microsoft extension licence | Licensed only for use with Microsoft products |
| `extension-ms-vscode-remote.remote-ssh` | Microsoft extension licence | Licensed only for use with Microsoft products |

Four needed a determination the captured evidence did not carry, resolved by
fetching the release licence:

- **zed** — GPL-3.0 for the editor; some components Apache-2.0, the
  collaboration server licensed separately.
- **ghostty** — MIT. The Ubuntu package copyright aggregates its whole
  dependency tree, which is why it lists 60 further licences.
- **extension-redhat.vscode-xml** — EPL-2.0.
- **controller-python** — the python-build-standalone tooling is MPL-2.0; the
  CPython artifacts carry PSF plus bundled third-party licences.

Two carry a caveat worth keeping visible:

- **firefox** — MPL-2.0 covers the code, but the licence grants no rights to
  Mozilla trademarks, so redistribution under the Firefox branding is not
  permitted.
- **bitwarden** — GPL-3.0 by default, with `/bitwarden_license` under the
  Bitwarden License v1.0; the published client mixes both.

`source-review.schema.json` gained `accepted` as a record status; it previously
allowed only `review-required`, which is why nothing could ever be marked done.

## D022 — The Linux host repository and the two-repository split

Decided with the operator on 2026-11-26
([design](superpowers/specs/2026-11-26-linux-host-refactor-design.md)). A Linux
machine is set up by two repositories, the same split as on Windows, where
setup-dev-win sets up Windows and hands off to setup-dev-linux-wsl inside WSL:

- **setup-dev-linux (this repository)** sets up the host: the Ubuntu 26.04 OS
  layer, third-party APT sources and their signing keys, the NVIDIA driver,
  desktop applications (APT, snaps, pinned binaries), GNOME settings, extensions
  and fonts, VS Code and its extensions, Zed, Obsidian, virtualisation, the VPN
  client, the firewall, the storage preflight and the VM test harness.
- **setup-dev-linux-wsl, run with `--target linux`**, sets up the command line:
  CLI tools, runtimes, the shell, dotfiles, chezmoi, Docker and kubectl plugins.
  It is the same command-line environment the operator gets inside WSL.

`./bootstrap apply` ends by handing off to it (D029). The repository was refactored
in place: the Python controller, the locked Ansible environment, the manifests, the
catalogue checks and the VM harness stay. The outer shape follows setup-dev-win:
`plan`, `apply` and `verify` (`install` stays as an alias of `apply`), a printed
`Profiles:` line and the handoff.

## D023 — Fresh installs only; migration and file copy removed

The operator: "remove all the migration and copy features". The `migrate` and
`migrate-secrets` commands, `manifest/migrate.json`, the rsync copy of D017, its
secrets pass (D020) and the disk-transfer handoff producer with its configuration
inputs are removed. `tests/test_no_migration.py` keeps them out of the scripts,
tests, manifests, recipes and live documents. The specification and machine
record that described the copy stay as history.

The repository is for a new Ubuntu 26.04 install. A machine set up by the version
before 2026-11-26 is reinstalled, or cleaned by hand: there is no cleanup stage and
no upgrade test. Restoring data stays manual (D001).

## D024 — The command line moved to setup-dev-linux-wsl; MOVED.md is the ledger

Removed from this repository: the command-line parts of the `core`, `dev`, `cloud`,
`kubernetes` and `security` groups, the CLI release binaries, the runtimes (NVM,
SDKMAN, Go, Rust and user uv; setup-dev-linux-wsl uses mise, and Temurin replaces
the Microsoft Build of OpenJDK there), the agent CLIs, the shell and its plugins,
the dotfiles and the krew plugins. This supersedes D003 and D012, and the
command-line parts of D006, D011, D013 and D019.

Nothing was removed without a destination. [MOVED.md](MOVED.md) has one row per
removed item: a profile fragment, APT list, mise configuration or chezmoi source on
setup-dev-linux-wsl's main branch, or a dropped row or decision there with its
reason. `tests/test_moved.py` fails when an item leaves `manifest/*.json` without
a row, and `tests/test_host_only.py` refuses command-line installers here.

claude-desktop (here) and Claude Code (there) share one Anthropic key file,
`/etc/apt/keyrings/anthropic.asc`, byte-identical in both repositories, so APT
never sees one URI with two `Signed-By` values.

## D025 — Host profiles: desktop and headless

A run selects host profiles from `profiles/host.json`: `desktop`, `media`,
`productivity`, `ai`, `network`, `lab`, `gpu`, `dev-gui` and `firewall`. Each maps to
manifest groups; `firewall` maps to its stage (D026). The `base` group installs on
every selection. The default is `desktop,media,productivity,ai,network,dev-gui,firewall`.

The desktop set is `desktop,media,productivity,ai,network,dev-gui`. A selection with
none of it is headless: it runs no snap, GNOME setting, VS Code extension or desktop
playbook, and `verify` demands none of them. `firewall` can be selected on its own;
on a headless machine it installs the OpenSnitch daemon without its UI.

Every command prints the selection on a `Profiles:` line in setup-dev-win's
wording, then `Profiles source: explicit`, `recorded` or `default`. `apply` records
the selection, before anything installs, in per-user state at
`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json` (directory 0700,
file 0600; owner and symlink checks on every read and write), so a re-run without
`--profiles` keeps it. The record lives outside the clone: re-cloning, `git clean`
or rebuilding `.workstation/` must not turn a headless machine into a desktop
install. A record that exists but cannot be read stops the run. The operator's
configuration file is never rewritten. `--manifest-groups` is the former name of
`--profiles`.

## D026 — Firewall: UFW and OpenSnitch

The `firewall` profile runs `ansible/firewall.yml`.

- **UFW**: default deny incoming, default allow outgoing, enabled. Incoming SSH (the
  UFW `OpenSSH` application rule) is allowed only with `--allow-ssh`, never by
  default, and the rule is added before UFW is enabled. The choice is recorded as
  `firewall.allow_ssh` in `state.json` (D025), not in the configuration file;
  later runs without a flag keep it, so an omitted flag never closes SSH, and
  `--no-allow-ssh` removes the rule and records that. libvirt's bridge is left to
  libvirt's own rules.
- **SSH warning**: when `apply` runs over SSH (`SSH_CONNECTION` is set) and SSH is
  not allowed, it warns on standard error and adds a `firewall:ssh-closing`
  notice. It does not refuse: the current session survives; new logins do not.
- **OpenSnitch**, the Linux counterpart of LuLu (Mac) and simplewall (Windows):
  `opensnitch` and `opensnitch-ebpf-modules` from the Ubuntu archive, enabled and
  running; its UI (`python3-opensnitch-ui`) only with the desktop set. Allow mode
  is seeded once, on first install, so setup and the handoff are never blocked by
  a prompt: `"DefaultAction": "allow"` in `/etc/opensnitchd/default-config.json`
  and, with the desktop set, `[global] default_action=1` in
  `~/.config/opensnitch/settings.conf` (created when absent; an existing value is
  never rewritten; the file is backed up before an edit). The flags
  `firewall.opensnitch_seeded` and `firewall.opensnitch_ui_seeded` in `state.json`
  record it. Later runs never rewrite either value: the operator switches to deny
  once their rules exist, and after that re-runs and the handoff may prompt.

`verify` reads `ufw status verbose` through `sudo -n` (without cached credentials
that check is deferred, not passed) and reports both OpenSnitch modes as notices,
never as failures. The firewall packages come only from the signed Ubuntu archive
and are installed by the playbook, not listed in `manifest/packages.json`, so the
manifest's declared-source check does not cover them.

## D027 — Docker belongs to setup-dev-linux-wsl; its ports stay reachable

Docker Engine, buildx, compose, the `docker` group and the NVIDIA container toolkit
are installed by setup-dev-linux-wsl (its `runtime-docker` and `gpu-nvidia`
profiles), one Docker setup for WSL and Linux. This repository installs none of
them and no longer adds the `docker` group; this supersedes D002. The host keeps
the NVIDIA driver.

By the operator's choice, ports a container publishes stay reachable from the
network on a Linux machine (Docker's default), unlike the Mac's loopback rule.
The consequence: Docker writes its own packet-filter rules ahead of UFW's, so a
published port is open to the LAN whatever UFW says. `verify` adds a
`firewall:docker-bypass` notice whenever `docker` is installed. To keep a port
private, publish it on `127.0.0.1`, or filter it in Docker's `DOCKER-USER` chain.

## D028 — chezmoi belongs to setup-dev-linux-wsl

One chezmoi source and one state file per machine, both setup-dev-linux-wsl's. This
repository never runs chezmoi and ships no chezmoi sources; `tests/test_host_only.py`
refuses a mention of it in `script/` and `ansible/`. Desktop files the host owns are
written by Ansible or by the controller as the target user: GNOME settings, the
OpenSnitch UI default, VS Code extensions. The handoff only checks whether
setup-dev-linux-wsl's record (`${XDG_CONFIG_HOME:-~/.config}/chezmoi/chezmoi.toml`)
exists, to decide whether to print the first-run hint (D029). This supersedes the
chezmoi ownership in D003, D012 and [TOOL-SELECTION.md](TOOL-SELECTION.md).

## D029 — The handoff to setup-dev-linux-wsl

The last `apply` stage, run only when the host stages succeeded; host verification
findings are reported but do not hold it back. As the target user, never as root:

1. Clone `https://github.com/istvano/setup-dev-linux-wsl` into
   `~/workspace/setup-dev-linux-wsl`, or update that clone. An existing directory's
   origin is read with `git config --get remote.origin.url`. A directory that is not
   a clone, a clone of another repository, or one with local changes to tracked
   files stops the run with a message naming it; nothing is overwritten.
2. Fetch, resolve `--linux-ref` (default `main`; `origin/<ref>`, else a tag or
   commit) with `git rev-parse --verify`, and check it out once with
   `checkout --detach`.
3. Run `./bootstrap apply --target linux` attached to the terminal; it asks for the
   git identity.

`--profiles LIST` is passed only when the operator gives `--cli-profiles LIST`: that
bootstrap refuses a list that disagrees with its recorded choice, so re-runs pass
none. On its first run it installs its own default without asking and records it.
So when it has recorded nothing and `--cli-profiles` is absent, `apply` prints a
`hint:` line before the host stages and again just before the bootstrap (`plan`
prints it too). The line names the set this repository installed before,
`core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp`
(plus `gpu-nvidia` with the `gpu` profile), says to interrupt (Ctrl-C) and re-run
`apply` with `--cli-profiles` to get it on this run, and says that once a choice is
recorded it is changed in `[data] profiles` of that chezmoi record instead.

For a run with no terminal, such as the VM cycle (D030), `--cli-git-name` and
`--cli-git-email` (both or neither) make the bootstrap run with
`--non-interactive --git-name NAME --git-email EMAIL`; it then takes its defaults for
everything else it would ask. The identity is passed on but never printed.

Outcomes: a failed bootstrap fails the run with its exit code (a `handoff` check,
outcome `failed`); a refusal prints one `handoff:` line naming the cause and exits
1; Ctrl-C during a host stage or the bootstrap prints one line and exits 130;
re-running is always safe. `--linux-ref`, `--cli-profiles` and the identity are checked
before anything changes, and so are the host programs the run needs: `gpg` and
`git` on the system path (packages `gnupg` and `git`; a missing one fails
`preflight` and `apply` with `prerequisite:<program>`). `verify` ends with
setup-dev-linux-wsl's `script/verify --target linux` as `cli:verify`; `apply` does
not, because that bootstrap ends with its own verify. `--no-handoff` skips both.

## D030 — VM acceptance runs both repositories on one guest

`just vm clean-cycle` (`make vm/clean-cycle`) destroys the guest, rebuilds it from
the verified image and runs `script/test-manifest-vm`: `apply` with every host profile
except `gpu` (the guest has no NVIDIA hardware) and `--allow-ssh` (the harness
reaches the guest over SSH), ending with the handoff. The first apply passes
`--cli-profiles` with the former command-line set and a throwaway identity, so
setup-dev-linux-wsl runs non-interactively. The re-run after the reboot passes
neither, which is the operator's re-run path. The guest needs network access:
setup-dev-linux-wsl is cloned from GitHub and installs from Homebrew and vendor
repositories.

Besides what the host installed, the cycle checks UFW and the OpenSnitch seeding,
that `apt-get update` and `apt-get check` stay clean with both repositories'
sources, and that `bootstrap verify` ends with a passing `cli:verify`.
`--skip-handoff` keeps a host-only cycle. `script/test-vm --controller` keeps a
controller-only path: the `firewall` profile alone, `--allow-ssh`, `--no-handoff`.
What a guest cannot show is listed in [TESTING.md](TESTING.md).
