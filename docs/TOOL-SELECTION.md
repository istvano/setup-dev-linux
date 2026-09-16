# Tool selection and ownership

Status: recommended implementation design, 2026-09-12. D006 and the capability matrix now define the confirmed target selection; this document describes ownership, not installed state. The initial supported platform is Ubuntu 26.04 LTS amd64 with GNOME. Hardware capacity, GPU profile and disk layout are per-machine inputs; [the machine record](migrations/current.md) is an example, not a requirement.

## Selected implementation stack

| Tool | Decision and responsibility | Execution location | Reason / alternative considered |
|---|---|---|---|
| Ansible Core | Primary orchestration: package sources, packages, privileged files, services, GPU, desktop state | Repository-local Python environment on the workstation | Modules provide structured state and privilege escalation. Prefer this to expanding a shell-only installer. No server, AWX or paid Ansible platform required. |
| chezmoi | User dotfiles: shell, Git, terminal, editor settings and CLI configuration | Login user | Reuse portable Mac templates and familiar diff workflow. Never manage the same file in Ansible templates. No package-install hooks. |
| APT / dpkg | OS, drivers, native libraries and suitable host applications | System; privileged tasks only | Ubuntu-native lifecycle and signed repositories. No Homebrew on Linux. System Python remains distribution-owned. |
| Snap | Explicit per-app delivery channel where selected; initial candidate for retained Firefox/Bitwarden | System-managed applications | Match existing Ubuntu use where suitable; verify publisher/channel and permissions. No automatic duplication of APT apps. |
| Verified upstream releases | Fallback for selected tools without a suitable supported repository | User bin directory or root-owned /opt, selected per tool | Exact release and reviewed digest/signature. No unreviewed curl-pipe-shell. |
| uv | Lock and create the setup's isolated Python environment; manage Python project dependencies | Repository .venv and project-local environments | No global pip or changes to Ubuntu Python. Bootstrap uv from a verified pinned artifact. |
| SDKMAN | Selected JVM manager: Java vendors/versions, Maven and Gradle/Kotlin | User | Explicit user decision. Preserve project requirements and Mandrel/native-image workflows. Use a reviewed versioned bootstrap artifact and controlled update policy. |
| NVM | Selected Node.js manager | User | Explicit user decision. Preserve .nvmrc selection and project-required Node versions. Install a pinned reviewed release without modifying shell files outside chezmoi. |
| Bash | Thin entry points, bootstrap trust setup and small integration helpers | User; explicitly scoped sudo | Keep logic in Ansible modules where practical. Every script has strict parsing and a read-only preview path. |
| Python / pytest | Catalogue validation, normalized inventory, CLI/renderer behavior tests | Setup's uv environment | Existing structured formats can be validated without a new executable or runtime manager. Tests exercise failure and recovery behavior, not implementation text. |
| ansible-lint / yamllint | Playbook and YAML validation | Setup's uv environment | Pin with the automation dependencies. Use only the collections actually required. |
| ShellCheck / shfmt / actionlint / gitleaks | Shell, formatting, CI and secret checks | Development/CI host | Carry across useful Mac gates. Missing required tools fail the strict gate. |
| QEMU/KVM + libvirt + cloud-init | Disposable Ubuntu integration guests | Development host; guest-local setup | Test real systemd/package/kernel behavior. Containers alone cannot prove workstation installation. Test VMs are separate from hostile-work lab VMs. |
| Ubuntu Autoinstall | Later phase: install the OS before running bootstrap | Target installer or disposable VM | Native installer path; use locally generated inputs. Standard storage mode is the reusable default and does not require an old SSD. Optional transferred-ssd mode is selected for this migration: /, /boot and EFI on SSD 1; /home and /var/lib on preserved SSD 2. Installer must not format transferred storage. No Landscape deployment needed for this personal setup. |
| Git / just | Version control and thin convenience aliases | User | Scripts remain the canonical interface, so just is not required to bootstrap. No automatic commits/pushes. |

No separate Ansible Vault/SOPS dependency is needed to run an ordinary install: the repository must not need production credentials. Selected age/GPG/SOPS user workflows remain independent of bootstrap credentials. Test credentials are throwaway and never checked in. Raw snapshots and logs are local/private.

Storage transfer is optional: see [confirmed decisions](DECISIONS.md). Apply validates only mounts required by the selected mode/layout and never performs data migration. Single SSD: EFI and separate /boot, /, /home; /var/lib is a directory on root. Two SSDs: EFI, /boot and / on SSD 1; /home and selected separate /var/lib on SSD 2. The separate /var/lib filesystem is optional, so its absence is not a failure for single-disk layouts.

