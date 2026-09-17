# Validation and acceptance specification

The catalogue, shared bootstrap foundation and first approved package slice are
implemented. The dated evidence below identifies actual passes; other workstation
acceptance requirements remain future work.
`script/check-catalogue` checks the present static artifacts only; it does not install.
It uses Python 3 and jsonschema. The pinned controller QA graph is exercised in the guest. Missing required tools fail, never silently skip. jsonschema
is not a dependency of the future distribution-Python bootstrap preview.

Run the current static checks:

```bash
python3 -B script/check-catalogue     # catalogue, schemas, selections, generated documents
python3 -B script/check-manifest      # every selection delivered; every binary and key pinned
python3 -B -m unittest discover -s tests
```

or `just verify-static`. Guest acceptance is `just vm clean-cycle` (`make vm/clean-cycle`).

The optional `--mac-source PATH` argument audits provenance against the recorded Mac
checkout; ordinary validation and all future workstation commands need no Mac checkout.

## Static catalogue gate (P0)

- Validate JSON with duplicate-key rejection and the committed structural schemas.
- Require unique capability IDs, valid references, nonempty purpose/evidence/acceptance,
  and exact KEEP coverage in target; default differs only by selected GPU capabilities.
- Reject optional/pending/omit leakage and conflicting selected owners.
- Verify raw review SHA-256 and exact 45-row mapping; preserve raw decisions unchanged.
- Validate all three storage examples and relative selection references. Examples are
  review-only, not installer input. Standard split with /var/lib on root is also valid.
- Assert source/licence readiness is not claimed by unverified candidates. A selected
  unresolved group blocks installation, not catalogue normalization.
- Compare capability matrix with catalogue and source mappings. During provenance QA,
  compare Mac declarations at recorded commit; routine validation needs no Mac checkout.
- Reject broken relative documentation links and scan tracked artifacts for private data.

## Foundation (P1)

| Scenario | Required evidence |
|---|---|
| Pristine offline preview | Distribution tools only; no sudo/downloads/files/cache/venv/log writes; target selection agrees with apply |
| Missing initial tools | Actionable exit 2; no attempt to install before mount guard |
| Wrong/missing mounts | No APT, managed-home, environment or log writes before failure |
| Old /var/lib mounted correctly | Reject absent/invalid fresh-target handoff evidence; matching UUID alone never passes |
| Reordered disks / duplicate identities | Roles stay tied to physical identity; ambiguity fails before mutation |
| Invalid JSON/config | Duplicate keys, unknown keys/IDs, conflicting choices, placeholders and example input rejected before install |
| Noninteractive input | Closed/non-TTY stdin never hangs; missing user/privilege input is actionable |
| Shared report | Config/catalogue/selection provenance consistent across commands; failures outrank incomplete; secrets absent |
| Independent verify | Deliberate state errors fail; broken user runtime cannot trigger downloads or repair |
| Prerequisite integrity | Corrupt digest prevents execution; distribution module/controller interpreter split works |

## Role acceptance (P2–P4)

Deliver verification in the same change as each role. Test clean users and existing-file
conflicts; preserve unrelated settings and restore owned-file backups. Exercise editor
startup, root extensions and dependency accounting; shell parsing and runtime switching;
synthetic Git LFS checkout and work/personal identity; disabled signing without key;
throwaway signing/decryption and browser profile separation. Verify supported telemetry
opt-outs rather than assuming environment variables are effective.

Use a desktop session for GNOME/keyring/Remmina/Wayland checks. Missing session is
incomplete. No real connection profiles or secrets enter tests. Backups remain unscheduled.

Test Docker build/Compose, registry and build cache, fresh-login group access and actual
port exposure from a second guest. Verify selected k3d/kind workflows in disposable
project-owned clusters; plugin failures must fail required checks. Verify OpenHands
mounts/socket absence/loopback. Test isolated lab guests independently of installer VMs.

CPU-only tests require no NVIDIA hardware. A selected GPU disconnected is incomplete;
physical driver/container/workload, connected/disconnected boot and sleep/wake results
must be observed. DDC acceptance applies only when the optional capability is enabled.

## Operations and full acceptance (P5–P8)

- Update report with unavailable network is incomplete; no implicit environment sync.
- Allowed APT/Snap refresh remains compliant; wrong source and mismatched exact pin fail.
- Reject stale reviewed update candidates; test partial package failure and documented
  recovery. Configuration restore must not claim binary/package rollback.
- Full pristine system/desktop VM install, reboot, second apply and independent verify;
  test interruption and intentional drift. Strict tooling requirements may not skip.
- Standard single with /var/lib on root; standard split with and without separate
  /var/lib; transferred split prepared/missing/unprepared/old-state cases.
- P7 only: verify image and explicit disk targets in disposable VMs; populate a second
  transfer disk and prove partitions/data remain unchanged by installer.
- Synthetic ordinary-file, database and VM restores; real credentials/data stay manual.
- P8: physical target and representative development workflows; report pass/fail/
  incomplete separately and preserve old-system recovery backup through cutover.

## Current evidence

Last full cycle: **2026-09-17**, from a guest destroyed and rebuilt from the
signature-verified Ubuntu 26.04 image. **50 checks, no failures.**

| | |
|---|---|
| Apply from pristine | 685s |
| APT packages | 87/87 for the twelve installed groups, each from its declared source |
| Third-party repositories | 16/16, each key verified against its recorded fingerprint |
| Pinned release binaries | 27/27, SHA-256 verified on download |
| Snaps | 4/4 on their declared channel |
| VS Code extensions | 17/17 |
| krew plugins | 6/6 |
| Agent CLIs | Claude Code 2.1.273 and Copilot 1.0.85, present and unmodified |
| GNOME settings | 72/72 declared keys; 5 extensions on, 2 deliberately off |
| Migration plan | 167.6 GB across 389,518 files, nothing written |
| Migration rehearsal | 18,164 files / 4.08 GB copied, completeness proved by a second pass |
| Credential separation | 2,195 source credential files compared by content; none arrived |
| Reboot | Guest returned in 24s; every group verified again unchanged |
| Second apply | Repeatable, no change |
| Docker group | Deferred on first apply, effective after the reboot, `docker run` without sudo |

Host gates before the run: `check-catalogue`, `check-manifest` and the unit
tests, all passing — `make verify-static`.

## What no VM run can establish

- **GPU delivery.** The `gpu` group is excluded from guest acceptance because
  the guest has no NVIDIA hardware. The 595 open driver, its kernel modules and
  nvidia-container-toolkit are unproven until the physical machine.
- **A rendered desktop session.** The settings are written and read back, but
  the guest runs a server image, so appearance, keybindings, dock behaviour and
  suspend are unobserved.
- **The migration at full size.** Rehearsed at 4.08 GB against real data shapes;
  the real move is 167.6 GB across 389,518 files.

## History

Each acceptance run, and the defects it found, is recorded in
[the evidence log](evidence-log.md).
