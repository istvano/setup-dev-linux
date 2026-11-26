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

or `just verify-static`. Guest acceptance is `just vm clean-cycle` (`make vm/clean-cycle`),
described below. `tests/test_vm_harness.py` pins the commands the harness runs in the guest,
so a harness change is tested on any host; only a Linux machine with KVM can boot the guest.

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
| Reordered disks / duplicate identities | Roles stay tied to physical identity; ambiguity fails before mutation |
| Invalid JSON/config | Duplicate keys, unknown keys/IDs, conflicting choices, placeholders and example input rejected before install |
| Noninteractive input | Closed/non-TTY stdin never hangs; missing user/privilege input is actionable |
| Shared report | Config/catalogue/selection provenance consistent across commands; failures outrank incomplete; secrets absent |
| Independent verify | Deliberate state errors fail; verification cannot trigger downloads or repair |
| Prerequisite integrity | Corrupt digest prevents execution; distribution module/controller interpreter split works |

## Role acceptance (P2–P4)

Deliver verification in the same change as each role. Test clean users and existing-file
conflicts; preserve unrelated settings and restore owned-file backups. Exercise editor
startup, root extensions and dependency accounting, and browser profile separation.
Verify supported telemetry opt-outs rather than assuming environment variables are
effective. Shell, runtime, Git identity and signing acceptance belong to
setup-dev-linux-wsl.

Use a desktop session for GNOME/keyring/Remmina/Wayland checks. Missing session is
incomplete. No real connection profiles or secrets enter tests. Backups remain unscheduled.

Docker, Kubernetes tooling and their acceptance belong to setup-dev-linux-wsl. Test
isolated lab guests independently of installer VMs.

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
  /var/lib.
- Synthetic ordinary-file, database and VM restores; real credentials/data stay manual.
- P8: physical target and representative development workflows; report pass/fail/
  incomplete separately and preserve old-system recovery backup through cutover.

## VM acceptance cycle

`just vm clean-cycle` destroys the guest, rebuilds it from the signature-verified
Ubuntu 26.04 image and runs `script/test-manifest-vm`, which runs both repositories on
one guest, the way the operator does (D030 in [DECISIONS.md](DECISIONS.md)):

1. `apply` with every host profile except `gpu`
   (`desktop,media,productivity,ai,network,lab,dev-gui,firewall`) and `--allow-ssh`,
   ending with the handoff. The guest has no terminal, so this first apply passes
   `--cli-profiles` with the former command-line set
   (`core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp`)
   and a throwaway identity; setup-dev-linux-wsl then runs `--non-interactive`.
2. Verify, reading the installed system: packages, pinned binaries, snaps, repository
   keys, VS Code extensions, GNOME settings; UFW enabled with incoming denied, outgoing
   allowed and the `OpenSSH` rule present; OpenSnitch installed and running, its daemon
   and UI defaults seeded to allow and the seeding recorded in `state.json`;
   `sudo apt-get update` and `apt-get check` with no warning, error or `Signed-By`
   conflict (claude-desktop registers its own source and setup-dev-linux-wsl adds
   Anthropic's for Claude Code); `bootstrap verify` with no failed check and a passing
   `cli:verify`.
3. Reboot, verify again, then `apply` a second time with no `--cli-profiles` and no
   identity: setup-dev-linux-wsl uses what it recorded, and the run must not conflict
   with it.

The guest needs network access: setup-dev-linux-wsl is cloned from GitHub and installs
from Homebrew and vendor repositories. `script/test-manifest-vm --skip-handoff` keeps a
host-only cycle; `--groups LIST` selects other host profiles (add `firewall` only with
`--allow-ssh`, which the harness passes for you). The private log is
`vm/state/manifest-test.log`.

`script/test-vm --controller` stays controller-only: it applies the `firewall` profile
alone with `--allow-ssh --no-handoff`, twice, and runs the pinned QA and lint.

### VM acceptance checklist

Automated by the cycle above:

- [ ] Both repositories on one guest: `handoff` passed on the first apply, `cli:verify`
  passed in `bootstrap verify`.
- [ ] `apt-get update` and `apt-get check` clean with both repositories' sources.
- [ ] OpenSnitch allow mode seeded once: daemon `DefaultAction` `allow`, UI
  `default_action=1`, both flags in `state.json`.
- [ ] UFW enabled, default deny incoming, allow outgoing, SSH allowed as chosen.
- [ ] A second `apply` after the reboot is idempotent and passes no conflicting
  `--profiles` to setup-dev-linux-wsl.

By hand, in the same guest after the cycle (`./script/vm ssh`, or the desktop fixture
for a session):

- [ ] **OpenSnitch UI autostart**: after `vm/desktop-fixture.py` gives the guest a
  GNOME session and automatic login, the OpenSnitch UI is running in that session and
  connected to the daemon.
- [ ] **UFW with `lab`**: start a libvirt guest on the default network inside the test
  guest (nested KVM) and confirm it gets an address from virbr0's DHCP and resolves
  names, with UFW enabled.
- [ ] **Ctrl-C during the bootstrap**: from an interactive SSH session with a terminal
  (`ssh -t`), run `apply` and press Ctrl-C while setup-dev-linux-wsl's bootstrap is
  running. `apply` prints one `apply: interrupted; re-running is safe` line, no
  traceback, and exits 130 (`echo $?`); a following `apply` completes.
- [ ] **Interactive first run**: on a fresh guest, run `apply` from a terminal without
  `--cli-profiles` or an identity: the `hint:` line appears before the host stages and
  again before the bootstrap, and setup-dev-linux-wsl prompts for the git identity.

## Current evidence

Last full cycle: **2026-09-17**, from a guest destroyed and rebuilt from the
signature-verified Ubuntu 26.04 image. **50 checks, no failures.** That run predates
the host refactor (2026-11-26): it still installed the command-line groups, krew
plugins, agent CLIs and Docker that setup-dev-linux-wsl now owns. No cycle has run
since: the two-repository cycle, the firewall stage and the handoff have no guest
evidence yet.

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
| Reboot | Guest returned in 24s; every group verified again unchanged |
| Second apply | Repeatable, no change |
| Docker group | Deferred on first apply, effective after the reboot, `docker run` without sudo |

Host gates before the run: `check-catalogue`, `check-manifest` and the unit
tests, all passing — `make verify-static`.

## What no VM run can establish

- **GPU delivery.** The `gpu` group is excluded from guest acceptance because
  the guest has no NVIDIA hardware. The 595 open driver and its kernel modules
  are unproven until the physical machine.
- **A rendered desktop session.** The settings are written and read back, but
  the guest runs a server image, so appearance, keybindings, dock behaviour and
  suspend are unobserved, and so is the OpenSnitch UI without the desktop fixture.
- **The Docker port exposure on a real network.** Published ports bypass UFW by
  design (D027); the guest's user-mode network does not show what a LAN peer sees.

## History

Each acceptance run, and the defects it found, is recorded in
[the evidence log](evidence-log.md).
