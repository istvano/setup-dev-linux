# setup-dev-linux host refactor Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** setup-dev-linux sets up only the Linux host (OS, drivers, desktop, firewall, groups) and hands the command line to setup-dev-linux-wsl `--target linux`; migration and CLI setup are gone and nothing is lost.

**Architecture:** Keep the Python controller (`bootstrap`, `script/workstation/`), the locked Ansible environment, the manifests and the VM harness (approach A). Remove migration and every CLI module/playbook/manifest entry; add `ansible/firewall.yml` + `script/workstation/firewall.py`, and `script/workstation/handoff.py` as the last apply stage; rename `install` to `apply` (alias kept), add a profile layer over the trimmed manifest groups with a printed "Profiles:" line.

**Tech Stack:** Python 3 (distribution Python, unittest), Ansible (locked controller venv), JSON manifests with schemas, just/Makefile, QEMU VM harness.

**Spec:** `docs/superpowers/specs/2026-11-26-linux-host-refactor-design.md` (approved).

**Prerequisite:** setup-dev-linux-wsl plan `docs/superpowers/plans/2026-11-26-linux-target-additions.md` is merged first (Docker, vendor apt incl. azure-cli/gcloud, Claude Code, Copilot, small tools), so no merged state loses a tool.

## Global Constraints

- Branch `host-refactor` (already holds the design). Commit per task with trailer `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.
- Gate after every task: `just verify-static` (equivalently `python3 -B script/check-catalogue && python3 -B script/check-manifest && python3 -B -m unittest discover -s tests`). Missing required tools fail, never skip.
- Ubuntu 26.04 LTS amd64; never run as root (existing `whole-bootstrap-root-forbidden`); elevation per step as today.
- Fresh installs only (decision 6): no cleanup of a machine provisioned by the old version, no upgrade test.
- This repository no longer runs chezmoi (setup-dev-linux-wsl owns it); desktop files the host owns are written by Ansible.
- Keep the repository's bars: pinned, hash-verified binaries; signed apt keys with recorded fingerprints; no download-and-run; JSON validated with duplicate-key rejection.
- The Anthropic apt key: one keyring file shared by claude-desktop and (installed by setup-dev-linux-wsl) claude-code, at `/etc/apt/keyrings/anthropic.asc`, so APT never sees one URI with two `Signed-By` values. Align the host's claude-desktop source to that keyring path.
- Docker, the docker group and the NVIDIA container toolkit are not installed by this repository (decision 3).
- Host profiles (exact names): `desktop`, `media`, `productivity`, `ai`, `network`, `lab`, `gpu`, `dev-gui`, `firewall`. Default: `desktop,media,productivity,ai,network,dev-gui,firewall`. Headless: any selection without the desktop set; `firewall` stays selectable on its own.
- Firewall values (exact): UFW enabled, `default deny incoming`, `default allow outgoing`, SSH allowed only with `--allow-ssh` (persisted in the config's `firewall.allow_ssh`); OpenSnitch installed and running with `"DefaultAction": "allow"` in `/etc/opensnitchd/default-config.json` (decision 9). Docker's published ports bypass UFW: say so in docs and in `verify` output when Docker is present.
- Handoff (exact): clone or update `~/workspace/setup-dev-linux-wsl` from `https://github.com/istvano/setup-dev-linux-wsl` (origin checked via `git config --get remote.origin.url`, ref resolved with `rev-parse --verify` then one `checkout --detach`), then run `./bootstrap apply --target linux` as the operator, interactively; pass `--profiles X` only when the operator gave `--cli-profiles X`.

## Review Focus

1. Running `apply` twice: every stage idempotent; the handoff on the second run updates the clone and re-runs bootstrap without passing a profile list that conflicts with the recorded one. Test in Task 6.
2. A headless selection (`--profiles firewall,gpu`): no desktop playbook, snap, GNOME setting or VS Code runs, and verify does not demand them. Test in Task 4.
3. `--allow-ssh` given once then omitted: the persisted choice holds (no silent SSH lock-out on the next run). Test in Task 5.
4. The handoff target directory exists but points at another origin or has local changes: stop with a clear message, never overwrite. Test in Task 6.
5. A manifest item removed in Task 2/3 that setup-dev-linux-wsl does not provide: the lossless table test fails. Test in Task 1.

---

### Task 1: The lossless table

