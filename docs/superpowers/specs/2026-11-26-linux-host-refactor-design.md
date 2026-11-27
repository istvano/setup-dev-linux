# setup-dev-linux becomes the Linux host repository: design

Status: draft for operator approval, 2026-11-26.

## Intent

The operator wants one command-line development environment, built by one repository,
`setup-dev-linux-wsl`, on every machine: inside WSL on Windows and directly on a Linux
machine. Each machine's own repository sets up the machine itself and then hands off,
the way `setup-dev-win` sets up Windows and hands off to `setup-dev-linux-wsl` inside
WSL. For Linux machines that host repository is this one, `setup-dev-linux`.

So this repository stops installing anything that belongs to the command line, keeps
everything that belongs to the operating system and the desktop, gains firewall
settings, loses the migration and file-copy features, and ends every run by handing off
to `setup-dev-linux-wsl --target linux`.

## Goals

- `setup-dev-linux` owns the OS layer on Ubuntu 26.04: apt repositories and keys,
  drivers (NVIDIA), desktop applications (apt, snap, pinned binaries), GNOME settings,
  extensions and fonts, the host editor (VS Code and its extensions, Zed), virtualisation
  (libvirt, virt-manager, quickemu), VPN client, system groups, firewall, the storage
  preflight and the VM test harness.
- A final **handoff** stage clones `setup-dev-linux-wsl` and runs
  `./bootstrap apply --target linux`, interactively (it asks for the git identity), and
  `verify` also runs that repository's `script/verify`.
- **No loss of functionality.** Every item the repository installs or configures today
  ends up in exactly one place: still here, already in `setup-dev-linux-wsl`, added to
  `setup-dev-linux-wsl` by this project, or recorded as deliberately dropped with a reason.
- The operator-facing shape matches `setup-dev-win`: top-level `plan`, `apply` (today
  `install`) and `verify`, a printed "Profiles:" line, the same handoff wording, ADRs for
  durable decisions.

## Non-goals

- Rewriting the installer. The Python controller, the locked Ansible environment, the
  manifests and the VM harness stay (approach A, operator decision).
- Changing what `setup-dev-linux-wsl` is: it stays the single owner of the shell,
  CLI tools, runtimes, dotfiles and (after this project) Docker.
- Applying Windows-style hardening beyond the firewall.

## Anti-goals

- Two repositories fighting over the same file. In particular the host repository no
  longer runs chezmoi: `setup-dev-linux-wsl` owns chezmoi on the machine (one source,
  one state file). Desktop files the host owns (for example a Ghostty config, GNOME
  settings) are written by Ansible.
- A machine that silently lost a tool it had before.
- Migration or file-copy code left half-removed.

## Decisions taken with the operator

1. Two repositories per Linux machine: `setup-dev-linux` (host) and
   `setup-dev-linux-wsl --target linux` (CLI). Same split as Windows.
2. Approach A: refactor in place, keep Python and Ansible; borrow `setup-dev-win`'s outer
   shape (commands, profiles line, handoff, ADRs).
3. **Docker belongs to `setup-dev-linux-wsl`** on both targets (one Docker setup for
   WSL and Linux). The host keeps the NVIDIA driver; the NVIDIA container toolkit goes
   with Docker.
4. Migration and file-copy features are removed completely.
5. Firewall settings are driven by this repository.
6. **Fresh installs only.** The refactored repository is for new Ubuntu installs; a
   machine provisioned by the current version is reinstalled or cleaned by hand. No
   cleanup stage, no upgrade test.
7. **Desktop and headless.** The desktop layer (desktop apps, GNOME settings,
   extensions and fonts, snaps, VS Code, OpenSnitch) is a set of profiles, selected by
   default; a server run leaves them out and keeps the OS layer, drivers, firewall,
   groups and the CLI handoff.
8. **Docker ports stay reachable from the network** on a Linux machine (operator
   choice; Docker's default, as today), unlike the Mac's loopback rule. Consequence to
   document: Docker's published ports are not filtered by UFW (Docker programs the
   packet filter itself), so a published port is open to the LAN whatever UFW says.
9. **OpenSnitch is installed and running in allow-by-default mode** after setup, so
   setup and the handoff are never blocked; the operator switches the default to deny
   once their rules exist (as with simplewall on Windows).

## What moves where (the builder verifies and completes this table first)

**Stays in `setup-dev-linux` (host):** apt repositories for host apps (vscode,
google-chrome, slack, dbeaver, claude-desktop, chatgpt, ppa-obs, ppa-quickemu); groups
`desktop` (dconf tools, extension manager, gparted, gedit, ghostty, fonts), `media`
(ffmpeg, flameshot, kazam, restricted addons, obs-studio), `productivity` (chrome,
slack), `ai` (claude-desktop, chatgpt), `network` (openvpn, network-manager-openvpn-gnome,
net-tools), `lab` (libvirt, virt-manager, bridge-utils, quickemu), `gpu` (driver,
modules, nvtop, dkms, headers, ubuntu-drivers-common), the GUI part of `dev` (code,
dbeaver-ce, meld); snaps (firefox, thunderbird, bitwarden, remmina); binaries zed and
obsidian; `desktop.json` (GNOME settings, extensions, fonts); VS Code extensions
(`plugins.json` `vscode_extensions`, since VS Code runs natively here); `system.json`
user groups except docker; storage preflight; VM harness; catalogue checks trimmed to
host scope; `update-report` for host pins.

