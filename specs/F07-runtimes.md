# F07 — Reviewed runtimes and synthetic developer workflows

## Shared behavior

Use reviewed current stable releases, excluding previews. Temurin 25 is the fixed
Java default line; Microsoft/Temurin 21/25 remain explicit project variants. NVM owns
Node version selection and SDKMAN owns JVM candidate selection. Do not introduce mise
or preserve historical Node/Maven/Mandrel versions as mandatory compatibility pins.
Ansible sequences reviewed acquisition and manager operations after storage checks;
chezmoi owns shell initialization. A manager installer may not rewrite shell files.

Bind exact artifacts to publisher hashes and release-specific licence evidence before
execution. Review manager bootstrap and native/helper downloads as a complete chain.
Never use curl-pipe-shell, floating install scripts or automatic manager self-update.
Run as the actual target user with a separate controller and runtime environment.
Preserve other installed versions and project selection files. Never replace project
pins globally. Missing selected prerequisites are failures/incomplete, never skips.

## Node/NVM slice

Use a pinned NVM source tree and exact stable Node Linux amd64 archive. Populate only
the dedicated managed NVM data directory. Verify preseeded cache bytes before invoking
NVM's binary-only installation for that version; reject fallback source builds. Check
the resulting runtime payload and default alias. Ensure `nvm use`, `nvm current` and
`nvm exec` agree. Independently verify without sourcing scripts that acquire missing
versions or running install commands. Explicit update operations handle new pins later.

Provide pnpm independently of the currently selected Node version, so switching Node
cannot hide the package manager. Verify a synthetic package install/build/test and
lockfile behavior with no production credentials. Report network/dependency failures.

## JVM slice

Manager role contract: Ansible acquires both exact source artifacts and constructs
the dedicated `~/.local/share/linux-os-setup/sdkman` tree as the target user. It owns
manager code and bootstrap policy/metadata; these are not declared chezmoi targets.
Chezmoi owns only shell initialization. Stage a complete new manager before atomic
placement; preserve unrelated `~/.sdkman`. Existing changed managed code or policy
fails without replacement. Verify code, policy and empty extension directory without
executing SDKMAN or downloading. Candidate/temp state is separately mutable. Guest
acceptance must cover repeat apply, fresh shell version output, read-only drift,
refusal to overwrite modified manager files and explicit fixture restoration.

SDKMAN archive acceptance: ZIP acquisition must retain executable modes and reject
absolute/traversing paths, duplicate normalized names, links and special files before
extraction. Verify every extracted file against the reviewed manifest. Test malicious
archives as fixtures before enabling SDKMAN delivery. CLI and native helpers have
separate release versions; the floating installer is evidence only, never executed.
Record compatibility evidence for the chosen pair before approving the manager.

Review SDKMAN CLI plus native helper, candidate metadata and each downloaded archive.
Use verified local candidate archives/registrations where supported; do not blindly
trust an SDKMAN identifier as artifact integrity. Disable automatic self-update and
unprompted candidate installation. Set Temurin 25 as default after all selected Java
variants are registered. Maven/Gradle/Kotlin/Mandrel must remain selectable without
changing that default. Verify effective JAVA_HOME and executable paths in a fresh shell.

Synthetic acceptance includes Java compilation, Maven test/package, a Gradle or Kotlin
fixture, and a Mandrel native-image build/run when its delivery is complete. Exercise
project-specific switching and restore the default. No existing project compatibility
is claimed because no current projects were supplied.

Before production JVM delivery, an isolated source experiment registers all four
reviewed Java archives with the tested SDKMAN pair. Compile/run the same synthetic
Java program under each vendor/major, assert effective vendor/version/JAVA_HOME, then
restore Temurin 25 and assert the global default never changed during shell switches.
Verify original archive trees after execution. This experiment authorizes no production
installation and does not replace role idempotence/drift or Maven/native-image tests.

## Additional runtimes and CLIs

### Mandrel native-image delivery

