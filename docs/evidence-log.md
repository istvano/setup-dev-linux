# Evidence log

Every acceptance run, in order, with what it proved and what it found. Kept
separate from [TESTING.md](TESTING.md), which states what must be tested and
records the current result; this is the history behind it.

Entries are not edited after the fact. Where a design was later withdrawn the
entries stay, marked, because they record work that was done and tested.

## Historical initial P0 validation — 2026-09-12

Observed results before the later Java/shell confirmations and pre-build review:

- `python3 -B script/check-catalogue`: passed for 251 capability entries, 171 target
  selections, the three structural schemas and three storage examples, raw-review
  hash, catalogue/matrix mappings and relative documentation links.
- `python3 -B script/check-catalogue --mac-source PATH`: passed against Mac commit
  `31344724d99b4150cb7ac44b2646fc8554c60a5e`, including all 146 profile declarations,
  25 extension declarations and complete source-file coverage for chezmoi/script.
- `python3 -B -m unittest discover -s tests -v`: 20 tests passed. These cover omitted
  KEEP entries, optional/pending leakage, duplicate IDs/JSON keys, unknown fields,
  false delivery-readiness claims, storage layouts/roles/receipts, placeholders,
  GPU selection consistency and explicit optional-selection conflicts.
- Artifact whitespace and private-key-marker checks passed. This limited marker
  check is not a full secret scan; the pinned secret-scanning CI gate remains P1 work.

The catalogue records 171 KEEP, 66 OPTIONAL, 10 PENDING and 4 OMIT entries. Its 231
package/extension entries still have unverified delivery metadata; 20 behavior entries
have no package-delivery status. Candidate sources, licences, versions and integrity
have not passed installation validation. No VM, package, service, desktop, GPU, physical
storage or production restore test was run, and no commit/push was performed by this work.

## Pre-build review validation — 2026-09-13

- `python3 -B script/check-catalogue`: passed with 251 capabilities, 173 target
  selections, three storage examples, 155 selected delivery review records,
  confirmed user-environment preferences, schemas and generated document equality.
- `python3 -B -m unittest discover -s tests -v`: **39 tests passed**. New negative
  cases reject incomplete/duplicate source coverage, false review approval,
  malformed/missing digests, wrong Ubuntu suites, extension identity/version
  mismatches, Java/plugin preference drift, committed proxy values and changed
  matrix mappings/notes/extra rows.
- The read-only `--mac-source` audit passed against the recorded commit. It reads
  Git objects at that commit rather than relying on the checkout's current files.
- The 17 selected VSIX archives were downloaded as data, opened as ZIP archives,
  and their root identities/versions checked against Marketplace metadata. All
  17 SHA-256 values matched published Marketplace values. No extension was executed
  or installed, and child dependencies were not validated by this root check.
- Raw-review SHA-256 remains
  `d6e40f209682c5bdd1b792acc2a07a306c37729e2602509299150544be71612a`.
- `git diff --check` passed for tracked changes. Most P0 artifacts remain untracked;
  this command alone does not check them. No repository commit or push was made.

Tests used the existing Python environment with jsonschema **4.19.2**.
`locks/qa-requirements.txt` was separately resolved with hashes for jsonschema
**4.26.0** and its dependency closure, targeting Python 3.14, without installing
the environment. Verification in that pinned environment remains unfinished.

At that checkpoint the decision counts were 173 KEEP, 64 OPTIONAL, 10 PENDING and 4 OMIT.
Delivery status remains unverified; source observations and published hashes are
not install or licence approvals. No build, workstation install, VM, reboot,
idempotence, actual native-image project, physical-device or restoration test ran.

Regenerate human-readable projections after editing their JSON sources:

```bash
python3 -B script/render-matrix --write
python3 -B script/render-source-review --write
```

Both renderers use only the standard library. They write only with explicit
`--write`; static checking never downloads or regenerates them automatically.

## Review decisions D013–D015 — 2026-09-13

After selecting reviewed current stable tools, deferring OpenHands and confirming
that no current projects exist, the checker and all **42 tests passed**. Counts are
251 capabilities: 172 KEEP, 65 OPTIONAL, 10 PENDING and 4 OMIT, with 154 selected
delivery review records. New checks cover version-policy preservation, OpenHands
exclusion from both initial profiles and rejection of assumed existing-project
validation. Synthetic workflow tests are planned, not yet implemented or run.


## Foundation and first package slice — 2026-09-13

The disposable Ubuntu 26.04 amd64 KVM guest passed
`./script/test-vm --controller --packages --reboot`. The source image signature and
SHA-256 were verified against the committed image lock. Cloud-init reports done,
with valid user/network schemas and no recoverable initialization errors.

- Standard split synthetic disks with /var/lib on root passed live storage checks;
  a wrong /home UUID rejected installation before controller work.
- Locked uv/Python/Ansible acquisition, repeat apply, pinned QA and offline Ansible
  lint passed. Controller integrity remained valid after QA and a real guest reboot.
- Git, curl and jq applied successfully twice. A disposable Git index, loopback HTTP
  fetch and jq JSON extraction passed without credentials or external projects.
- Deliberate guest jq removal caused independent verification to fail without
  reinstalling it. Explicit reapply restored it and verification passed.
- The package suite repeated successfully after reboot. Full-profile installation
  still reports the remaining source/role gates as failures or incomplete.
- GNOME 50.1 and gdm3 run in the guest, with an actual test-user desktop session and
  captured screenshot. Desktop packages were test-image provisioning, not delivered
  by the production desktop role.

