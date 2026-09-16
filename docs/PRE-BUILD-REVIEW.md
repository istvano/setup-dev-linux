# Pre-build review

Prepared 2026-09-13; retained as review history. **The user subsequently authorized
spec-driven implementation and a disposable Ubuntu test VM.** Current implemented
commands and limits are in [OPERATIONS.md](OPERATIONS.md); feature contracts are in
[specs](../specs/README.md). The foundation exists, but the full workstation installer
and its application roles are not complete.

## Confirmed configuration

| Area | Result |
|---|---|
| Platform | Ubuntu 26.04 LTS amd64, GNOME; hardware remains machine-specific |
| Java | SDKMAN; **Temurin 25 is the default**; Microsoft/Temurin 21 and 25 remain project-selectable |
| Native image | Mandrel remains selected; use a reviewed current stable candidate and synthetic native-image smoke test |
| Shell | Oh My Zsh: git, zsh-autosuggestions, zsh-syntax-highlighting; preserve proxyon/proxyoff using private local settings |
| Node | NVM with a reviewed current stable baseline; adapt projects as needed; project selection must not hide installed agent CLIs |
| Version policy | Prefer reviewed current stable tools, including major upgrades, and adapt projects. Temurin 25 remains the explicit Java default |
| Project testing | No current projects exist; plan synthetic workflow tests, with actual project compatibility unassessed |
| OpenHands | Deferred to the optional backlog; excluded from both initial selections |
| Scanning | Installed metadata identifies Simple Scan and SANE utilities; actual device/backend acceptance remains physical testing |
| Storage | Single/split layouts and optional transferred data drive; no encryption selected; no partitioning or data movement in post-install apply |
| Containers | Rootful Docker and authorized target-user group membership; loopback ports; project services remain project-owned |

The machine-readable preferences are in [user environment](../profiles/user-environment.json).
Exact KEEP selections remain in [target](../profiles/target.json) and
[reusable default](../profiles/default.json). The two confirmed Zsh plugins are now
KEEP in both profiles. The default excludes the two GPU-profile capabilities.

## Changes to inspect

- [Capability matrix](CAPABILITY-MATRIX.md): complete catalogue and provenance mapping.
  Static QA now compares the entire deterministic rendering, catching changed mappings,
  notes and extra rows. The optional Mac audit reads the recorded Git commit, so local
  edits in that checkout cannot silently change historical evidence.
- [Source review](SOURCE-REVIEW.md): observations for every selected package/extension,
  proposed Linux delivery paths, version/hash candidates and unresolved checks.
  Evidence does not promote catalogue delivery to verified.
- [QA dependency lock](../locks/qa-requirements.txt): hashed jsonschema dependency closure,
  resolved for Python 3.14. The new environment has not been installed or synchronized.

## Items that still block dependent installation

The detailed ledger records remaining checks per capability. These are the principal
gaps; this list is not permission to bypass the rest of the ledger.

| Area | Required resolution |
|---|---|
| SDKMAN/JDKs | Reconcile SDKMAN candidate versions with Adoptium patch releases; obtain exact Microsoft 21/25 hashes and inspect the CLI/native download chain |
| Mandrel | Resolve a reviewed current stable candidate and verify a synthetic native-image workflow; no existing project is available |
| Gradle/Kotlin | Published artifact hashes are recorded; confirm SDKMAN resolves those exact inputs. Gradle 9.7.1 is the stable candidate; 9.8.0-rc-1 is not a stable 9.8.0 release |
| Slack | Complete Linux artifact integrity and update-policy review |
| Vendor repositories | Verify signing-key fingerprints and signed repository metadata; downloaded Packages metadata alone is insufficient |
| Licences | Review release-specific binary and bundled-component terms, including proprietary apps and extension dependencies; source LICENSE observations are not blanket approval |
| Controller and user tools | Complete controller/collection and transitive tool locks; isolate aider's Python requirement from the controller |
| Extensions | Review dependency and pack children and their licences; root VSIX checks do not validate those children |
| Updates | Current stable major upgrades are selected; recheck exact releases and plan/test project adaptations. Dated Helm/pnpm/Terragrunt candidates are not automatically approved pins |
| Credentials | Proposed GNOME credential backend: Docker secretservice helper; confirm its version/source and test disposable keyring operations during implementation. Authentication stays manual |

The latest overall Obsidian release inspected was Android-only. The ledger instead
records the available Linux desktop 1.13.7 candidate. This is why a generic “latest
release” endpoint must not be treated as a platform-aware installer.

## Validation boundary

Run the static checker and negative tests described in [TESTING.md](TESTING.md).
Recorded validation runs and their scope are listed in TESTING.md.
Their success establishes structural consistency, selection coverage and the declared
review invariants. It does not establish Ubuntu package installability, application
compatibility, idempotence, storage safety at runtime or workstation readiness.

After the user's review, unfinished work remains in [TASKS.md](../TASKS.md).
OpenHands is optional backlog work and no longer blocks initial-target readiness;
its Linux source and isolation checks still apply before future explicit enablement.
P1 starts with the shared read-only JSON/config loader and storage guard, followed by
the isolated controller and Ansible foundation. Installation, reboot, second-apply,
drift, VM, native-image and physical-device tests remain unrun. Private disk identities,
accounts, credentials, proxy values and production data must never enter Git.