Deliver the reviewed Linux amd64 Mandrel archive as an additional local SDKMAN Java
candidate, with no change to Temurin 25's default. Require selected SDKMAN/Java and
the source-approved C++/zlib/FreeType development prerequisites. On Ubuntu 26.04 use
the verified `libfreetype-dev` package; the upstream example's `libfreetype6-dev` has
no candidate in that release. Never invoke a vendor installer or remote SDKMAN hook.
Verify the full payload, exact registration, Java default and required APT state
independently. Existing modified payload/registration fails without replacement.

Acceptance: explicitly select Mandrel in a project shell, compile Java, build a
native executable with no fallback, run/assert its output, restore Temurin 25 and
verify its default. Limit build memory in the 8 GiB guest. Repeat apply/reboot and
negative dependency/payload fixtures remain required; no Quarkus or existing-project
compatibility is implied by the basic synthetic executable.

### Maven, Gradle and Kotlin delivery

Require selected, independently verified SDKMAN and Java. Acquire exact approved
archives after storage guards, then register local candidates through the inspected
SDKMAN function. Set only each tool's own default; never change the Java default.
Chezmoi's SDKMAN initialization exposes their current directories. Do not rewrite
existing Maven settings, Gradle user configuration, project wrappers or SDKMAN project
files. Changed payloads/registrations fail without replacement. Back up changed tool
default links privately before explicit reapply. Verification reads payloads and links
without running managers or downloading. Missing prerequisites fail visibly.

Acceptance: repeat apply; Maven test/package and packaged Java execution; Gradle
compile/build and local Java execution; Kotlin compile-to-JAR and execution. Confirm
Temurin 25 stays the default and all tools remain visible during Java selection.
Dependency downloads belong to disposable fixture caches; no credentials or real
projects are imported. Test default drift without repair and explicit recovery.

Specify Python and agent delivery before their tasks. User Python never becomes
the controller interpreter. Agent CLIs must remain on a stable path across runtime
switches. Credentials, model downloads and authenticated agent sessions stay manual;
check locally available versions/help and synthetic unauthenticated behavior honestly.

### Go delivery

Use the current stable publisher Linux amd64 archive and checksum from Go's release
metadata. Ansible places the exact immutable payload below the managed user-tool tree
after storage verification; chezmoi adds only its versioned `bin` directory to PATH.
Do not use a system-wide `/usr/local/go`, a floating installer or change `GOROOT`,
`GOPATH`, module proxy/authentication or project files. Existing changed payloads fail
without replacement. Independent verification reads the entire payload manifest and
never executes Go, downloads modules or repairs state.

Acceptance: fresh-shell version/architecture, local module init/test/build/run with
`GOPROXY=off`, repeat apply, controller-absent verification, deliberate payload drift
without repair and explicit fixture restoration. The fixture has no external
dependencies or production cache/credentials. Rust/Python/agent tools remain separate.

### Rust delivery

Use rustup 1.29.1 and the publisher's dated Rust 1.98.1 channel for
`x86_64-unknown-linux-gnu`. Acquire rustup-init, the signed-by-published-digest channel
manifest and only the minimal rustc, Cargo and standard-library archives by exact URL
and SHA-256. Stage those reviewed files in a temporary local distribution root so
rustup performs the toolchain transaction through file URLs without reaching a
floating channel or opening a listener. Disable rustup self-update and shell-file
modification. Do not execute the network bootstrap script.

Keep RUSTUP_HOME and CARGO_HOME in dedicated managed state below
`~/.local/share/linux-os-setup`; chezmoi adds only the stable Cargo shim directory to
PATH. Set the exact `1.98.1-x86_64-unknown-linux-gnu` toolchain as the rustup default.
Preserve project `rust-toolchain` files and unrelated conventional `~/.rustup` and
`~/.cargo` trees. Rustup owns its metadata and shims; Ansible owns sequencing and the
reviewed immutable inputs. Existing changed manager or toolchain payloads fail without
replacement. Verification reads the locked manager, default selection and full
toolchain payload without running rustup, rustc or Cargo, downloading or repairing.

Acceptance: repeat apply; fresh-shell manager/compiler/Cargo versions and active
toolchain; local dependency-free Cargo test/build/run with registry networking disabled;
project pin selection and restoration of the global default; controller-absent verify;
deliberate manager/toolchain/default drift; corrupt/unavailable input failure before
placement; explicit fixture recovery; and a reboot repeat in the disposable guest.
No crates.io, private registry, cross-target, native-library or real-project
compatibility is implied by this synthetic fixture.