Guest testing found and corrected invalid cloud-init key-generation schema, a
reboot-volatile repository path, retrying failed acceptance instead of only SSH
readiness, and QA-generated controller bytecode drift. Private logs/images remain
under ignored vm/state and vm/disks. No physical host package installation, disk
formatting or production migration was performed.

This proves the tested foundation and three-package workflows, not the complete
172-capability workstation. Other layouts, transfer handoff, remaining source and
role delivery, desktop integrations, runtimes, containers, updates, restoration and
physical workflows remain unfinished in TASKS.md.


## F05 CLI extension and stronger verification — 2026-09-13

The approved package suite now includes Git LFS, ripgrep and ShellCheck, for six
packages total. Their guest workflows passed before and after reboot: Git LFS
clean/smudge round-tripped a local payload, ripgrep exercised match/no-match behavior,
and ShellCheck accepted the valid fixture and reported SC2086 for the invalid one.
The repeat-apply check asserts zero changes in Ansible's recap. Verification also
passes with the controller directory temporarily absent and does not recreate it.

The package implementation now resolves selected roots together in memory and rejects
untrusted/wrong-suite dependency candidates, removals and broken solutions before the
combined APT transaction. Installed-state checking additionally requires fully
installed dpkg status; matching metadata cannot make a half-configured package pass.
See the final validation checkpoint below for the tested code revision's results.


### Foundation validation checkpoint (before F06/F07)

- Host: catalogue/schema/generated-document checks and all **94 behavioral tests passed**.
- Guest: `./script/test-vm --controller --packages` passed on the final code, including
  all **94 tests** in the locked controller environment and Ansible lint with zero
  failures/warnings across both playbooks.
- `./script/test-vm --controller --packages --reboot` passed with the dependency-source
  check and combined transaction. The subsequent fully-installed dpkg-state refinement
  passed the final non-reboot suite and its installed/half-configured/unpacked fixtures.
- The source fingerprint below covers bootstrap, pyproject/uv.lock, guest fixtures/image
  lock and regular non-private files in script/tests/ansible/catalogue/config/profiles/locks.
  It is SHA-256 of sorted relative-path + NUL + file-SHA-256 + newline records:
  `996ac854f600584760f5c92e952a7127230cb9fc86b6b8eba2c788ff0f82d16e`.
- Original source-review bytes retain their recorded SHA-256; `git diff --check` passed.
  No commit or push occurred. The disposable VM is left running for continued work.

At this checkpoint F06 had a specification but no user-file implementation.
The later F06/F07 checkpoint below supersedes that implementation status. Remaining package coverage and system-security policy also remain open.


## F06/F07 shell, Git, Node and pnpm checkpoint — 2026-09-14

The saved disposable Ubuntu 26.04 VM survived the physical host restart and was
started using its existing disks. No VM recreation or host installation was needed.
`./script/test-vm --controller --packages --user-environment` passed with all
**115 behavioral tests** and offline Ansible lint across five playbooks. The selection
used nine APT packages, four immutable upstream tools, Node and three user behaviors.

- Chezmoi repeat apply reported zero changes; verification passed with the controller
  temporarily absent. Existing unrelated shell content survived. Managed drift failed
  verification without repair; explicit reapply and private backup restoration passed.
- Fresh Zsh loaded the selected plugins once. Proxy on/off preserved unset state,
  values and export attributes, including repeated activation and invalid private input.
- Synthetic personal/work Git identity scopes and actual configured Git LFS filtering
  passed. No production identities, repositories or credentials were used.
- NVM/Node passed offline local npm dependency install, test and build, `.nvmrc`
  selection, `nvm exec`, deactivation/default restoration and wrong-default drift
  detection with private backup on explicit repair. These tests also passed after a
  guest reboot in the preceding 113-test snapshot.
- pnpm passed offline local dependency install, frozen-lockfile reinstall, test/build
  and executable availability after NVM deactivation. This latest pnpm addition has
  not yet been exercised after reboot or with native Node addons.
- The initial pnpm manifest omitted archive hardlinks. Installation correctly rejected
  that payload; the manifest now covers hardlink contents and has a regression test.
- Modified Oh My Zsh payload failed verification and installation refused replacement;
  restoring the fixture bytes recovered verification.

These are synthetic feature tests, not full workstation acceptance or real-project
compatibility. SDKMAN/JVM, other application roles, security policy, other storage
layouts/transfer handoff and physical workflows remain unfinished.

## SDKMAN and four-JDK role checkpoint — 2026-09-14

`./script/test-vm --controller --packages --user-environment --reboot` passed with
**134 behavioral tests** on host and guest. Offline Ansible lint reported zero
failures/warnings across all seven playbooks. The runner now discovers all Ansible
playbooks so later roles cannot be omitted from lint by a stale explicit list.

- SDKMAN CLI 5.23.0/native 0.7.35 local-registration experiments passed in Bash and
  Zsh. The production manager role passed repeat apply, fresh shell version output,
  read-only verification and refusal to overwrite deliberate module drift.
- The four reviewed Temurin/Microsoft 21/25 archives compiled and ran a synthetic
  program with expected vendor/version/JAVA_HOME. The isolated source experiment
  covered Bash and Zsh; the managed role covered a fresh Zsh session.
- Temurin 25 remained the global default during shell selection. Deliberately making
  Temurin 21 the default failed verification without repair; explicit reapply restored
  Temurin 25 and preserved the previous link in a private JSON backup.
- The managed selection passed twice and with the controller temporarily absent.
  SDKMAN/Java, Node/npm, pnpm, shell/Git, backup restoration and drift checks repeated
  successfully after a real guest reboot. This closes the previous pnpm reboot gap.

