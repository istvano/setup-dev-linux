# Same targets as the justfile, for machines without `just` installed —
# including a new one, before `just` itself is on it.
#
# Targets that act on a machine take variables rather than positional
# arguments:  make apply CONFIG=config/mine.json PROFILES=desktop,dev-gui
#
# Grouped subcommands use a slash:  make vm/up, make vm/status. They are .PHONY,
# so make does not look for a file of that name inside the vm directory.

SHELL := /bin/bash
.SHELLFLAGS := -eu -o pipefail -c
.DEFAULT_GOAL := help

PYTHON ?= python3 -B
BOOTSTRAP ?= ./bootstrap
OUT ?= /tmp/workstation-inventory.json
MAC ?= ../mac-os-setup
# GROUPS is the former name of PROFILES.
GROUPS ?=
PROFILES ?= $(GROUPS)
ARGS ?=

# Fail with a usable message instead of passing an empty flag to a command that
# would then act on the wrong thing.
define require
	@if [ -z "$($(1))" ]; then \
		echo "error: $(1) is required — e.g. make $(2) $(1)=$(3)" >&2; \
		exit 2; \
	fi
endef

.PHONY: help
help: ## List the available targets
	@echo "linux-os-setup — make targets (same set as the justfile)"
	@echo
	@grep -hE '^[a-zA-Z_/-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  \033[1m%-18s\033[0m %s\n", $$1, $$2}'
	@echo
	@echo "Variables: CONFIG, PROFILES, OUT, MAC, ARGS"

# --- Static checks ----------------------------------------------------------

.PHONY: check
check: ## Validate the catalogue, schemas, selections and generated documents
	$(PYTHON) script/check-catalogue

.PHONY: check-manifest
check-manifest: ## Prove every selection has a delivery and every binary is pinned
	$(PYTHON) script/check-manifest

.PHONY: test
test: ## Run the unit tests
	$(PYTHON) -m unittest discover -s tests

.PHONY: verify-static
verify-static: check check-manifest test ## Everything that runs without a VM

# --- This machine -----------------------------------------------------------

.PHONY: inventory
inventory: ## Read this workstation into a raw inventory snapshot
	$(PYTHON) script/inventory --output $(OUT)

.PHONY: review
review: ## Regenerate docs/INVENTORY-REVIEW.md from this machine and the Mac baseline
	$(PYTHON) script/inventory --output $(OUT)
	$(PYTHON) script/inventory-review --inventory $(OUT) --mac-source $(MAC)

.PHONY: desktop-manifest
desktop-manifest: ## Regenerate manifest/desktop.json from this machine's GNOME settings
	$(PYTHON) script/inventory --output $(OUT)
	$(PYTHON) script/build-desktop-manifest --inventory $(OUT) --dropped-apps kiro

.PHONY: update/report
update/report: ## Show what a version refresh would change; writes nothing
	$(PYTHON) script/update-report

.PHONY: update/apply
update/apply: ## Re-pin everything that can be re-pinned automatically, then check
	$(PYTHON) script/update-report --write
	$(PYTHON) script/check-catalogue
	$(PYTHON) script/check-manifest
	$(PYTHON) -m unittest discover -s tests

.PHONY: update/binaries
update/binaries: ## Re-pin the third-party release binaries only
	$(PYTHON) script/resolve-binaries --write

.PHONY: update/keys
update/keys: ## Re-record the repository signing-key fingerprints only
	$(PYTHON) script/resolve-repository-keys --write

# --- A new workstation ------------------------------------------------------

.PHONY: plan
plan: ## Show what would be installed, changing nothing (CONFIG=, optional PROFILES=)
	$(call require,CONFIG,plan,config/mine.json)
	$(BOOTSTRAP) plan --config $(CONFIG)$(if $(strip $(PROFILES)), --profiles $(PROFILES),)

.PHONY: preflight
preflight: ## Check the live machine before any write (CONFIG=)
	$(call require,CONFIG,preflight,config/mine.json)
	$(BOOTSTRAP) preflight --config $(CONFIG)

.PHONY: apply
apply: ## Set up the host (CONFIG=, optional PROFILES=gpu,firewall)
	$(call require,CONFIG,apply,config/mine.json)
	$(BOOTSTRAP) apply --config $(CONFIG)$(if $(strip $(PROFILES)), --profiles $(PROFILES),)

.PHONY: install
install: apply ## Former name of apply

.PHONY: verify
verify: ## Report drift without repairing it (CONFIG=, optional PROFILES=)
	$(call require,CONFIG,verify,config/mine.json)
	$(BOOTSTRAP) verify --config $(CONFIG)$(if $(strip $(PROFILES)), --profiles $(PROFILES),)

# --- Disposable test VM -----------------------------------------------------

.PHONY: vm/fetch
vm/fetch: ## Fetch and verify the Ubuntu image
	$(PYTHON) script/vm fetch

.PHONY: vm/reset
vm/reset: ## Discard the guest and its disks
	$(PYTHON) script/vm reset

.PHONY: vm/up
vm/up: ## Build a fresh guest from the verified image and boot it
	$(PYTHON) script/vm prepare
	$(PYTHON) script/vm start

.PHONY: vm/status
vm/status: ## Report whether the guest is prepared and running
	$(PYTHON) script/vm status

.PHONY: vm/stop
vm/stop: ## Stop the guest
	$(PYTHON) script/vm stop

.PHONY: vm/ssh
vm/ssh: ## Run a command in the guest (ARGS='uptime')
	$(PYTHON) script/vm ssh $(ARGS)

.PHONY: vm/accept
vm/accept: ## Apply the manifest in the guest, reboot and repeat
	$(PYTHON) script/test-manifest-vm

.PHONY: vm/foundation
vm/foundation: ## Run the F01-F07 guest suite: storage preflight negatives and runtime fixtures
	$(PYTHON) script/test-vm $(ARGS)

.PHONY: vm/clean-cycle
vm/clean-cycle: vm/reset vm/up ## Destroy the guest, rebuild it, apply and accept
	$(PYTHON) script/test-manifest-vm