### User Python and uv delivery

Use the reviewed uv 0.12.13 Linux amd64 release and the current stable CPython 3.14.7
`python-build-standalone` archive dated 2026-09-01. The controller may use the same
source versions, but its repository-local environment and the user's runtime state
remain separate. `/usr/bin/python3` stays distribution-owned and remains the explicit
interpreter for bootstrap guards and managed-host Ansible modules. Python requires
an explicit uv selection; an uv-only selection delivers no Python interpreter.

Ansible places the complete verified uv payload on a versioned stable path. It stages
the exact Python archive behind a temporary local file mirror and invokes the pinned
uv binary with automatic discovery/configuration disabled to install that exact patch
release into a dedicated `UV_PYTHON_INSTALL_DIR` with `--no-bin`, so uv does not touch
conventional user executable links. Normalize its version alias to a relative link
and rewrite uv's generated `sysconfig` prefix to the final managed location before
atomic placement. The lock hashes that file with its location normalized; verification
checks its content and final prefix. Disable automatic Python downloads outside
explicit installation. The installed interpreter files and directories are read-only
to avoid bytecode writes inside the locked source tree; project virtual environments
and caches remain project/user owned. Chezmoi exports the managed uv path and user
Python directories without defining PYTHONPATH, changing system alternatives, installing
global packages or editing project `.python-version`/`pyproject.toml` files. Existing
conventional uv/Python state remains outside the managed directories.

Independent verification hashes the complete uv and Python payloads and checks the
declared default executables without running either tool, downloading, syncing or
repairing. Existing changed payloads fail without replacement. Acceptance covers two
applies, fresh-shell uv/Python versions, a project-local virtual environment, an
offline locked local dependency/test/build/run workflow, project Python selection,
controller-absent verification, runtime switching visibility, corrupt-input failure
before placement, deliberate payload/default drift, explicit fixture recovery and a
reboot repeat. No PyPI credentials, external packages or real projects are used.

### Selected agent CLI delivery