Source/implementation details: [SDKMAN](SOURCE-EVIDENCE.md#sdkman), [Java](SOURCE-EVIDENCE.md#java-temurin-and-microsoft-openjdk).
This does not cover Mandrel native-image, Maven/Gradle/Kotlin builds, remaining roles,
full workstation acceptance or physical hardware. Subsequent checkpoints extend it.

## Maven, Gradle and Kotlin checkpoint — 2026-09-14

`./script/test-vm --controller --packages --user-environment --reboot` passed with
**142 behavioral tests**, zero Ansible lint failures/warnings across eight playbooks,
and successful repeat acceptance after guest reboot.

- Maven 3.9.16 resolved the synthetic project's fixture dependencies with strict
  checksums, executed a JUnit test, packaged the application and ran the JAR contents.
  A deliberately failing assertion produced a Surefire failure; restoring the test
  passed an offline package run using the temporary fixture cache.
- Gradle 9.7.1 built and ran the local Java fixture offline; Kotlin 2.4.20 compiled a
  runnable JAR and its output matched. Their paths remained visible while Java
  switched to Microsoft 21, then back to the Temurin 25 default.
- Default drift failed independent verification without repair. A dangling Maven
  default exposed SDKMAN's copy fallback; the wrapper fix backs up and removes only
  the dangling managed link before SDKMAN recovery. Regression tests cover both Java
  and tool defaults. The corrected guest recovery passed before and after reboot.
- All existing Node/pnpm, Java, shell/Git, private backup and immutable-drift acceptance
  repeated successfully. No real projects or credentials were used.

Source and fixture limits are in [JVM-TOOLS-REVIEW.md](SOURCE-EVIDENCE.md#maven-gradle-and-kotlin).
Mandrel/native prerequisites were not part of this 142-test checkpoint. Their later
implementation and host tests must not be confused with guest native-build success.

## Mandrel native-image checkpoint — 2026-09-14

`./script/test-vm --controller --user-environment --reboot` passed with **154
behavioral tests**, zero Ansible lint failures/warnings across nine playbooks, and
the complete feature suite repeated after a real guest reboot.

- The role installed only the three scoped Ubuntu prerequisites selected by Mandrel,
  verified the 25.0.4.1-Final archive and registered it as an additional SDKMAN Java
  candidate. Temurin 25 remained the global default.
- A fresh managed Zsh selected Mandrel, compiled Java, created an amd64 ELF executable
  using `native-image --no-fallback -O1` with a 3 GiB build heap, ran it and checked
  its output. It then restored the Temurin 25 shell selection.
- Removing the guest's `g++` metapackage caused independent Mandrel verification to
  fail without repair. Explicit installation restored the reviewed prerequisite and
  verification passed. Disabled Mandrel produces no prerequisite records in unit tests.
- Payload/registration and prerequisite failure fixtures, corrupt-download placement
  boundaries and capability/prerequisite mapping validation passed. The original
  source-review evidence file retained its recorded SHA-256.

This proves a small native executable on the disposable Ubuntu guest. It does not
prove Quarkus, arbitrary native libraries or existing projects. See
[Mandrel review](SOURCE-EVIDENCE.md#mandrel) for source/licence and Ubuntu package details.

## Go runtime checkpoint — 2026-09-14

`./script/test-vm --controller --user-environment` passed with **158 behavioral
tests** and zero Ansible lint failures/warnings across ten playbooks.

- The exact Go 1.27.1 Linux amd64 archive and all 15,639 installed entries were
  verified before and after placement under the managed user-tool directory.
- A fresh managed Zsh reported the expected version and linux/amd64 target. A local
  synthetic module initialized, tested, built and ran with module networking and
  automatic toolchain acquisition disabled.
- Deliberate VERSION-file drift failed independent verification without repair.
  Installation refused to replace the changed payload; restoring the original fixture
  bytes recovered verification.
- Existing Node/pnpm, SDKMAN/JVM, Mandrel, shell/Git and immutable-tool acceptance
  repeated successfully. No credentials or real projects were used.

The combined Rust runtime checkpoint below repeated this Go acceptance after reboot.
External modules, private proxies, CGO libraries, cross-compilation and real-project
compatibility remain unverified. Source and delivery details are in [Go review](SOURCE-EVIDENCE.md).

## Rust and combined runtime reboot checkpoint — 2026-09-14

`./script/test-vm --controller --user-environment --reboot` passed the complete suite
before and after a real reboot. Each cycle ran **167 behavioral tests** and reported
zero Ansible lint failures/warnings across 11 playbooks.

- rustup 1.29.1 installed the minimal Rust 1.98.1 toolchain solely from the exact
  locally staged manifest and Cargo/rust-std/rustc components. Two Ansible applies and
  independent verification passed without redownload or repair.
- A fresh managed Zsh reported the exact rustup, rustc and Cargo versions and state
  paths. A dependency-free Cargo project generated its lock offline, tested, built and
  ran an amd64 ELF executable with registry networking disabled. Its exact project
  toolchain pin resolved correctly, and Node selection did not hide Rust commands.
- Modified rustc bytes and a wrong default each failed verification without repair.
  Installation refused the modified payload; restoring the fixture recovered it.
  Removing the shared `g++` package made both Rust and Mandrel fail, and the explicit
  package apply restored their prerequisite.
- Go's version/build/drift suite and all earlier Node/pnpm, SDKMAN/JVM, Mandrel,
  shell/Git, backup and immutable-tool cases also passed after reboot.

No registry credentials, external crates or real projects were used. Cross targets,
native dependencies and private registries remain unverified. Source, licence and
state ownership details are in [Rust review](SOURCE-EVIDENCE.md).

## User Python/uv and OpenCode combined reboot checkpoint — 2026-09-15

`./script/test-vm --controller --user-environment --reboot` passed before and after
a real Ubuntu 26.04 guest reboot. Each cycle ran **181 behavioral tests**; offline
Ansible lint reported zero failures/warnings across all **13 playbooks**. The
controller and selected user roles applied twice in each cycle, followed by
independent read-only verification.

- The managed user uv 0.12.13 and Python 3.14.7 interpreter passed exact archive,
  binary and complete 4,571-entry payload checks. A synthetic local-wheel project
  created its lock and venv, ran unit tests and executed offline. An uv-only profile
  did not acquire Python in host behavioral tests. The Python tree is sealed against
  import-generated bytecode: an earlier unsealed guest run added 63 files and
  changed three bundled bytecode files; those fixture changes were restored from
  locked bytes before the final two-cycle checkpoint.
- Changing the Python-generated `_sysconfigdata` prefix or locked content failed
  verification without repair. Explicit fixture restoration recovered it.
- OpenCode 1.18.31 reported its version and help in private disposable XDG state.
  Its executable remained visible after NVM selected another Node version. Deliberate
  binary drift failed read-only verification and installation refused replacement;
  explicit fixture restoration recovered it.
- All earlier Go, Rust, JVM/Mandrel, Node/pnpm, shell/Git, backup and package-drift
  fixtures passed again in both cycles.

The Python fixture has no external PyPI dependencies, native extensions or real
projects. OpenCode did not log in or call a model. Agent provider sessions, four
remaining selected agent CLIs, application/desktop/container roles, transfer handoff,
full pristine OS installation and physical workstation acceptance remain unfinished.
Source and delivery details are in [Python review](SOURCE-EVIDENCE.md#uv-and-cpython),
[OpenCode review](SOURCE-EVIDENCE.md#opencode) and [agent gates](SOURCE-EVIDENCE.md#agent-clis-delivery-gates).

## Codex CLI and combined agent reboot checkpoint — 2026-09-15

`./script/test-vm --controller --user-environment --reboot` passed before and
after a real Ubuntu 26.04 guest reboot. Each cycle ran **185 behavioral tests**;
offline Ansible lint reported zero failures/warnings across all **14 playbooks**.
The controller and selected user roles applied twice in each cycle, and independent
read-only verification passed.

- The official Codex CLI 0.154.0 Linux amd64 musl archive matched its publisher
  digest, and the exact single extracted binary matched the locked digest. The
  artifact worker normalized that archive member to a versioned `codex` executable
  without a shell installer, npm prefix or profile replacement.
- A fresh managed Zsh reported `codex-cli 0.154.0`; its help listed the `exec`
  command. The binary remained visible after NVM Node switching and Microsoft
  21/Temurin 25 shell selection. The first guest run had a fixture-only assertion
  looking for the literal phrase `codex exec` in help; current help displays
  `exec` as a command row. The assertion was corrected, checked directly in the
  guest, and the complete two-cycle suite then passed.
- Deliberate binary modification failed independent verification, and install
  refused to overwrite the changed payload. Explicit restoration of the fixture
  bytes recovered verification. Host tests also rejected unexpected archive
  members and a wrong download digest before placing a binary.
- Earlier user Python/uv, OpenCode, JVM/Mandrel, Go, Rust, Node/pnpm, APT prerequisite,
  private backup and retained shell/Git cases repeated in both cycles.

Codex's local version/help check did not sign in, call a model or exercise a
project session. The bundled Sigstore certificate verifies the binary signature,
but its full certificate chain/transparency proof remains unverified here; the
publisher digest is pinned for installation. At that checkpoint, Aider,
Claude Code and Cline remained selected delivery work; the later Cline result
is recorded below. The transfer-handoff producer/verifier, application,
desktop/container roles, full pristine OS installation and physical workstation
acceptance remain unfinished. See [Codex source review](SOURCE-EVIDENCE.md#codex),
[agent gates](SOURCE-EVIDENCE.md#agent-clis-delivery-gates), [F02 handoff contract](../specs/F02-storage-guard.md)
and [unfinished tasks](../TASKS.md).

## Withdrawn: transfer evidence checkpoints (2026-09-15 to 2026-09-16)

The five checkpoints that follow record work on the automated transferred-disk
design, withdrawn on 2026-09-16 (D017). They are kept as a record of what was
built and tested, not as evidence for any current guarantee. The code, fixtures
and the `transferred-ssd` storage mode are removed; files move by copy, proved
in the manifest and migration acceptance below.

## Transfer evidence format fixture checkpoint — 2026-09-15

`python3 -B -m unittest discover -s tests -v` passed **192 host tests** and
`./script/test-vm` passed **192 tests in the Ubuntu 26.04 guest** plus its live
standard-layout preflight and wrong-UUID installation boundary. This is a static
and synthetic fixture checkpoint; it does not prepare or boot a transferred disk.

- The T6a parser accepts exact private receipt/system-witness fields, selected
  disk and mount bindings, owner/mode restrictions and a receipt digest of the
  exact witness bytes. It rejects duplicate/unknown fields, invalid UTC dates,
  changed witness content, different disk/mount UUIDs, public receipt modes,
  oversized files and symlinked evidence or parent paths.
- A standard profile refuses evidence before opening either file. A structurally
  valid synthetic pair still leaves transfer storage assessment at **incomplete
  (exit 3)**. The parser has no install/verify command path that could enable
  transferred apply.

The offline comparison producer, independently retained system-disk witness,
live machine/package consistency verifier, post-apply package checkpoint and
actual transferred-disk maintenance/boot guest cases are unfinished. These are
specified in [F02](../specs/F02-storage-guard.md) and remain in [TASKS.md](../TASKS.md).

## Cline CLI-only and combined reboot checkpoint — 2026-09-15

`python3 -B script/check-catalogue` passed, and
`python3 -B -m unittest discover -s tests -v` passed **196 host tests**.
`./script/test-vm --controller --user-environment --reboot` exited 0 against
the existing dedicated Ubuntu 26.04 amd64/GNOME KVM guest. It ran **196 guest
behavioral tests in each live cycle** and offline Ansible lint reported zero
failures/warnings across **15 playbooks**. The controller and selected user
roles applied twice with independent read-only verify; the runner observed a
real changed guest boot ID and repeated live acceptance after reboot. Private
guest evidence is in `vm/state/foundation-test.log`; its reboot marker follows
both Cline passes.

- The CLI-only lock matched the publisher's npm SHA-512 values for both the
  `cline` wrapper and Linux x64 binary package, then checked all 148 archive
  members and the generated launcher. The exact two-package role never ran
  npm postinstall or downloaded the wrapper's SDK dependencies.
- A fresh managed Zsh executed Cline **3.0.62** version/help with disposable
  private Cline/XDG state. The same launcher path and command worked after
  NVM project selection, `nvm deactivate`, Microsoft Java 21 selection and
  restoration of Temurin 25, both before and after reboot.
- In both live cycles, deliberate changes to the compiled binary, a Hub
  webview asset and the launcher failed read-only verify. Repeat install
  refused to replace the changed files; explicit fixture restoration made
  verify pass. Host negative tests rejected corrupt downloads, unexpected or
  linked archive members before placement and existing payload drift without
  download.
- Earlier Java/Mandrel, Maven/Gradle/Kotlin, Go/Rust, user Python/uv,
  OpenCode/Codex, Node/pnpm, native prerequisites and retained shell/Git cases
  repeated in the same guest cycles. A required selected capability with an
  unresolved delivery remains a failure; the suite does not assert whole
  workstation readiness.

This checkpoint did not authenticate Cline, run a model/provider or Hub session,
or exercise the selected VS Code extension. The five SDK packages declared by
the published npm wrapper are deliberately outside this CLI-only closure; any
SDK API use needs its own transitive review. No real projects were available,
and full application, desktop/container, transfer handoff, pristine OS-install
and physical hardware acceptance remain unfinished. See [Cline source review](SOURCE-EVIDENCE.md#cline),
[agent gates](SOURCE-EVIDENCE.md#agent-clis-delivery-gates) and [unfinished tasks](../TASKS.md).

## Transfer offline comparison core checkpoint — 2026-09-15

`python3 -B script/check-catalogue` passed, and
`python3 -B -m unittest discover -s tests -v` passed **203 host tests**.
`./script/test-vm` exited 0 in the dedicated Ubuntu 26.04 guest with **203
guest tests**, its live standard-layout preflight/wrong-UUID guard and a real
POSIX ACL metadata fixture. No transferred disk was mounted or prepared by
this checkpoint.

- The read-only comparator checks every relative directory, regular file and
  symlink twice. It hashes file bytes and xattrs (including POSIX ACL xattrs),
  and compares uid/gid, modes, mtime, symlink targets and hardlink groups.
  Identical copied fixture trees produced deterministic redacted digests.
- Old package-status file contents, mode and `user.*` xattr changes,
  unreadable attributes, mismatched hardlink groups, outside-tree hardlinks,
  special files, root symlinks/overlap and a writer change between passes
  failed host fixtures. A copied package-status file with a real POSIX ACL
  passed comparison in the guest; changing only that ACL failed comparison.
- The core never writes a receipt or witness and has no command path into
  `bootstrap preflight` or `install`. Transfer storage assessment remains
  **incomplete (exit 3)** even with structurally valid evidence.

T6b still needs an offline maintenance producer bound to the selected root,
machine identity and package baseline, plus an independent system-disk witness
and private receipt. T6c needs initial/post-package live verification; T6d
needs actual disposable transferred-disk maintenance-to-boot cases. Neither
this fixture nor a matching UUID authorizes production data transfer. See
[F02](../specs/F02-storage-guard.md) and [unfinished tasks](../TASKS.md).

## Transfer evidence publication-core checkpoint — 2026-09-16

`python3 -B script/check-catalogue` passed, and
`python3 -B -m unittest discover -s tests -v` passed **211 host tests**.
After restarting the repository-owned disposable VM, `./script/test-vm` exited
0 in Ubuntu 26.04 with **211 guest tests**, the live standard-layout checks and
the real POSIX ACL fixture. The raw source-review SHA-256 remained
`d6e40f209682c5bdd1b792acc2a07a306c37729e2602509299150544be71612a`.

- The separate-`/var/lib` publication core brackets the complete two-pass tree
  comparison with stable, no-follow reads of `dpkg/status`. It binds the report,
  package baseline, selected UUIDs/disk IDs, supplied target identity and hashed
  machine ID into canonical evidence without copying private tree contents.
- Both outputs use pre-existing, no-follow parent directories, owner/mode checks,
  fsynced staging files and no-replace final links. The system witness is placed
  first and the mode-`0600` target-user receipt last. An injected interruption
  before receipt placement left only the witness and no staging files.
- Host fixtures rejected divergent content, stale package bytes, symlinked or
  changing package status, target mismatch, pre-existing output, an output inside
  a compared tree and a symlinked output parent. The Ubuntu fixture compared a
  real `system.posix_acl_access` value, detected its change, then published and
  re-parsed the evidence pair after restoring equality.

This core accepts target identity and ownership from its caller. It does not
discover the target, prove the source/destination/output paths are on the selected
physical disks, stop writers, create directories, expose an operator command or
authorize bootstrap. Home-only transfer, the live initial/post-package verifier
and an actual maintenance-to-boot transition on synthetic disks remain unfinished.
Transfer preflight therefore still returns **incomplete (exit 3)**.

## Transfer maintenance path-binding checkpoint — 2026-09-16

`python3 -B script/check-catalogue` passed, and both the host suite and
`./script/test-vm` passed **219 tests**. The Ubuntu run repeated its live
standard-layout guard and real ACL publication fixture. This checkpoint used
inventory fixtures for the transferred layout; it did not attach or boot a
transferred disk.

- The read-only adapter requires every ordinary live storage check to pass up
  to the expected deferred handoff result. It then binds the fresh source and
  fixed `/etc/linux-os-setup/transfer-witness.json` location to the system root,
  `/var/lib` to its selected data mount, and the configured receipt to the target
  user's directory on `/home`.
- Fixtures rejected sources on a transferred or unexpected nested mount,
  receipts outside the target home, another witness path, another prepared path,
  wrong/read-only mounts, platform mismatch and malformed machine identity.
  The machine-ID reader rejects oversized, writable, symlinked and changing
  inputs and does not follow a symlinked parent.

The adapter has no public command and performs no publication. It does not prove
that services are stopped or that a maintenance-to-normal-boot transition is
safe. Those guarantees, the home-only branch, live package checkpoints and
synthetic transferred-disk boot cases remain unfinished, so transfer preflight
continues to return **incomplete (exit 3)**.

## Transfer maintenance command-boundary checkpoint — 2026-09-16

`python3 -B script/check-catalogue` passed, and both the host suite and
`./script/test-vm` passed **224 tests**. The executable bit on
`script/produce-transfer-handoff` and the unchanged raw-review digest were also
checked. The guest repeated the standard live guard and ACL publication fixture;
it did not enter rescue mode or attach a transferred-disk fixture.

- The command requires UID 0 before it reads configuration, rejects examples,
  uses the ordinary live inventory plus the path-binding adapter, and accepts
  only PID 1 systemd with exactly one of rescue/emergency active while graphical
  and multi-user targets are inactive.
- It requires the receipt parent to be target-user-owned and mode-private. It
  creates or reuses only the fixed root-owned mode-private witness directory
  beneath `/etc`, then delegates all evidence bytes and witness-before-receipt
  ordering to the publication core. Output remains redacted.
- Fixtures rejected non-root invocation before a private path was opened,
  ordinary or ambiguous systemd targets, wrong PID 1, public/incorrectly owned
  receipt parents and unsafe witness-directory reuse.

The command does not isolate the system, prepare mounts or copy data. No actual
rescue-mode command execution, transferred-disk reboot, home-only producer or
live initial/post-package verifier has passed. `bootstrap` does not call this
command or consume its evidence, and transfer preflight remains **incomplete
(exit 3)**.

## Transfer home baseline and live-verifier core checkpoint — 2026-09-16

`python3 -B script/check-catalogue` passed,
`python3 -B -m unittest discover -s tests -v` passed **245 host tests**, and
`./script/test-vm` passed **245 guest tests** with the live standard guard and
real ACL fixture. The guest publication fixture also accepted a stable restored
home extra while proving the fresh home baseline. No transferred disk was
attached and the guest did not enter rescue mode.

- Evidence schema/producer version 2 supersedes fixture-only version 1 before
  any production evidence existed. Its witness records separate fresh/prepared
  home paths and nullable `/var/lib` paths; version 1 is rejected because it did
  not prove the transferred home baseline.
- The home comparator scans both trees twice. Fresh baseline files, links,
  ownership, modes and ACL/xattrs must match; directory mtimes may differ and
  stable restored extras are allowed without entering evidence. Missing or
  changed baseline entries, an extra hardlink to a baseline file, overlapping
  comparison roots and writer races fail.
- Publication now combines the mandatory home report and optional exact
  `/var/lib` report. Home-only transfer emits null package and `/var/lib` fields;
  separate `/var/lib` still brackets all comparisons with stable package-status
  hashes. Host fixtures covered both branches and the command now requires
  `--fresh-home`, with `--fresh-var-lib` only when selected.
- The internal initial verifier rejects machine drift, evidence changes, another
  prepared destination and unrecorded first-apply package changes. The strict
  checkpoint parser accepts a later apply-owned package digest only when its
  witness, root, machine and timestamp bind to the original receipt. Home-only
  transfer forbids package checkpoints.

Checkpoint publication is not implemented, and neither verifier is wired into
`bootstrap`. Actual rescue-mode production, transferred-disk boot/reboot,
interruption recovery and negative mount cases remain T6c/d work. Transfer
preflight therefore remains **incomplete (exit 3)**.

## Machine manifest and file migration acceptance — 2026-09-16

The first end-to-end acceptance of [F13](../specs/F13-machine-manifest.md) and
[F14](../specs/F14-file-migration.md), run with `script/test-manifest-vm`
against a guest destroyed and rebuilt from the verified Ubuntu 26.04 image.

Host static gates before the run: `check-catalogue` passed (251 capabilities,
169 target selections), `check-manifest` passed (146 selections, 130 delivery
entries, 27 pinned binaries, 16 signed repositories), 226 unit tests passed.

### Applied from a pristine guest

Groups: core, dev, cloud, kubernetes, containers, lab, media, network,
security, ai, productivity, desktop. The `gpu` group is excluded — the guest
has no NVIDIA hardware.

| Result | Observed |
|---|---|
| Apply duration | 794s from a pristine image |
| APT packages | 84/84 present per `dpkg-query` |
| Third-party repositories | 16/16 configured, each key verified against its recorded fingerprint |
| Pinned release binaries | 27/27 installed, each verified by SHA-256 on download |
| Snaps | 4/4 installed on their declared channel |
| Executable check | 9/9 sampled binaries ran (helm, k9s, yq, sops, kubeconform, actionlint, d2, chezmoi, hadolint) |
| `bootstrap install` outcome | `incomplete` — packages delivered, undelivered selections reported as deferred |

### Migration

| Result | Observed |
|---|---|
| Full-home plan (dry run) | 389,426 files, 168.1 GB, nothing written |
| Bounded real copy | 18,162 files, 4.08 GB (`bin`, `Documents` from the operator's home) |
| Completeness proof | Second rsync pass reported nothing outstanding |
| Credential leak check | 16,939 guest files hashed against 784 source credential digests; none matched |

### Survives a reboot and repeats

| Result | Observed |
|---|---|
| Reboot | Guest returned in 15s; all four verification groups passed again unchanged |
| Second apply | Completed; verification unchanged |

### What this run does not establish

- **GPU delivery.** The `gpu` group was excluded. The NVIDIA 595 open driver,
  its kernel modules and nvidia-container-toolkit are unproven until the
  physical machine.
- **The GNOME desktop session.** The guest runs a server image, so
  `manifest/desktop.json` — 28 dconf sections, 7 shell extensions — is declared
  and applied by `ansible/desktop.yml` but never exercised in a real session.
- **Editor extensions and krew plugins.** Declared in `manifest/plugins.json`;
  no role installs them yet.
- **The physical move.** Rehearsed against real data shapes at 4 GB, not run
  against the new workstation.

### Defects this acceptance found

Each was fixed and carries a regression test or a recorded decision:

1. **Sealed payload could not be placed.** `python_user.py` sealed the staged
   runtime read-only before renaming it into place; moving a directory to a new
   parent rewrites its own `..` entry, which the kernel refuses without write
   permission. Every fixture test passed and the live install failed. Two
   regression tests now cover it.
2. **Binary keys saved as `.asc`.** APT chooses how to read a keyring from its
   extension, so a binary key under an `.asc` name was ignored and the
   repository silently treated as unsigned. Keys are now normalised to binary
   `.gpg` and verified against a recorded fingerprint by
   `workstation/repository_keys.py`, with 11 tests.
3. **Wrong OpenTofu key.** `get.opentofu.org` publishes the binary-release key;
   the repository is signed by a subkey of a different key at
   `packages.opentofu.org`. Fingerprint pinning caught it.
4. **Vendor packages that self-register a source.** claude-desktop and chatgpt
   install their own source file for a URI this repository also declared, and
   APT refuses to read its whole source list when one URI carries two
   `Signed-By` values. Each is now installed alone and its URI handed back
   before the next apt call.
5. **`authorized_keys` overwritten by the secrets pass.** It replaced the
   destination's key with the source's, revoking the key the copy was running
   over and locking the operator out mid-transfer. Never copied now (D020).
6. **No retry on release downloads.** A transient GitHub 500 failed an
   otherwise correct install. Downloads retry; the checksum still decides what
   is acceptable.

Two earlier leak checks were themselves wrong before the third was trusted:
testing for absent paths failed because the guest creates its own `~/.ssh` and
`~/.gnupg`, and matching by file name failed for the same reason. The check now
compares content hashes, ignoring empty files, whose digest matches everywhere.

## GNOME settings delivery — 2026-09-16

`ansible/desktop.yml` was wired into the install and exercised in a clean cycle
from a destroyed guest.

| Result | Observed |
|---|---|
| Apply duration | 704s from a pristine image |
| Declared dconf keys | 71 across 27 sections, applied and read back |
| Extensions | 5 enabled, 2 deliberately left off — exactly as declared |
| Independent readback | `Yaru-olive` theme, `green` accent, `Ubuntu Sans 11`, the five enabled extensions and the power settings confirmed by `dconf read` in the guest |
| Reboot | Guest returned after 304s; settings unchanged |
| Second apply | Reported no change |
| Packages, binaries, snaps | 84/84, 27/27, 4/4 unchanged |

`dconf load` was checked to work both with and without a session bus: with one
it goes through dconf-service, without one dconf writes the user database
directly. Both paths were confirmed to store values, not merely exit zero.

### What this found

- **Installed is not enabled.** `gnome-extensions list` reports installed
  extensions; the inventory recorded all seven as though they were on. Two
  (`snapd-prompting`, `ubuntu-appindicators`) are installed and deliberately
  off. The inventory now records enabled and disabled separately, and
  verification fails both when an extension that should be on is off and when
  one that should be off is on.
- **Extension-managed state drifts.** `tiling-assistant` stores the mutter
  settings it overrides in `overridden-settings` while active and removes them
  when not, so three keys appeared in one snapshot and not the next. Replaying
  a stale copy would have the extension restore values that are no longer
  current, so that key is now excluded deliberately rather than captured by
  chance.
- Applying is not the same as having applied: the worker reads every declared
  key back and fails on a keyfile dconf accepted but did not store.

### Limits

The guest is a server image, so nothing has rendered these settings. Appearance,
keybindings, dock behaviour and suspend remain unobserved until a real GNOME
session. The manifest enables extensions but installs none, relying on those
shipped with `ubuntu-desktop`.

## Single package path — 2026-09-16

`manifest/packages.json` became the only source of what installs. The legacy
approved-package path (`ansible/packages.yml`, `catalogue/approved-delivery.json`
as an install input) was removed, and its source checks were generalised to all
94 packages rather than dropped.

| Result | Observed |
|---|---|
| Apply duration | 697s from a pristine image |
| APT packages | 87/87 for the twelve installed groups, each from its declared source |
| Pinned binaries | 27/27 |
| Snaps | 4/4 |
| Desktop settings | 71/71 keys, 5 extensions on and 2 deliberately off |
| Reboot | Guest returned in 15s; all checks passed again |
| Second apply | Repeatable |
| `bootstrap verify` coverage | 94 manifest packages, up from 9 |

### What this found

- **kubectl was being installed from the wrong repository.** google-cloud-cli
  ships a `kubectl` at epoch `1:585.0.0-0`, which outranks upstream Kubernetes'
  `1.34.11-1.1`. APT's candidate is the highest version across every configured
  repository, so adding that repository silently replaced kubectl — and every
  earlier run reported success while installing Google's build. The probe now
  chooses the highest version *from the declared source*, and APT preferences
  pin each repository-sourced package to its declared host so a later upgrade
  cannot switch it back. Confirmed in the guest: `kubectl 1.34.11-1.1` from
  `pkgs.k8s.io`.
- **The vendor handover was deleting the vendor's own source file.** Our
  declared source and ChatGPT's self-registered one were both named
  `chatgpt.sources`, so handing the URI back removed the vendor's file. The
  package stayed installed but belonged to no repository and could never
  update. Our files are now named `workstation-<id>.sources`, which cannot
  collide. Google Chrome behaves the same way — its postinst rewrites the file
  it finds — and is now declared self-registering too.
- **Vendor-registered sources had no index.** A package installed from a source
  the vendor registered during that same install is attributed to no repository
  until the next refresh, so verification rightly failed it. Metadata is now
  refreshed after each vendor install.
- **Verification checked groups that were never installed.** A machine
  installed without the `gpu` group has not failed to install it. The applied
  groups are recorded during install and verification is scoped to them.
- **A signature change broke two runtime modules silently.** `verify_packages`
  changed shape and `mandrel_runtime` and `rust_runtime` still called it with a
  list of prerequisite records, which the package layer then treated as a
  filesystem path. They now use `verify_named_packages`, and a test asserts the
  call sites pass package names.
- **The reboot check could not fail honestly.** While the guest is down, qemu's
  port forward still accepts the TCP connection, so `ssh` gets past connect and
  waits for a banner that never arrives; `ConnectTimeout` does not apply. The
  first poll blocked for the entire window and a successful reboot was reported
  as a failure. The poll now has a hard timeout.

### Deliberately not carried over

The legacy path simulated the whole resolver transaction to prove that
dependencies also came from reviewed sources. That simulation was removed
rather than generalised: python-apt's manual marking is not a faithful model of
APT's solver and reported conflicts that a real install resolves without
difficulty — six `qemu-*-hwe` packages, which `apt-get install -s` handles
cleanly. The guarantee now rests on there being no undeclared source configured
on the machine and APT refusing unsigned ones, which is recorded in
`workstation/packages.py`.

## Closing the delivery and verification gaps — 2026-09-16

Four gaps closed and exercised in a clean cycle from a destroyed guest:
**45 checks, no failures**.

| Delivery | Result |
|---|---|
| APT packages | 87/87 for the twelve installed groups, each from its declared source |
| Pinned binaries | 27/27 present; raw assets checked against their pinned digest |
| Snaps | 4/4 on their declared channel |
| Repositories | 16/16 configured with their recorded signing key |
| VS Code extensions | 17/17 installed |
| krew plugins | 6/6 installed, after krew bootstrapped itself into `~/.krew` |
| Claude Code | `2.1.273` present and unmodified, runs |
| Copilot CLI | `1.0.85` present and unmodified, runs |
| GNOME settings | 72/72 keys, 5 extensions on and 2 deliberately off |
| Migration | 167.6 GB planned, 4.08 GB copied and proved complete |
| Credential separation | 2,195 source credential files compared by content, none arrived |
| Reboot and second apply | Guest returned in 24s; everything verified again unchanged |

### What changed

- **`bootstrap verify` now covers the whole manifest.** Binaries, snaps and
  repository keys were previously checked only by the VM fixture, so a clean
  verify on a real machine did not mean the machine matched the manifest.
- **The prompt is now delivered, and started.** The managed shell sets
  `ZSH_THEME=""`, so a starship configuration file alone renders nothing; the
  `init` line matters as much as the config. The same applies to atuin.
- **Agent CLIs are pinned to exact npm tarballs.** A tarball's SHA-256 covers
  every file inside it, and the executable's own digest is recorded separately,
  so replacement after installation is detectable. npm is never invoked.
- **krew bootstraps itself before plugins install.** kubectl only discovers
  plugins named `kubectl-<name>` on PATH, so the `krew` binary in
  `/usr/local/bin` is not reachable as `kubectl krew` until krew installs itself
  into `~/.krew`.

### What this found

- **`krew list` has two output shapes.** It prints a bare list of names when
  stdout is not a terminal and a `PLUGIN VERSION` header when it is.
  Verification dropped the first line unconditionally, so the alphabetically
  first plugin — `images` — was reported missing while installed. Both shapes
  now parse, with a regression test for each.
- **`.npmrc` is not committable configuration.** It carries an employer registry
  URL, an address and `strict-ssl=false`. It was declared as a managed dotfile;
  it is now private input, moved by the secrets pass.
- **Two dotfiles were declared and delivered by nothing.** `.zprofile` only adds
  `~/.local/bin` to PATH, which the managed shell already does, and `.profile`
  is the distribution default. Declaring a file nothing writes is how a machine
  ends up with a binary and no configuration, so a test now asserts every
  declared dotfile is one something delivers.

### Limits unchanged

GPU delivery and the rendered desktop session remain unproven — the guest has no
NVIDIA hardware and runs a server image. VS Code extension versions are not
pinned, unlike the binaries and agent CLIs.
