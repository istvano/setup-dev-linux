# setup-dev-linux

Sets up the host of a fresh Ubuntu 26.04 LTS amd64 machine, then hands the command
line to [setup-dev-linux-wsl](https://github.com/istvano/setup-dev-linux-wsl).

A Linux machine is set up by two repositories, the same split as on Windows
(setup-dev-win, then setup-dev-linux-wsl inside WSL):

- **This repository: the host.** Third-party APT sources and their keys, the NVIDIA
  driver, desktop applications (APT, snaps, pinned binaries), GNOME settings, VS Code
  and its extensions, Zed, Obsidian, virtualisation, the VPN client and the firewall.
- **setup-dev-linux-wsl `--target linux`: the command line.** CLI tools, runtimes,
  the shell, dotfiles, chezmoi, Docker and kubectl plugins. `apply` ends by running
  it. [docs/MOVED.md](docs/MOVED.md) says where each item this repository used to
  install went.

Fresh installs only: nothing is copied from another machine, and a machine set up
by an earlier version of this repository is reinstalled, not upgraded.

## Quick start

On the new machine, as your own user (never root, never `sudo`):

```bash
sudo apt install git gnupg          # preflight checks for both
git clone https://github.com/istvano/setup-dev-linux ~/workspace/setup-dev-linux
cd ~/workspace/setup-dev-linux
# write config/your-machine.local.json from a config/*.example.json (docs/NEW-MACHINE.md)

./bootstrap plan   --config config/your-machine.local.json   # what would run; writes nothing
./bootstrap apply  --config config/your-machine.local.json   # the host, then the handoff
./bootstrap verify --config config/your-machine.local.json   # report drift; never repairs
```

Read the `hint:` line `apply` prints before choosing the command-line profiles
(below). `just` and `make` offer the same commands; neither is needed on a new
machine:

```bash
just apply config/your-machine.local.json                     # PROFILES, then any flags
just apply config/your-machine.local.json "" --no-handoff
make apply CONFIG=config/your-machine.local.json FLAGS='--allow-ssh'
```

`just --list` and `make help` list everything; a parity test keeps the two in step.
Full procedure: [NEW-MACHINE.md](docs/NEW-MACHINE.md).

## What gets installed

`manifest/` is the single source of truth:

| File | Holds |
|---|---|
| `packages.json` | APT packages by group, each naming the archive or a repository |
| `repositories.json` | Third-party APT sources, each with its signing key |
| `snaps.json` | Snaps and their channels |
| `binaries.json` | Desktop release binaries (zed, obsidian), each pinned to a version, URL and SHA-256 |
| `desktop.json` | Curated GNOME settings, extensions and fonts |
| `plugins.json` | VS Code extensions |
| `system.json` | Group memberships beyond packages |

## Profiles

A run selects host profiles (`profiles/host.json`): `desktop`, `media`,
`productivity`, `ai`, `network`, `lab`, `gpu`, `dev-gui` and `firewall`. The default is
`desktop,media,productivity,ai,network,dev-gui,firewall`. A selection without any of
`desktop,media,productivity,ai,network,dev-gui` is headless: no snaps, GNOME
settings or VS Code. `firewall` can be selected on its own.

Every run prints the selection on a `Profiles:` line, followed by
`Profiles source: explicit|recorded|default`. `apply` records the choice in
`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json`, outside the clone,
so a re-run without `--profiles` keeps it even after re-cloning or rebuilding
`.workstation/`:

```bash
./bootstrap apply --config config/your-machine.local.json --profiles gpu,firewall   # a headless GPU server
```

## Firewall

The `firewall` profile enables UFW (deny incoming, allow outgoing) and installs
OpenSnitch running in allow mode (the daemon's `"DefaultAction": "allow"` and, with the
desktop set, the UI's own `default_action` in `~/.config/opensnitch/settings.conf`; both
are seeded once on first install, so setup and the handoff are never blocked). Switch to
deny yourself later: re-runs do not rewrite it, but after that the handoff and later
`apply` runs may prompt for git, apt and Homebrew connections.

SSH is closed unless you pass `--allow-ssh`. The choice is recorded as
`firewall.allow_ssh` in the same `state.json`, so later runs without the flag keep it,
and `--no-allow-ssh` removes the rule again. A run over SSH without `--allow-ssh`
warns that new SSH logins will be refused.

```bash
./bootstrap apply --config config/your-machine.local.json --allow-ssh
```

Docker comes from setup-dev-linux-wsl, and the ports its containers publish stay
reachable from the network: Docker's own packet-filter rules bypass UFW. `verify`
says so whenever Docker is installed. Publish on `127.0.0.1` to keep a port private.

## The handoff to setup-dev-linux-wsl

`apply` ends, once the host stages have succeeded, by cloning or updating
`~/workspace/setup-dev-linux-wsl` (a clone of anything else, or one with local
changes, stops the run and is never overwritten), checking out `--linux-ref`
(default `main`) and running its `./bootstrap apply --target linux` as you,
interactively: it asks for your git name and email.

It passes `--profiles` only when you give `--cli-profiles`; otherwise
setup-dev-linux-wsl uses its recorded choice, or on its first run its own default,
which it installs without asking and records. On that first run apply prints a
`hint:` line before the host stages and again just before the handoff, with the list
matching what this repository used to install: interrupt (Ctrl-C; apply exits 130,
and re-running is safe) and re-run with `--cli-profiles`. Once the choice is
recorded, setup-dev-linux-wsl refuses a different `--cli-profiles`: change
`[data] profiles` in `${XDG_CONFIG_HOME:-~/.config}/chezmoi/chezmoi.toml` instead,
then re-run.

```bash
./bootstrap apply --config config/your-machine.local.json \
  --cli-profiles core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp   # add ,gpu-nvidia with the gpu profile
./bootstrap apply --config config/your-machine.local.json --no-handoff   # host only
```

`--cli-git-name NAME --cli-git-email EMAIL` run it with `--non-interactive`, for a
run with no terminal (the VM cycle uses them). `verify` appends setup-dev-linux-wsl's
`script/verify --target linux` (skipped with `--no-handoff`). After the first `apply`,
log out and back in: group memberships, such as the `docker` group, take effect in a
new session.

## How the manifest was decided

Two inputs, with fixed precedence:

1. **This machine** — `script/inventory` reads the installed packages, snaps,
   third-party repositories, runtimes, shell setup, GNOME settings and the
   binaries installed outside APT.
2. **The Mac baseline** (`../mac-os-setup`) — contributes tools and structure
   this machine lacks. Additive only, never a runtime dependency.

Both render into [docs/INVENTORY-REVIEW.md](docs/INVENTORY-REVIEW.md), which
records every item, where it came from, and the decision made about it.
`script/check-manifest` fails if a kept selection has no delivery, or if the
manifest would install something never selected.

To change what a new machine gets, change the manifest.

## Guarantees

- Every third-party binary is pinned to a version, URL and SHA-256 before it
  may install. Unpinned entries are refused, not downloaded.
- Every third-party APT source declares a signing key or a Launchpad PPA.
- Ubuntu archive packages need no per-item review; third-party sources do.
- `apply` never removes unrelated packages, never partitions or formats, and
  refuses to run as root. The handoff never overwrites a clone it did not make.
- `apply` is repeatable; a second run on a correct machine changes nothing.
- `verify` reads the system and reports drift. It never repairs.

## Storage layouts

| Layout | System disk | Data disk |
|---|---|---|
| Single disk | EFI, separate `/boot`, `/` and `/home`; `/var/lib` within `/` | Not required |
| Split system/data | EFI, separate `/boot` and `/` | `/home`; optionally separate `/var/lib` |

Disk roles come from verified stable identities in private configuration.
"System disk" and "data disk" never mean the first or second enumerated device.
No target disk encryption is selected.

## Keeping it current

```bash
make update/report        # what has moved upstream; writes nothing
make update/apply         # re-pin what can be re-pinned, then check
```

`update/report` compares every pinned version with what upstream publishes and
says which can be refreshed automatically and which are hand-curated locks
needing review. Full procedure: [OPERATIONS.md](docs/OPERATIONS.md#keeping-versions-current).

## Testing

```bash
just verify-static        # no VM needed
just vm clean-cycle       # destroy the guest, rebuild, apply with the handoff, verify, reboot, repeat
```

The clean cycle runs both repositories on one guest and needs network access:
setup-dev-linux-wsl is cloned from GitHub. It needs Linux with KVM.

Grouped subcommands use a slash in make and a module in just, which spells the
same path with `::` or a space:

```bash
make vm/status           just vm status      # or: just vm::status
make vm/up               just vm up
make vm/clean-cycle      just vm clean-cycle
```

`make help` and `just --list vm` list them.

The VM cycle cannot prove GPU delivery or the desktop session: the guest has no
NVIDIA hardware and runs a server image. [TESTING.md](docs/TESTING.md) lists what
it checks and what stays manual.

## Documents

Start with [the document index](docs/README.md), or go straight to:

- [New machine runbook](docs/NEW-MACHINE.md) — fresh Ubuntu to a working machine
- [Operations](docs/OPERATIONS.md) — commands, and keeping versions current
- [Decisions](docs/DECISIONS.md) — D022–D030 describe the host role
- [Moved items](docs/MOVED.md) — where each command-line item went
- [Inventory review](docs/INVENTORY-REVIEW.md) — every item and its decision
- [TASKS.md](TASKS.md) — what is unfinished

Keep private disk identifiers, inventories, credentials, backups and VM images
out of Git.