**Files:** Create `docs/MOVED.md` (one row per CLI item this repository installs today: item, where it goes — `setup-dev-linux-wsl:<profile/file>` or `dropped:<DROPPED.md row>`), `tests/test_moved.py`, `tests/fixtures/manifest-before.json` (snapshot of every package, binary, repository, runtime, agent, snap, plugin and shell/dotfile item in today's manifests, generated by a small script you write once and commit the output of).

- [ ] Step 1: failing test `test_every_removed_item_is_accounted_for`: every item in the fixture that is absent from the current manifests has exactly one MOVED.md row with a destination; `test_moved_destinations_are_concrete` (each destination names a profile/file or a DROPPED row). It fails once Task 2/3 start removing items without rows.
- [ ] Step 2: generate the fixture; fill MOVED.md from the design's table (verify each destination exists on setup-dev-linux-wsl main at the time of writing; items not there become DROPPED rows with the reason, never silently omitted).
- [ ] Step 3: run the gate; expect pass (nothing removed yet).
- [ ] Step 4: commit `test: lossless table for items moving to setup-dev-linux-wsl`.

### Task 2: Remove migration and file copy

**Files:** Delete `script/workstation/migrate.py`, `tests/test_migrate.py`, `manifest/migrate.json`; modify `script/workstation/cli.py` (drop `migrate`, `--to`, `--secrets`, `--dry-run`, `--rsh`, `--remote-home`, `--only-trees`, `--source-home`), `justfile` and `Makefile` (drop migrate-plan, migrate, migrate-secrets; keep the just/make parity test green), `manifest/dotfiles.json` `never_managed` references to migration, docs (NEW-MACHINE.md migration sections, README "Quick start" migrate lines, ARCHITECTURE transfer-handoff paragraphs, TESTING transfer acceptance, CAPABILITY-MATRIX rows), catalogue entries that exist only for migration.

- [ ] Step 1: failing test `test_no_migration_surface`: `bootstrap migrate` is rejected as an unknown command; no file under script/, tests/, manifest/, justfile, Makefile mentions `migrate` or `rsync` (allow docs/DECISIONS.md history and the design/plan).
- [ ] Step 2-4: run, implement, gate.
- [ ] Step 5: commit `refactor: remove migration and file copy`.

### Task 3: Remove CLI setup

**Files:** Delete playbooks `ansible/{user-tools,sdkman,java-runtime,jvm-tools,mandrel,go-runtime,rust-runtime,python-user,node-runtime,npm-cli,opencode-runtime,codex-runtime,cline-runtime,user-environment}.yml` and their `script/workstation/*.py` modules, `script/apply-*` entry points and `tests/test_*` for them, their `locks/*`; delete `manifest/shell.json`, `manifest/dotfiles.json`, `manifest/runtimes.json` (or reduce runtimes to nothing and delete); in `manifest/packages.json` drop groups `core`, `cloud`, `kubernetes`, `containers`, `security` and the CLI members of `dev` (keep `code`, `dbeaver-ce`, `meld` as group `dev-gui`), drop `nvidia-container-toolkit` from `gpu`; in `manifest/binaries.json` keep only `zed`, `obsidian`; in `manifest/repositories.json` keep only vscode, google-chrome, slack, dbeaver, claude-desktop (keyring `anthropic`), chatgpt, ppa-obs, ppa-quickemu, nvidia driver sources if any; `manifest/plugins.json` keep `vscode_extensions`, drop `krew_plugins`; `manifest/system.json` drop the docker group; `script/workstation/controller.py` and `cli.py` drop every CLI branch (runtimes, user tools, user environment, npm agents, krew); trim `catalogue/` records and `profiles/*.json` selections to host scope while `script/check-catalogue` stays green; `script/update-report`, `script/resolve-*`, `script/check-manifest` for the remaining pins only.

- [ ] Step 1: failing tests: `test_no_cli_modules` (none of the deleted module names importable; controller never references their playbooks); `test_manifest_host_only` (exact remaining groups and binaries above; no `docker`, `nvidia-container-toolkit`, `chezmoi`); Task 1's lossless test covers every removed item.
- [ ] Step 2-4: run, implement, gate.
- [ ] Step 5: commit in two or three logical commits (`refactor: remove CLI runtimes and user environment`, `refactor: host-only manifests and catalogue`).

### Task 4: Profiles and the plan/apply/verify commands

**Files:** Modify `script/workstation/cli.py` (commands `plan`, `preflight`, `apply`, `verify`; `install` kept as an alias that prints "install is now apply"), `--profiles CSV` replacing `--manifest-groups` (old flag accepted as an alias), a profile catalogue `profiles/host.json` (`{"default": [...], "profiles": {"desktop": ["desktop"], "dev-gui": ["dev-gui"], ...}, "desktop_set": [...]}` mapping profile → manifest groups and the `firewall` stage), the printed first line `Profiles: <csv> (default <csv>; available <csv>; change with ./bootstrap apply --config <file> --profiles <list>)`; `justfile`/`Makefile` targets `plan`, `apply`, `verify` (keep `install` alias); controller stage list driven by profiles (desktop.yml, plugins.yml for VS Code, snaps only when the desktop set is selected).

- [ ] Step 1: failing tests: profile validation (unknown names rejected listing valid ones); default selection exact; headless selection runs no desktop/snaps/VS Code stage and verify skips them; the Profiles line exact; `install` aliases `apply`.
- [ ] Step 2-4: run, implement, gate.
- [ ] Step 5: commit `feat: host profiles and plan/apply/verify`.

### Task 5: Firewall

**Files:** Create `ansible/firewall.yml` (ufw package, defaults, enable, optional `ufw allow OpenSSH`; opensnitch package (check Ubuntu 26.04 archive first; if absent, a pinned, SHA-256 verified release .deb through the existing binaries/vendor-package mechanism) plus its UI for the desktop set, `/etc/opensnitchd/default-config.json` `DefaultAction` = `allow`, service enabled), `script/workstation/firewall.py` (`verify(config) -> list[check]`: reads `ufw status verbose` and the opensnitch config/service; notes Docker port bypass when `docker` is present), tests `tests/test_firewall.py`; modify cli/controller to run the stage when `firewall` is selected; config schema gains `firewall.allow_ssh` (bool, default false) and the `--allow-ssh` flag persists it.

- [ ] Step 1: failing tests: exact ufw defaults in the playbook; SSH rule only when allow_ssh; persisted allow_ssh honoured without the flag; opensnitch DefaultAction allow; verify parses fixture `ufw status verbose` outputs (active/inactive, with/without OpenSSH) and reports each; Docker-bypass note appears only when docker is installed.
- [ ] Step 2-4: run, implement, gate.
- [ ] Step 5: commit `feat: UFW and OpenSnitch firewall stage`.

### Task 6: Handoff to setup-dev-linux-wsl

**Files:** Create `script/workstation/handoff.py` (`run_handoff(user: str, ref: str = "main", cli_profiles: str | None = None) -> int` running the fixed git program and `./bootstrap apply --target linux` as the operator; `verify_cli(user) -> list[check]` running that repository's `script/verify --target linux`), tests `tests/test_handoff.py` (a local bare repository standing in for GitHub, as setup-dev-win's handoff test does); modify cli (`apply` ends with the handoff unless `--no-handoff`; `--cli-profiles`; `--linux-ref` default `main`; `verify` appends the CLI verify), docs.

- [ ] Step 1: failing tests: first run clones and runs bootstrap (stubbed) with `--target linux` and no `--profiles`; `--cli-profiles core,dev` passes `--profiles core,dev`; second run fetches and checks out the new tip; a clone with another origin or a dirty tree stops non-zero with a message naming the directory; an unknown ref stops with "unknown ref"; never runs as root; verify appends the CLI verify result and fails when it fails.
- [ ] Step 2-4: run, implement, gate.
- [ ] Step 5: commit `feat: hand off the command line to setup-dev-linux-wsl`.

### Task 7: Decisions, runbook and VM acceptance

**Files:** `docs/DECISIONS.md` (new decisions: host role and the two-repository split; migration removed; CLI moved with MOVED.md; firewall; Docker owned by setup-dev-linux-wsl with ports reachable and UFW bypass; chezmoi ownership; fresh installs only; desktop/headless profiles), `README.md` (new purpose and quick start: plan, apply, verify), `docs/ARCHITECTURE.md`, `docs/NEW-MACHINE.md` (fresh Ubuntu → apply → handoff → login again for groups), `docs/OPERATIONS.md`, `docs/TESTING.md` (VM clean-cycle now runs apply including the handoff; network required), `docs/CAPABILITY-MATRIX.md` regenerated, `script/test-vm`/`script/vm` adjusted so the clean cycle runs `apply` with the handoff.

- [ ] Step 1: write the docs; every command, profile name and flag matches the code.
- [ ] Step 2: gate; expect pass.
- [ ] Step 3: commit `docs: setup-dev-linux as the Linux host repository`.
