# Linux software review

Inventory date: 2026-09-12. Target: Intel i7-13700, 128 GB RAM, 2 TB SSD, no NVIDIA GPU. OS selection pending; Ubuntu 26.04/GNOME proposed.

Mark each decision KEEP, OMIT, or OPTIONAL. OMIT means leave out of the new machine, not uninstall from the old machine. Installed files do not prove active usage. Remmina is explicitly confirmed by the user.

## Linux applications and tools observed

| Software/workflow | Evidence | Decision / review note |
|---|---|---|
| Remmina | Desktop entries, Snap archive, configuration directories; user confirmed | KEEP; reconcile installation channel and migrate profiles |
| Bitwarden | Snap archive | KEEP |
| Firefox | Snap archive | KEEP |
| Google Chrome | Manual APT package | KEEP |
| Microsoft Edge / Chromium | Configuration directories only | OPTIONAL |
| Thunderbird | Snap archive | OPTUINAK |
| Slack | Manual APT package | KEEP |
| Obsidian | Manual APT package | KEEP |
| LibreOffice | Desktop entries | KEEP |
| VS Code and extensions | Package and extension directories | Review extension list below |
| Kiro | Manual APT package | OMIT |
| JetBrains applications | OMIT Configuration directory only | Identify active products |
| Claude desktop / ChatGPT desktop | APT package names and desktop entries | Review provenance before reinstalling; names do not establish official vendor origin |
| Claude Code / Codex / Copilot | User-local executable names | Review installation provenance and retained settings |
| Git / GitHub CLI / GnuPG | Manual APT packages | KEEP |
| DBeaver Community | Manual APT package | KEEP connections; credentials separately |
| Meld / Vim / gedit / GNOME Text Editor | Packages or desktop entries | KEEP overlapping editors |
| Midnight Commander / mcedit | Package and desktop entries | KEEP |
| Docker Engine / Compose / Buildx / containerd | Installed packages | KEEP; rebuild using target OS package sources |
| kubectl / kubectx / Helm / k3d / k9s / Stern | Packages, executable names | Review; kubectl exists through multiple paths |
| Cilium / Hubble / kubelogin / yq | System-local executable names | Review provenance and versions |
| AWS CLI / Azure CLI | Manual APT packages | Review |
| Custom eph-* commands | System-local executable names | Identify owning source repository and installation method |
| QEMU / libvirt / virt-manager / Quickemu | Packages | Review which VM frontends are needed |
| OpenVPN / NetworkManager OpenVPN | Manual APT packages | Review; connection secrets stay private |
| Aviatrix VPN Client | Desktop entry | Confirm active use and source |
| HTTPie / curl / wget / net-tools | Manual APT packages | KEEP |
| Dive / Skopeo | Manual APT packages | KEEP |
| zsh / Oh My Zsh | Package / shell integration marker | keep shell customization |
| Starship / Atuin | Executable or shell integration markers | Keep; history may contain sensitive data |
| fish | Configuration directory only | Confirm active use; executable not found earlier |
| NVM / Node 22.21.0 | Runtime directory | Preserve project compatibility when moving to mise |
| SDKMAN / Java 21 and 25 / Mandrel | Runtime directories | Keep vendor and native-image requirements |
| Maven 3.9.11 | Runtime directory | Keep |
| uv / Python 3.12 | Executable and runtime directories | Keep; rebuild project environments |
| OBS Studio / Kazam / Flameshot | Manual APT packages | keep obs studio and flameshot |
| FFmpeg | Manual APT package | Keep |
| btop / htop / Resources / nvtop | Packages or desktop entries | Keep overlapping monitors; nvtop needs a retained use case |
| fastfetch | Manual APT package | Omit |
| dconf Editor / GNOME Extension Manager | Manual APT packages | KEEP |
| GParted / Disks / disk usage analyzer | Packages or desktop entries | KEEP |
| Deja Dup | Desktop entry | KEEP alongside proposed restic/rclone |
| Inconsolata / Powerline fonts | Manual APT packages | KEEP alongside Mac Nerd Font choice |
| Rhythmbox / Shotwell / Showtime / Transmission / scanner utilities | Desktop entries | Optional desktop applications; KEEP |
| NVIDIA drivers, kernel modules, NVIDIA toolkit source | Packages / source filename | KEEP as I have egpu |

## Observed VS Code extension families

Review each: Claude Code, Codex, ESLint, Prettier, GitLens, Go, Python/Pylance/debugpy, Jupyter, Dev Containers, Remote SSH, Docker/Containers, Kubernetes, Makefile Tools, XML, YAML, vscode-icons.

Some installed directories are old versions or dependency extensions. Resolve active extensions and pack roots before creating pins; do not reinstall every directory.

## Mac baseline candidates not established as installed here

Review before adding: chezmoi, mise, Ghostty, Zed, age, SOPS, gitleaks, shellcheck, shfmt, actionlint, yamllint, hadolint, Trivy, restic, rclone, direnv, zoxide, fzf, bat, ripgrep, eza, tmux, Cline, aider, OpenCode, OpenHands, LM Studio; additional Kubernetes and optional security/cloud/data/document tools from the Mac profiles.

The Mac manifests remain the complete source list. This is a decision checklist, not a finalized Linux package manifest. Mac-only applications and integration hooks require replacement or omission.

## Inventory limitations

APT manual selections include OS foundations, libraries and upgrade residue; do not treat them as a removal list. Snap service querying timed out, so archives and desktop entries were used. uv tool listing could not acquire a lock in its read-only cache. System service status was unavailable in the restricted session. No shell history, credentials, connection contents, or private repository remotes were read to infer use. Container and VM data inventories remain operator-run steps.
