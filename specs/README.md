# Feature specifications

Implementation is authorized by the user on 2026-09-13, including a disposable Ubuntu
26.04 test VM. Each feature follows: specify observable behavior, define tasks and
negative acceptance cases, implement, run fixtures and guest tests, record evidence.
Unfinished tasks live in TASKS.md; specifications retain requirements and test IDs.
No runtime dependency on the Mac checkout is introduced. The Mac design contributes
the bootstrap/operator-script separation and disposable-image test lifecycle.

| Feature | Scope | Dependencies | Acceptance |
|---|---|---|---|
| F01 | Strict config loader, pure plan, common redacted reports | P0 schemas | Invalid input fails; preview writes nothing; no false install readiness |
| F02 | Live platform/user/storage preflight | F01 | Wrong disks/mounts fail before writes |
| F03 | Ubuntu VM lifecycle and guest test runner | Verified image | Isolated credentials/storage/network; correct OS; repeatable guest tests |
| F04 | Locked automation controller and initial Ansible apply | F01–F03 | Distribution host Python; verified downloads; scoped privilege; independent verification |
| F05 | Source-approved packages and system security | F04 | Correct source/version, signatures, failure recovery and second apply |
| F06 | Chezmoi shell, Git, identities and browser files | F05 | Preserve unrelated configuration; private backups; declared owner only |
| F07 | SDKMAN/NVM and other runtimes/agent CLIs | F05–F06 | Stable reviewed releases, Temurin 25 default, synthetic builds, runtime switching |
| F08 | Editors/extensions and GNOME desktop integration | F05–F07 | Root/child accounting, settings readback, actual desktop-session tests |
| F09 | Docker/Kubernetes/KVM lab and optional GPU | F05–F07 | Loopback exposure, fresh-login access, synthetic clusters; physical GPU separate |
| F10 | Drift verification, update/snapshot and recovery | F04–F09 | Never repair during verify; reviewed updates; restore fixtures |
| F11 | Full fresh-machine end-to-end acceptance | F03–F10 | Pristine guest, reboot, repeat apply, drift and failure recovery |
| F12 | Separate OS installation and physical cutover | F11 | Disposable-disk destructive tests; manual physical/data gates |
| F13 | Machine manifest: inventory, review, pinned delivery | F04–F07 | Every selection delivered; every binary and repository key pinned; repeatable apply |
| F14 | File migration to a new workstation | F13 | Credentials excluded from the ordinary copy; completeness proved by a second pass |

OpenHands remains optional backlog, outside initial acceptance. No real projects
exist; synthetic tests prove basic workflows only. Physical GPU/scanner/display
acceptance cannot be replaced by VM results.

Detailed contracts: [F01](F01-config-plan.md), [F02](F02-storage-guard.md),
[F03](F03-ubuntu-vm.md), [F04](F04-controller.md),
[F05](F05-approved-packages.md), [F06](F06-user-environment.md),
[F07](F07-runtimes.md), [F13](F13-machine-manifest.md),
[F14](F14-file-migration.md). F08–F12 need detailed specs before implementation.

F02's automated transferred-disk contract was withdrawn on 2026-09-16: files
move by copy, specified in F14. F02 now covers standard-layout preflight only.

F13 and F14 have guest evidence. GPU delivery and the GNOME desktop session
remain unproven — the guest has no NVIDIA hardware and runs a server image.
See [testing evidence](../docs/TESTING.md).