The initial target selects Aider, Claude Code, Cline, Codex and OpenCode. Review
each current stable Linux amd64 source separately, including release-specific
terms, transitive dependencies and published integrity evidence before marking
that capability verified. Cline's npm installation needs a private, pinned prefix
that is stable through NVM project switching. Aider needs a locked isolated uv tool
environment and a Python version compatible with its reviewed metadata; it may
select a different interpreter without changing the global user Python default.
The [PyPI metadata](https://pypi.org/pypi/aider-chat/json) for Aider 0.86.2
currently requires `>=3.10,<3.13`, so its
candidate isolated interpreter is a reviewed Python 3.12 patch, in a separate
agent-tool directory from the default Python 3.14.7 source tree.
Claude Code needs its published signed platform manifest or a separately reviewed
signed Ubuntu channel. Codex and OpenCode need exact official platform artifacts,
not floating installers. Do not invoke curl-pipe-shell or let any agent update its
managed executable silently.

Ansible sequences acquisition, validation and placement as the explicit target
user; chezmoi exports only declared stable executable paths. Full installed
payloads and version/default links have independent read-only verification.
Credentials, account login, model/provider setup, downloaded models, project
prompts, agent sessions and authenticated workflows remain operator tasks. A guest
may check local versions/help and documented unauthenticated behavior, but must
report live model use as unverified. Acceptance includes two applies, unavailable
and corrupt source failures before placement, modified payload refusal, controller-
absent verification, visibility across Node/JVM/Python switching and a reboot
repeat. No selected agent is a successful skip while its source remains unreviewed.

OpenCode is the first independent agent slice: review v1.18.31's generic x64
baseline GNU archive, publisher SHA-256, exact extracted binary, tagged MIT
licence and the bundled Bun/WebKit LGPL-2 licensing scope. The single-file
artifact needs only Ubuntu's glibc compatibility in the
disposable guest. Ansible places it on a versioned path; chezmoi exports the path
and `OPENCODE_DISABLE_AUTOUPDATE=1` for managed-shell commands. Avoid replacing
an existing global OpenCode configuration. Its standalone `--version` may create
XDG state, so the guest fixture directs configuration, cache, data and state to
its own private temporary directories. Verification reads its complete payload
without executing the CLI. Test local version/help, Node switch visibility, two
applies, deliberate artifact drift/refusal and explicit fixture restoration, then
repeat after reboot. Authentication and model sessions are not asserted.

Codex is the next independent agent slice. Review the official latest
non-prerelease `rust-v0.154.0` Linux x86_64 musl CLI archive, the publisher's
SHA-256, its single static-pie executable and its tagged Apache-2.0 licence/NOTICE.
The publisher also supplies a Sigstore bundle for the extracted binary; match
its digest, verify its bundled-certificate signature and recorded workflow identity,
and report the unverified certificate-chain/transparency boundary explicitly.
No shell installer, npm auto-update or existing Codex configuration is part of
delivery. Ansible places the exact binary under a versioned user path; chezmoi
exports that path. Read-only verification hashes its one-file payload without
launching Codex or touching `CODEX_HOME`. Guest version/help uses private disposable
Codex/XDG state and checks path visibility after Node and Java switching. Corrupt
archive, unexpected tar member, changed binary and failed source acquisition cannot
place or overwrite it. Repeat apply and verification after reboot; sign-in and
model execution remain manual.

### Cline CLI-only package slice

F07-T6c selects the current stable tagged CLI release, separate from the VS Code
extension. Review exact `cline` npm wrapper and matching `@cline/cli-linux-x64`
package for Ubuntu amd64, including registry integrity, tagged licence,
embedded runtime terms and npm provenance limits. The wrapper declares five
SDK packages as regular dependencies, but its published `bin/cline` uses only
Node built-ins and launches the fully compiled platform binary. This slice
delivers that documented CLI execution closure only; it does not expose the
JavaScript SDK packages or claim SDK API support. Normal global npm dependency
installation is outside the slice and cannot be an implicit download.

Ansible extracts the two locked package payloads below one private versioned
target-user directory in the publisher's `node_modules` lookup layout. It
never runs npm install or postinstall: the latter caches a second executable
and can rename a running Hub's discovery record. A minimal launcher uses the
reviewed absolute managed default Node binary to execute the unmodified
publisher wrapper after `nvm use` or `nvm deactivate`. It sets
`CLINE_NO_AUTO_UPDATE=1`, which the tagged updater checks before fetching or
applying an update. Chezmoi adds only the launcher's versioned `bin` directory
to PATH. Do not replace conventional `~/.cline`, editor configuration,
provider credentials, agent plugins or histories. Independent verification
reads the complete compiled binary, wrapper, assets and launcher without
executing Cline, downloading or repairing. Changed managed payloads fail.

F07-T7c acceptance: reject missing/changed Node, corrupt/unavailable archive,
archive links/traversal/duplicates/unexpected members and extra/modified
installed files before placement; assert no postinstall/SDK downloads. In a
disposable Ubuntu 26.04 guest check local version/help and unauthenticated
behavior with private Cline/XDG state. Repeat apply and verify, switch and
deactivate NVM, switch Java, test deliberate binary/asset/launcher drift with
explicit fixture recovery, then repeat after reboot. Provider login, Hub
sessions, extension integration, model turns and real projects remain outside
this unauthenticated fixture.

## Tasks and acceptance

- F07-T1: refresh/review NVM, Node and pnpm sources, licences, hashes and dependencies.
- F07-T2: guarded NVM acquisition, binary-only Node install, default and independent verifier.
- F07-T3: chezmoi initialization and synthetic Node/pnpm workflow, version switching and drift.
- F07-T4: complete SDKMAN native chain and all Java/Maven/Gradle/Kotlin/Mandrel locks.
- F07-T5: guarded JVM candidate registration/default selection and synthetic build fixtures.
- F07-T6: specify and implement remaining runtimes/agent CLIs, including stable executable paths.
- F07-T7: second apply, interruption/download corruption, unavailable candidates, wrong default,
  missing prerequisite and read-only verification tests in the disposable Ubuntu VM.
