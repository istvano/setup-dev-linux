# linux-os-setup

Reproducible Ubuntu 26.04 LTS workstation setup, plus a file migration for
moving to a new machine.

The repository holds a declarative record of what this workstation runs and an
installer that reproduces it elsewhere. New machine: install the manifest, copy
your files, authenticate by hand.

## Quick start

```bash
just verify-static                            # catalogue, manifest coverage, tests
just plan config/your-machine.json            # what would be installed; writes nothing
just install config/your-machine.json         # install it
just migrate config/your-machine.json newbox  # copy your files, from the old machine
```

A `Makefile` offers the same targets, for a machine that does not have `just`
on it yet — which includes a new one, before this repository installs it:

```bash
make verify-static
make plan CONFIG=config/your-machine.json
make install CONFIG=config/your-machine.json
make migrate CONFIG=config/your-machine.json HOST=newbox
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
| `binaries.json` | Third-party release binaries, each pinned to a version, URL and SHA-256 |
| `runtimes.json` | NVM/Node, SDKMAN/JVM, uv, agent CLIs |
| `shell.json` | Login shell, oh-my-zsh, starship, atuin |
| `dotfiles.json` | Files chezmoi manages, and files it deliberately does not |
| `desktop.json` | Curated GNOME settings, extensions and fonts |
| `plugins.json` | Editor extensions and kubectl plugins |
| `migrate.json` | Which home directories move, and what never moves |

The manifest is grouped by purpose — `core`, `dev`, `cloud`, `kubernetes`,
`containers`, `lab`, `gpu`, `desktop`, `media`, `productivity`, `ai`,
`network`, `security` — so an install can take part of it:

```bash
just install config/your-machine.json core,dev,kubernetes
```

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
- `install` never removes unrelated packages, never partitions or formats, and
  refuses to run as root.
- `install` is repeatable; a second run on a correct machine changes nothing.
- `verify` reads the system and reports drift. It never repairs.
- `migrate` never deletes on the destination, excludes credentials from the
  ordinary copy, and proves completeness with a second pass rather than
  assuming it.

## Storage layouts

| Layout | System disk | Data disk |
|---|---|---|
| Single disk | EFI, separate `/boot`, `/` and `/home`; `/var/lib` within `/` | Not required |
| Split system/data | EFI, separate `/boot` and `/` | `/home`; optionally separate `/var/lib` |

Disk roles come from verified stable identities in private configuration.
"System disk" and "data disk" never mean the first or second enumerated device.
No target disk encryption is selected. Automated physical-disk transfer was
withdrawn on 2026-09-16; files move by copy.

## Testing

```bash
just verify-static        # no VM needed
just vm clean-cycle       # destroy the guest, rebuild, apply, verify, migrate, reboot, repeat
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

- [New machine runbook](docs/NEW-MACHINE.md) — the procedure for moving
- [Inventory review](docs/INVENTORY-REVIEW.md) — every item and its decision
- [Machine manifest spec](specs/F13-machine-manifest.md) — contract and limits
- [File migration spec](specs/F14-file-migration.md) — contract and limits
- [Architecture](docs/ARCHITECTURE.md), [Decisions](docs/DECISIONS.md),
  [Operations](docs/OPERATIONS.md), [Testing](docs/TESTING.md)
- [TASKS.md](TASKS.md) — what is unfinished

Keep private disk identifiers, inventories, credentials, backups and VM images
out of Git.
