set shell := ["bash", "-euo", "pipefail", "-c"]

# Grouped subcommands live in a module: `just vm status`, or `just vm::status`.
# just spells a module path with "::" or a space, never "/", so the Makefile's
# `make vm/status` is `just vm::status` here. List them with `just --list vm`.

[doc("Disposable test VM: fetch, reset, up, status, stop, ssh, accept, foundation, clean-cycle")]
mod vm

[doc("Version refresh: report, apply, binaries, keys")]
mod update 'just/update.just'

default:
  @just --list

# --- Static checks ----------------------------------------------------------

# Validate the catalogue, schemas, selections and generated documents.
check:
  python3 -B script/check-catalogue

# Prove every reviewed selection has a delivery and every binary is pinned.
check-manifest:
  python3 -B script/check-manifest

test:
  python3 -B -m unittest discover -s tests

# Everything that runs without a VM.
verify-static: check check-manifest test

# --- This machine -----------------------------------------------------------

# Read this workstation and write a raw inventory snapshot.
inventory OUT="/tmp/workstation-inventory.json":
  python3 -B script/inventory --output {{OUT}}

# Regenerate docs/INVENTORY-REVIEW.md from the inventory and the Mac baseline.
review MAC="../mac-os-setup" OUT="/tmp/workstation-inventory.json":
  python3 -B script/inventory --output {{OUT}}
  python3 -B script/inventory-review --inventory {{OUT}} --mac-source {{MAC}}

# Regenerate manifest/desktop.json from this machine's GNOME settings.
desktop-manifest OUT="/tmp/workstation-inventory.json":
  python3 -B script/inventory --output {{OUT}}
  python3 -B script/build-desktop-manifest --inventory {{OUT}} --dropped-apps kiro

# --- A new workstation ------------------------------------------------------

# Show what would be installed, changing nothing.
plan CONFIG:
  ./bootstrap plan --config {{CONFIG}}

# Check the live machine before any write.
preflight CONFIG:
  ./bootstrap preflight --config {{CONFIG}}

# Install the manifest.
install CONFIG GROUPS="":
  ./bootstrap install --config {{CONFIG}} {{ if GROUPS == "" { "" } else { "--manifest-groups " + GROUPS } }}

# Report drift without repairing it.
verify CONFIG:
  ./bootstrap verify --config {{CONFIG}}

# --- Moving here from the old machine ---------------------------------------

# Preview the copy to HOST, writing nothing.
migrate-plan CONFIG HOST:
  ./bootstrap migrate --config {{CONFIG}} --to {{HOST}} --dry-run

# Copy the declared trees to HOST and prove the copy is complete.
migrate CONFIG HOST:
  ./bootstrap migrate --config {{CONFIG}} --to {{HOST}}

# Copy credential paths to HOST. Deliberately separate from migrate.
migrate-secrets CONFIG HOST:
  ./bootstrap migrate --config {{CONFIG}} --to {{HOST}} --secrets

# --- Disposable test VM -----------------------------------------------------
# See vm/mod.just: just vm --list
