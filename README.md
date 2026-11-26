# linux-os-setup

Reproducible Ubuntu 26.04 LTS workstation setup for a fresh machine.

The repository holds a declarative record of what this workstation runs and an
installer that reproduces it elsewhere. New machine: install the manifest, authenticate by hand.

## Quick start

```bash
just verify-static                            # catalogue, manifest coverage, tests
just plan config/your-machine.json            # what would be installed; writes nothing
just apply config/your-machine.json           # set up the host (install is an alias)
```

A `Makefile` offers the same targets, for a machine that does not have `just`
on it yet — which includes a new one, before this repository installs it:

```bash
make verify-static
make plan CONFIG=config/your-machine.json
make apply CONFIG=config/your-machine.json
```

`just --list` and `make help` both list everything. The two are kept in step by
a parity test.

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

The manifest is grouped by purpose, and a run selects host profiles
(`profiles/host.json`): `desktop`, `media`, `productivity`, `ai`, `network`,
`lab`, `gpu`, `dev-gui` and `firewall`. The default is
`desktop,media,productivity,ai,network,dev-gui,firewall`; a selection without the
desktop profiles is headless. Every run prints the selection on a `Profiles:` line,
followed by `Profiles source: explicit|recorded|default`. `apply` records the
choice in `${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json`,
outside the clone, so a re-run without `--profiles` keeps it even after re-cloning
or rebuilding `.workstation/`:

```bash
just apply config/your-machine.json gpu,firewall     # ./bootstrap apply --config ... --profiles gpu,firewall
```

The `firewall` profile enables UFW (deny incoming, allow outgoing) and installs
OpenSnitch running in allow mode (the daemon's `"DefaultAction": "allow"` and, with the
desktop set, the UI's own `default_action` in `~/.config/opensnitch/settings.conf`; both
are seeded once on first install, so setup and the handoff are never blocked). Switch to
deny yourself later: re-runs are not rewritten, but after that the handoff and later
`apply` runs may prompt for git, apt and Homebrew connections. A run over SSH without
`--allow-ssh` warns that new SSH logins will be refused. SSH is closed unless
you pass `--allow-ssh`; the choice is recorded as `firewall.allow_ssh` in the same
`state.json`, so later runs without the flag keep it, and `--no-allow-ssh` removes
the rule again. Docker's published ports bypass UFW (`verify` says so when Docker
is installed).

```bash
./bootstrap apply --config config/your-machine.json --allow-ssh
```

Command-line tools, runtimes, the shell, dotfiles, kubectl plugins and Docker are
installed by [setup-dev-linux-wsl](https://github.com/istvano/setup-dev-linux-wsl)
(`--target linux`), not here. [docs/MOVED.md](docs/MOVED.md) says where each item
this repository used to install went. `apply` ends by handing off to it, as
setup-dev-win does: it clones or updates `~/workspace/setup-dev-linux-wsl` (a clone
of anything else, or one with local changes, stops the run and is never
overwritten), checks out `--linux-ref` (default `main`) and runs its
`./bootstrap apply --target linux` as you, interactively. It passes `--profiles`
only when you give `--cli-profiles`; otherwise setup-dev-linux-wsl uses its recorded
choice, or on its first run its own default, which it installs without asking and
records. On that first run apply prints a `hint:` line before the host stages and
again just before the handoff, with the list matching what this repository used to
install: interrupt (Ctrl-C; apply exits 130, and re-running is safe) and re-run
with `--cli-profiles`. Once the choice is recorded, setup-dev-linux-wsl refuses a
different `--cli-profiles`: change `[data] profiles` in
`${XDG_CONFIG_HOME:-~/.config}/chezmoi/chezmoi.toml` instead, then re-run.

```bash
./bootstrap apply --config config/your-machine.json \
  --cli-profiles core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp   # add ,gpu-nvidia with the gpu profile
./bootstrap apply --config config/your-machine.json --no-handoff   # host only
```

`verify` appends setup-dev-linux-wsl's `script/verify --target linux` (skipped with
`--no-handoff`).

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
  refuses to run as root.
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
just vm clean-cycle       # destroy the guest, rebuild, apply, verify, reboot, repeat
```

Grouped subcommands use a slash in make and a module in just, which spells the
same path with `::` or a space:

```bash
make vm/status           just vm status      # or: just vm::status
make vm/up               just vm up
make vm/clean-cycle      just vm clean-cycle
```

`make help` and `just --list vm` list them.

The VM cycle proves everything except GPU delivery and the desktop session —
the guest has no NVIDIA hardware and runs a server image.

## Documents

Start with [the document index](docs/README.md), or go straight to:

- [New machine runbook](docs/NEW-MACHINE.md) — the procedure for moving
- [Operations](docs/OPERATIONS.md) — commands, and keeping versions current
- [Inventory review](docs/INVENTORY-REVIEW.md) — every item and its decision
- [TASKS.md](TASKS.md) — what is unfinished

Keep private disk identifiers, inventories, credentials, backups and VM images
out of Git.