**Already in `setup-dev-linux-wsl`:** the CLI part of `core`, `dev`, `cloud` (aws,
tofu), `kubernetes`, `security`; 22 of the 27 binaries (helm, k9s, k3d, stern,
kubelogin, krew, kubeconform, kubeseal, helmfile, argocd, terragrunt, terraform-docs,
sops, syft, grype, trufflehog, osv-scanner, actionlint, hadolint, d2, yq, chezmoi,
dive, as Homebrew formulae); runtimes (mise replaces NVM, SDKMAN, pinned Go/Rust, user
uv); codex, cline, opencode; shell, prompt, history, dotfiles, krew plugins.

**To add to `setup-dev-linux-wsl` in this project (otherwise lost):**
- Docker engine, buildx, compose and skopeo, plus the docker group, for
  `--target linux` (pulls that part of `setup-dev-linux-wsl`'s Docker milestone forward;
  ports reachable from the network per decision 8, so that repository's loopback-only
  `daemon.json` applies to the WSL target only, later). Docker inside WSL stays in that
  repository's WSL milestone, together with `appendWindowsPath=false`, the `code`
  wrapper and the credential store. The NVIDIA container toolkit goes into
  `setup-dev-linux-wsl`'s opt-in `gpu-nvidia` profile, not into every Docker install.
  Exposure checks there must be target-aware: a desktop Linux machine has legitimate
  non-loopback listeners (avahi and the like).
- azure-cli and google-cloud-cli from the vendors' signed apt repositories (pulls the
  planned vendor-apt work forward).
- Claude Code CLI from Anthropic's signed apt repository (as `setup-dev-linux-wsl`'s
  spec already plans; on the host it shares the vendored Anthropic key with
  claude-desktop, one keyring and one `Signed-By` so APT never sees conflicting
  sources), and GitHub Copilot CLI through mise's npm backend (latest stable, ADR-011).
- mc, fastfetch, cilium-cli, hubble and vim (if not already present), or a DROPPED.md
  row each with the reason.

**Already deliberately dropped** (DROPPED.md in `setup-dev-linux-wsl`): httpie (xh),
Mandrel/SDKMAN, NVM, oh-my-zsh, Ansible controller as a CLI tool, and the rest listed
there.

**Removed from this repository:** `migrate` and `migrate-secrets` commands, `manifest/migrate.json`,
`script/workstation/migrate.py`, its tests, docs sections and just/Makefile targets; the
transfer storage mode and handoff-evidence machinery that only served migration; the
CLI playbooks and modules (user-tools, sdkman, java/jvm-tools/mandrel, go, rust,
python-user, node, npm-cli, opencode, codex, cline runtimes, user-environment, binaries
for CLI tools), their locks and tests; `shell.json`, `dotfiles.json`, `runtimes.json`
and the CLI parts of `packages.json`, `binaries.json`, `repositories.json`, `plugins.json`.

## Firewall (new)

(OpenSnitch per decision 9; Docker and UFW per decision 8.)

- **UFW**: enabled, default deny incoming, allow outgoing; an `ssh` allowance only when
  the operator selects it (profile or flag), never by default; libvirt's bridge left to
  libvirt's own rules. Verified by reading `ufw status verbose`.
- **OpenSnitch** (outbound, per application), the Linux counterpart of LuLu (Mac) and
  simplewall (Windows): installed with the desktop; rules are the operator's.
- `verify` reports both.

## Profiles (builder's call, confirmed in review)

Host profiles are the trimmed manifest groups (desktop, media, productivity, ai,
network, lab, gpu and the GUI dev group); the desktop ones are on by default. The run
prints a "Profiles:" line like `setup-dev-win`. By default the handoff passes no CLI
profiles, as `setup-dev-win` does, so `setup-dev-linux-wsl` uses its recorded choice;
an optional `--cli-profiles` is passed through only when the operator gives it (its
bootstrap refuses a list that disagrees with the recorded one, so passing a list on
every run would break re-runs).

## Handoff

The last stage, after the host stages succeed: clone or update
`~/workspace/setup-dev-linux-wsl` (same hardening as `setup-dev-win`'s handoff: fixed
program, origin check, resolve-then-checkout of the requested ref), then run
`./bootstrap apply --target linux` as the operator (never as root), passing selected CLI
profiles through. A failed handoff fails the run with the Linux repository's exit code;
re-running is safe.

## Constraints

- Ubuntu 26.04 LTS, amd64. Never run as root; elevation per step as the repository does today.
- Keep the repository's existing quality bars: pinned and verified downloads, signed
  apt keys with recorded fingerprints, no download-and-run scripts, tests fail rather
  than skip, the VM clean-cycle acceptance.
- Latest-stable policy applies in `setup-dev-linux-wsl` (its ADR-011); this repository
  keeps its own pinning for host binaries and keys unless the operator decides otherwise.

## Approaches considered

- **A. Refactor in place (chosen):** keep the controller, Ansible, manifests, VM harness;
  remove CLI and migration; add firewall and handoff; adopt `setup-dev-win`'s outer shape.
  Least risk of losing behaviour.
- **B. Rebuild in `setup-dev-win`'s shape:** uniform repositories, but a rewrite that
  replaces tested Ansible and the catalogue layer; real risk of dropped behaviour.
- **C. Fold host setup into `setup-dev-linux-wsl`:** contradicts the two-repository split.

## Left to the builder

- The exact catalogue trimming (keep the checks, reduce records to host scope).
- Whether `install` stays as an alias of `apply`.
- Test layout for the new firewall and handoff stages; VM clean-cycle extended to run the
  handoff end to end.
- Ordering of the work across the two repositories so that no merged state loses a tool:
  the `setup-dev-linux-wsl` additions land before the host removes the same items.