## Single-owner configuration contract

- Ansible owns `/etc` changes, package repositories, packages, service units, scoped group membership, selected GNOME settings and installation sequencing.
- chezmoi owns declared user dotfiles. Ansible may invoke it as the actual login user, but may not template those files itself. It must not set HOME to root or run user tools with sudo.
- SDKMAN owns JVM tools; NVM owns Node.js. uv owns Python project environments and the setup environment. mise is not part of the selected baseline; Go and pnpm use verified versioned upstream distributions; pinned rustup manages explicitly pinned Rust toolchains. These capabilities are now selected. The setup's Python must remain usable if user runtime configuration is broken.
- Ansible invokes runtime/tool reconciliation after chezmoi renders configuration. Compare installed state before reporting changed; do not use `changed_when: false` to hide installation changes.
- Every package ID has one source owner. Detect APT/Snap/upstream duplicates and report a reconciliation task; do not silently uninstall existing software.
- No chezmoi hook may invoke Ansible or install system packages. No Ansible role may call the bootstrap recursively.
- GNOME changes run in the target user's active session. Without session D-Bus, explicitly defer them to a user-invoked desktop command, rather than claiming successful application. GTK/GNOME defaults are allowlisted, not a full dconf dump.

The Ansible APT module supports check/diff mode, but package installation can start services; roles must specify intended service behavior. [APT module](https://docs.ansible.com/projects/ansible/latest/collections/ansible/builtin/apt_module.html)

Check mode is a simulation and unsupported modules can be skipped. The plan command therefore also reports unassessed operations and never equates preview success with install success. [Ansible check mode](https://docs.ansible.com/projects/ansible-core/devel/playbook_guide/playbooks_checkmode.html)

Chezmoi advises sparse, idempotent script use; retaining file management without duplicating package hooks reduces orchestration overlap. [Chezmoi scripts](https://www.chezmoi.io/user-guide/use-scripts-to-perform-actions/)

## Workstation components

| Component | Proposed choice | Boundary and conditions |
|---|---|---|
| Containers | Docker Engine + Compose + Buildx | Native Linux host daemon; no Colima/Rancher/OrbStack VM. Rootful Docker with the selected workstation user in the privileged docker group is the confirmed default. Ansible adds supplementary membership without replacing other groups; verify access after a new login. Never make the socket world-writable or add unrelated users. No TCP daemon socket. |
| GPU | Ubuntu-supported NVIDIA driver branch + NVIDIA Container Toolkit | Drivers on host; configure toolkit only for selected container runtime. CUDA dependencies stay in projects/containers unless a host compiler use case requires otherwise. |
| Remote desktop | Remmina, preferred APT package with required RDP/secret plugins | Host GUI, with GNOME keyring integration. Validate Ubuntu package names and protocol support before pinning selection. Preserve profiles manually. Avoid duplicate Snap/APT installs. |
| Virtualization | KVM/libvirt; virt-manager (selected) | Host virtualization; isolated lab guests for untrusted code. Quickemu is optional and disabled by D006. |
| Host security | AppArmor plus Ubuntu UFW baseline | Preserve default confinement; deny unsolicited inbound connections while preserving explicitly selected access. UFW is not a LuLu-style application egress firewall. Application egress tooling remains a separate evaluated decision. |
| Passwords/signing | Bitwarden, GnuPG, desktop pinentry/keyring | Host capabilities. Fresh SSH key per machine; restore decryption identities manually. |
| Display switching | Optional ddcutil candidate, disabled | Host DDC/CI access for the shared monitors; validate connection paths and least-privilege device access on actual hardware. |
| Backup | Keep Deja Dup, restic and rclone | Host access to selected files. Keep overlapping user choices; do not enable two competing schedules. Backup destination/encryption setup remains manual. |
| Shell | zsh, Starship, Atuin; retained Oh My Zsh customizations | Host interactive shell. No automatic login-shell change. Oh My Zsh is retained; identify customizations and pin source and selected plugins; disable uncontrolled self-updates and avoid its remote installer. |
| Local AI | LM Studio optional, disabled | NVIDIA support does not authorize installing every inference runtime. Preserve the Mac LM Studio preference as a candidate; no MLX on Linux or automatic model downloads. |

Docker group access grants root-level privileges. That tradeoff is visible in the plan and verified rather than hidden in a convenience task. [Docker post-installation](https://docs.docker.com/engine/install/linux-postinstall)

Docker supports Ubuntu 26.04, and its published ports require separate scrutiny because they can bypass UFW. Repository-created ports bind `127.0.0.1`; test exposure from a second VM as well as inspecting bindings. [Docker Ubuntu installation](https://docs.docker.com/engine/install/ubuntu/)

NVIDIA lists Ubuntu 26.04 amd64 in its Container Toolkit platform table. This supports the software choice, not the untested enclosure, link, hotplug or suspend behavior of the particular eGPU. [NVIDIA platform support](https://docs.nvidia.com/datacenter/cloud-native/container-toolkit/latest/supported-platforms.html)

SDKMAN and NVM are retained by user decision. Verify selected Java distributions, Mandrel and Node release availability during implementation; compatibility testing validates retained workflows, not migration to mise. See [confirmed decisions](DECISIONS.md).

## Version, source and licence policy

Before installing any selected tool, record its purpose, profile, source URL, platform, update policy, licence identifier/terms and free/paid/conditional classification. The core automation design requires no paid service. Do not infer vendor authenticity from an application name, especially the observed ChatGPT/Claude desktop packages.

Pin the setup interpreter, uv artifact, ansible-core, linters and pytest; commit `uv.lock` and use `uv sync --locked`. Pin required Ansible collections in `requirements.yml` and verify downloaded artifacts where the distribution mechanism supports it. Resolve concrete current versions in implementation phase P1; this design does not invent untested pins. [uv locking and syncing](https://docs.astral.sh/uv/concepts/projects/sync/)

For APT, record supported Ubuntu release, approved repository and installed versions. Prefer supported security updates over indefinite blanket package holds. Exact historic APT availability is not guaranteed by a manifest; an offline/rebuild-exact requirement would additionally need a managed artifact mirror or snapshot. Do not claim byte-identical reinstalls without one.

For downloaded tools/extensions, use exact versions and reviewed integrity information. For images, use immutable digests. For Snap, record publisher, channel and observed revision, and document refresh behavior; do not promise permanent revision availability. A chosen app's auto-update behavior must be stated in its catalogue entry.

## Deferred alternatives

- Nix/Home Manager: deferred; introduces a second system/package model beyond the existing Ubuntu and Mac workflows.
- Terraform: not selected. OpenTofu, Terragrunt and terraform-docs are selected developer tools, not the workstation orchestration engine.
- Salt/Puppet/Chef: no need for a persistent configuration-management service for one workstation.
- AWX/Ansible Automation Platform and Landscape: no personal-workstation requirement justifies their service infrastructure.
- Molecule: defer until role scenario complexity warrants another test framework; begin with pytest fixtures and direct disposable-VM integration.
- Flatpak: available as a future per-app choice, not a blanket extra delivery channel in the initial plan.
- mise consolidation: declined for the current baseline. SDKMAN and NVM are the selected runtime managers; do not replace them during implementation.

## Confirmed additions and foundation contracts

See [capability matrix](CAPABILITY-MATRIX.md) for exact selected, optional, pending and
omitted capabilities. The full Mac Kubernetes set and plugins, editor/agent set, selected
AWS/Azure/IaC tools and OpenVPN integration are confirmed. Optional MCP policy, DDC, local
AI and specialist profiles remain disabled. Do not install a Mac-only integration because
its source token appears in the audit mapping.

NVM/SDKMAN remain the user-selected runtime managers. Go and pnpm are independent verified
upstream installations; Rust uses pinned rustup/toolchains. Gradle/Kotlin use SDKMAN.
Selected agents use reviewed Linux channels; pin and isolate any npm CLI prefix from
project NVM switching. uv tooling never replaces distribution Python or imports Mac pins.

JSON configuration/catalogue parsing precedes automation dependency installation. Run
storage/handoff guards before APT or any managed writes. P1 introduces independent
verification and consistent reports; P2–P4 add checks with each role. All workstation
commands require `--config PATH`; read-only commands never implicitly sync uv or trigger
runtime installation. [Architecture](ARCHITECTURE.md) defines the exact contracts.

Package/licence sources in the catalogue are explicitly unverified candidates. Complete
source validation and pin selection before dependent install roles. A supported-channel
update is not automatically drift; an exact-pin mismatch or unapproved source is.
Workstation updates do not edit tracked pins and do not promise atomic package rollback.
