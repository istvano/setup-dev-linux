# Source evidence

Source, licence and integrity review for each tool this repository installs
outside the Ubuntu archive. One section per tool, merged from the separate
documents these were originally written as.

The machine-readable authority is `catalogue/source-review.json`, rendered to
[SOURCE-REVIEW.md](SOURCE-REVIEW.md), and the pins themselves live in `locks/`
and `manifest/binaries.json`. This document carries the reasoning those files
cannot: what was checked, what was accepted, and what remains open.

All 54 records are accepted as of 2026-09-17 (D021): 49 free licences and 5
conditional, the latter accepted for personal use with no redistribution right.
The conditional five are Claude Code (CLI and extension), the ChatGPT extension,
and the two Microsoft remote extensions, which are licensed only for use with
Microsoft products.

That review covers third-party sources only — 54 capabilities across upstream
releases, the VS Code marketplace, krew, vendor APT repositories, SDKMAN, PyPI
via uv, snaps and npm. Ubuntu archive packages carry no per-item record: the
archive signature is the guarantee, and checking each one repeats it. See
[D018](DECISIONS.md).

Go and Rust had sections here. Both roles were omitted on 2026-09-16 (D019) and
are unreachable — the configuration loader refuses to select an omitted
capability — so their review was dropped with them. Re-enabling either means
reviewing its source afresh.

## SDKMAN

Reviewed 2026-09-14. The SDKMAN manager now has Ansible delivery, independent verification and guest
role evidence. The Java role has its own section above; other JVM tools
retain their delivery gates.

The [CLI 5.23.0 release](https://github.com/sdkman/sdkman-cli/releases/tag/5.23.0)
and [native 0.7.35 release](https://github.com/sdkman/sdkman-cli-native/releases/tag/v0.7.35)
provide the selected Linux x64 ZIP inputs. Their download SHA-256 values match the
publisher release metadata. Exact URLs, hashes, Apache-2.0 licence-document hashes
and complete extracted file manifests are in [sdkman-review.json](../locks/sdkman-review.json).
The CLI/native licence documents are from their respective exact release tags.

The inspected floating installer named native 0.7.34. It was read only; it is not an
installation input and was never executed. The newer native release was tested with
the current CLI before any production approval. ZIP extraction rejects unsafe paths,
duplicate normalized names, links and special files, and preserves executable status
without privileged permission bits. Payload verification includes every regular file.

### Source findings and implementation constraints

- Initialization loads modules using `find -type f`. Symlinking the entire source
  directory or individual module files does not satisfy that loader. The implemented role
  delivers verified regular module files and independently verifies them.
- The CLI has no supported offline-mode setting in this release. Disabling health
  checks does not make arbitrary commands offline. Do not advertise an offline
  manager or invent an `sdk offline` command/configuration value.
- Public `sdk install` can validate versions remotely and execute fetched hooks.
  Production registration must avoid that unreviewed chain. The pinned internal
  `__sdkman_install_local_version` function only registers an existing local folder;
  it was inspected and exercised with synthetic local candidates. This is a
  pin-specific internal API dependency, requiring renewed review on manager updates.
- The native `sdk current java` reports the global default, even after `sdk use`
  changes the active shell. Verify `JAVA_HOME` and executable behavior independently.
  Native default links may be absolute; verify their resolved target.
- Disable self-update, automatic environment selection/installation and health-check
  requests in the managed configuration. Chezmoi owns shell initialization. Ansible owns the dedicated manager code and bootstrap policy/metadata; chezmoi
  does not also declare those files. Candidate/temp state is separately mutable.

### Actual guest experiment

`./script/test-vm --sdkman-review` passed on Ubuntu 26.04 with all 119 static/behavioral
tests. The dedicated fixture checks guest identity, actual target user and live
storage preflight before creating its temporary state. It downloads only the reviewed
archives, checks their digests/manifests and runs the CLI/native pair in both Bash and
Zsh. Local registration, global default, shell switching, effective JAVA_HOME,
executable selection and home lookup passed. Candidate and broker endpoints point to
an unavailable loopback address for these checks. Temporary candidates are small
shell scripts, not Java runtimes; no JVM compilation or production-role claim follows.

The subsequent manager role test passed with 127 host/guest behavioral tests, repeat
apply, fresh Zsh version output, verification with the controller absent and deliberate
module drift. Installation refused to overwrite the changed module; restoring the
fixture bytes recovered verification. Managed policy drift and injected extension
fixtures fail read-only unit verification. Existing `~/.sdkman` is preserved; the
managed directory is `~/.local/share/linux-os-setup/sdkman`.

The lock filename retains `review` for continuity, but now backs the approved manager
role. CLI 5.23.0 and native 0.7.35 are acquired through Ansible after storage guards,
then regular files and policy are staged and atomically placed. Neither vendor
bootstrap nor remote candidate hooks run. A changed managed manager/policy fails
without replacement. Normal shell startup does not choose a different project JDK.

Next: complete Java-role guest acceptance and Maven/Gradle/Kotlin/Mandrel delivery.
Temurin 25 remains the required default.

### Dangling-default recovery

The native 0.7.35 `default` implementation checks `Path.exists()`, which misses a
dangling symlink. Creating the new link then fails and triggers a copy fallback;
the guest recovery fixture reproduced this and left temporary copied state. The
wrapper now records a private backup and removes only that dangling managed default
link before invoking SDKMAN. Existing valid links remain SDKMAN-owned operations;
ordinary directories still fail without replacement. Java and JVM-tool unit fixtures
assert backup bytes/permissions exist before native recovery executes.
The reviewed implementation is [native default.rs](https://github.com/sdkman/sdkman-cli-native/blob/v0.7.35/src/bin/default.rs).

## Java (Temurin and Microsoft OpenJDK)

Reviewed 2026-09-14 under D013. Temurin 25 remains the default; the other three
vendor/major combinations remain project-selected. Source review and synthetic manager compatibility are complete. The Ansible Java
role now has guest acceptance; the separate reboot checkpoint is recorded in TESTING.md.

| Variant | Exact runtime | Publisher archive SHA-256 |
|---|---|---|
| Temurin 25 | 25.0.4.1+1 | dbb698396d478e7fa2b1e50f4103324b2a99b90569ee27c33f2261f9215cf41e |
| Temurin 21 | 21.0.12.1+1 | ce79869e1307ed8ee1e2baa86a412b1eb5b75d10a01006d788a6f968bcfaee94 |
| Microsoft 25 | 25.0.4.1+1 | d3b07dd6fd096353d6834e62a6f32117eb610d0bee24cb70acb8c82832043b68 |
| Microsoft 21 | 21.0.12.1+1 | 4c0c7f5cd0b6bb81109d01f13a1678ee0f73f36c1020080d97c4de3ce3cac207 |

The official [Adoptium 25 metadata](https://api.adoptium.net/v3/assets/latest/25/hotspot?architecture=x64&image_type=jdk&os=linux)
and [Adoptium 21 metadata](https://api.adoptium.net/v3/assets/latest/21/hotspot?architecture=x64&image_type=jdk&os=linux)
identified Linux x64 HotSpot JDK archives and checksums. Microsoft's
[download page](https://learn.microsoft.com/en-us/java/openjdk/download) links the
Linux x64 archives and SHA-256 documents for both selected lines. Every downloaded
archive matched its publisher checksum. Exact URLs and extracted file manifests are
recorded in [java-review.json](../locks/java-review.json); floating metadata endpoints
are review evidence, not installation inputs.

All four release files identify the expected vendor, GNU libc build and runtime
version. The archive's `legal/java.base/LICENSE` contains GPLv2 plus the Classpath
exception; its hash is locked alongside the complete legal/assembly/component notice
files and payload. These are bundled OpenJDK distributions, not proprietary JDK terms.
Preserve all bundled notices and source/redistribution obligations. Remaining JVM tools
have their own source/licence review gates.

`./script/test-vm --java-review` passed on the dedicated Ubuntu 26.04 VM. The fixture
verifies guest identity, target user and storage before downloading/extracting exact
inputs. It registers each local JDK through the reviewed SDKMAN CLI/native pair,
compiles and runs the same Java program under all four runtimes in Bash and Zsh,
asserts effective vendor/version/JAVA_HOME, retains the Temurin 25 global default
while switching and restores its shell selection. Full payload manifests still match
after execution. Temporary files are removed after the experiment.

This proves basic Java compile/run and manager selection on this guest. Maven, Gradle,
Kotlin, Mandrel native-image, GUI/AWT, production-role repeat apply/drift and existing
project compatibility are not covered. No existing projects were supplied.

### Implemented Java role

Ansible acquires the four exact archives after storage checks and invokes the locked
SDKMAN local-registration function as the actual target user. No broker lookup,
unreviewed hook or vendor installer runs. All four payloads are immutable and verified
independently; modified registrations or files fail without replacement. Temurin 25
is set after registrations. A changed global default is privately backed up before
explicit reapply restores it. Chezmoi owns SDKMAN shell initialization.

The role passed `./script/test-vm --controller --packages --user-environment` with
134 behavioral tests. The installed JDKs compiled/ran the fixture in a fresh managed
Zsh session, vendor/version/JAVA_HOME checks passed across all four selections, the
global default stayed Temurin 25, and deliberately selecting Temurin 21 as default
failed read-only verification. Explicit reapply restored the default and its private
backup contained the previous link. Second apply and verification without the
controller also passed. The later reboot/lint checkpoint belongs in TESTING.md.

## Maven, Gradle and Kotlin

Reviewed 2026-09-14. Exact archives and extracted file manifests are in
[jvm-tools.json](../locks/jvm-tools.json). Maven, Gradle and Kotlin now have an
Ansible/SDKMAN delivery implementation; actual build acceptance is recorded separately
in TESTING.md. Source review alone does not establish complete workflow readiness.

| Tool | Stable version | Publisher archive SHA-256 |
|---|---|---|
| Maven | 3.9.16 | 80ffca22aed9e8b9713a232f3394fd81d7f20322df75efdb2b047dbd3e3a23bb |
| Gradle | 9.7.1 | acd53f1edaf02f1a8ff99879f8a34b302661a057d9b063ae9e35b552f804d20a |
| Kotlin compiler | 2.4.20 | 59e9ca74c7904ef2c122b12114937673ccce68de820a663f0ed66ccf8799e0b7 |

[Maven's download page](https://maven.apache.org/download.cgi) identifies 3.9.16 as
stable; 3.10 and 4.0 are still previews and were excluded. The binary archive matched
its published SHA-512. Its detached signature verified against Apache's published
KEYS, signer fingerprint `84789D24DF77A32433CE1F079EB80E92EB2135B1`. SHA-256 was then
recorded for installation. GPG used a temporary public-key directory, not personal keys.

[Gradle's current-version metadata](https://services.gradle.org/versions/current)
identified 9.7.1 as released/final and supplied the matching distribution checksum.
[Kotlin's 2.4.20 release](https://github.com/JetBrains/kotlin/releases/tag/v2.4.20)
provides the compiler ZIP; its SHA-256 matched publisher release metadata. All
runtime URLs are exact versions, not floating metadata endpoints.

Main code uses Apache-2.0 with bundled component notices, retained and included in
payload manifests. Maven's distribution also lists BSD, MIT, EPL-2.0, public-domain
and CDDL/GPL-with-Classpath components. Kotlin's licence README distinguishes JetBrains
code from bundled third-party code, including BSD-derived compiler components.
Gradle's distribution includes its licence/notice and bundled library notices.
The main-project licence must not be read as replacing third-party obligations.

Ansible verifies artifacts before registering local SDKMAN candidates. The role
requires selected SDKMAN and Java, sets only the corresponding tool defaults and
never changes the Java default. Existing user Maven/Gradle configuration and project
wrappers remain untouched. Payload/registration drift fails without replacement;
changed tool-default links are privately backed up on explicit reapply.

The build fixture uses an isolated Maven settings file/repository, explicit compiler
plugin 3.16.0, Surefire 3.6.0 and JUnit Jupiter 6.1.3. Those fixture dependency versions
were observed in publisher documentation/Maven Central metadata. Initial Maven
resolution uses strict checksums, then the failing-test/recovery exercise runs offline.
The fixture cache is temporary; it is not a production dependency lock or a claim
that every transitive build dependency has a workstation delivery approval.
Gradle and Kotlin fixtures use local sources without external project dependencies.

### Mandrel next slice

[Mandrel 25.0.4.1-Final](https://github.com/graalvm/mandrel/releases/tag/mandrel-25.0.4.1-Final)
is the current reviewed candidate, superseding the historical 25.0.0.1 inventory.
The Linux amd64 archive was downloaded and matches publisher SHA-256
`e47ff6bfe6a8dbb482fdc65c9a49fc6f3ba2fa61ef3cc8fb6229a88989054c31`.
Its release notes identify Ubuntu prerequisites `g++`, `zlib1g-dev` and
`libfreetype6-dev`. These need source-approved dependency delivery before a native-image
build; none is silently installed by the current JVM tool role. Mandrel remains
unverified in the catalogue pending complete archive/licence/dependency and build
acceptance. It must never replace the Temurin 25 default.

## Mandrel

Reviewed 2026-09-14. The role and native build/reboot acceptance are implemented;
the exact evidence and limits are recorded in TESTING.md.

[Mandrel 25.0.4.1-Final](https://github.com/graalvm/mandrel/releases/tag/mandrel-25.0.4.1-Final)
is the current stable security update based on JDK 25.0.4.1+1. The Linux amd64 archive
matched publisher SHA-256 `e47ff6bfe6a8dbb482fdc65c9a49fc6f3ba2fa61ef3cc8fb6229a88989054c31`.
The archive and complete file manifest are in [mandrel.json](../locks/mandrel.json).
Its main licence bytes match the exact release-tag LICENSE: GPLv2 with Classpath
exception and bundled component terms. All notices, legal files and library payloads
are retained. The historical 25.0.0.1 inventory is not an installation pin.

### Ubuntu 26.04 dependencies

The publisher's Ubuntu example names g++, zlib1g-dev and libfreetype6-dev. Both the
Ubuntu package index and actual guest APT metadata show that libfreetype6-dev has no
candidate on resolute; the development package is libfreetype-dev. This substitution
is explicit and source-reviewed, not a silent fallback.

| Package | Ubuntu source | Licence scope |
|---|---|---|
| g++ | gcc-defaults | GPL-2.0-or-later shim and BSD notices; GCC compiler GPL-3.0 with runtime library exception |
| zlib1g-dev | zlib | Zlib |
| libfreetype-dev | freetype | FTL or GPL-2.0-or-later with bundled notices |

Exact Ubuntu copyright URLs/hashes and permitted suites are recorded in
[prerequisites.json](../catalogue/prerequisites.json). The compiler implementation's
additional [GCC 15 copyright](https://changelogs.ubuntu.com/changelogs/pool/main/g/gcc-15/gcc-15_15.2.0-16ubuntu1/copyright)
was also inspected, including the GCC Runtime Library Exception.

These are internal dependencies of explicitly selected, approved Mandrel, not new
profile selections. Disabled Mandrel requests no packages. The shared Ansible APT
role checks signed Ubuntu resolute/update/security metadata, source package,
architecture and the combined resolver transaction. It rejects removals, broken
solutions and changed dependencies from unapproved suites. Verification never
refreshes indexes or repairs missing packages.

### Role and acceptance contract

Ansible acquires the verified archive after system prerequisites, then registers
`25.0.4.1-ws-mandrel` as an additional SDKMAN Java candidate. It never changes the
Temurin 25 default. Select it explicitly for a project shell; native-image is not
added globally ahead of the default JDK. Existing candidate registrations and
payload drift fail without replacement. Verification includes all required APT
state, the artifact manifest, registration and base Java default.

The disposable fixture compiled Java, built a native ELF executable with
`--no-fallback` and a 3 GiB JVM heap limit, run/assert output and restore Temurin 25.
It also removed only the guest's g++ metapackage to require independent Mandrel
verification failure, then explicitly reapplies to restore prerequisites. This is a
basic synthetic native-image test, not a Quarkus or existing-project compatibility
claim. No production workload, credentials or physical hardware were used.

## uv and CPython

Reviewed 2026-09-15 for the selected Ubuntu 26.04 LTS amd64 user runtime. The
automation controller has its own repository-local pinned Python/uv environment;
`/usr/bin/python3` is still Ubuntu's bootstrap and managed-host interpreter.

The immutable [lock](../locks/python-user.json) fixes uv 0.12.13's official
Linux x86_64 GNU archive at SHA-256
`745765a3b6e360ad76743599ae5c42e9278c7edf8bbff9fc76d05bf2623a04dd`,
both executable digests and the tagged MIT licence document digest
`860e3d7a86b84e6a7012c7a635fc64df475cebc6cce34dfeb73a5982ec58176c`.
It fixes the `python-build-standalone` CPython 3.14.7 archive from its
2026-09-01 release at SHA-256
`3959f92825141e04adf44982d3a83ee57af0877e893b0796e04c1468749d9b04`.
The archive's CPython licence file hashes to
`b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231`;
its bundled dependencies and notices have varied terms. The complete installed
interpreter tree, including the bundled notices, has 4,571 locked file/link
entries. The lock is scoped to these exact reviewed releases and amd64 GNU layout.

Ansible runs the worker as the explicit target user after the live storage guard.
It installs the uv payload under a versioned user-tool directory, downloads and
hashes the Python archive, and presents it from a temporary `file://` mirror
to the pinned uv binary with `--offline --no-cache --no-config --no-bin`.
The install permits explicit Python acquisition only during this operation.
The experiment found that uv's default executable-link mode can return success
despite failing to write conventional `~/.local/bin` links; `--no-bin` avoids that
ambiguous behavior. Its installed minor-version alias points at the temporary
directory, so the worker replaces it with a relative alias before placement.

uv writes the installation location into one `_sysconfigdata` file. Two
isolated installations produced identical SHA-256
`e140e2c3c2b5fe3d8c9280b0ed682b7b062483ad4f4704286e4003932b9d188b`
after substituting their prefix with the lock's marker. The worker rewrites only
that generated prefix to the final managed directory before an atomic directory
rename. Read-only verification checks the *final* prefix, the normalized hash,
the alias, all other file contents and executable modes, and the exact file/link
set. The interpreter files and directories are sealed read-only so normal module
imports cannot create bytecode in the source tree. Changed payloads block
installation without repair.

Chezmoi exports the managed interpreter and uv executable directories plus
`UV_PYTHON_INSTALL_DIR` and disables automatic Python downloads. It does not
set `PYTHONPATH`, replace Ubuntu Python, add global packages or modify user
projects. An uv-only selection does not acquire the interpreter; Python selection
requires uv explicitly. Existing conventional user uv/Python locations remain outside the
managed tree. A separate synthetic local-wheel project tests uv's project lock,
venv, dependency, unittest and run workflow without contacting PyPI; it gives
no real-project or native-extension compatibility claim.

Primary documentation: [uv Python command and mirror flags](https://docs.astral.sh/uv/reference/cli/),
[Python download policy](https://docs.astral.sh/uv/concepts/python-versions/),
[standalone distribution licensing](https://github.com/astral-sh/python-build-standalone/blob/main/docs/running.rst).
Guest acceptance and its limits are recorded in [TESTING.md](TESTING.md).

## Agent CLIs: delivery gates

The target selects Aider, Claude Code, Cline, Codex and OpenCode. The implemented
OpenCode and Codex sources and unauthenticated guest checks are in
[OpenCode](#opencode) and [Codex](#codex).
The [Cline CLI-only source review](#cline) now fixes its 3.0.62
wrapper and Linux binary package without npm lifecycle scripts or an SDK
package graph. Guest unauthenticated acceptance passed before and after reboot;
see [testing](TESTING.md). The other
two remain blocked by their
individual source/dependency/licence and integrity reviews, and authentication
or model sessions remain operator work.

### Aider candidate — 2026-09-15

Current [PyPI metadata](https://pypi.org/pypi/aider-chat/json) reports
`aider-chat` 0.86.2 requiring `>=3.10,<3.13`. Its public wheel SHA-256
`64f6a0c66c9f4633ad9f479bca3e64ebcba02b9da03c6b604b74a44736b2416e`
matched downloaded bytes. The wheel bundles Apache-2.0 licence text with SHA-256
`cfc7749b96f63bd31c3c42b5c471bf756814053e847c10f3eb003417bc523d30`;
its metadata has 301 dependency declarations including conditional extras.
These are candidate publisher observations, not a reviewed transitive install lock.

The exact CPython 3.12.14+20260901 GNU stripped archive, which uv 0.12.13 knows
for this platform, matched SHA-256
`72748da13197c1fb161e3afeef20a6a385ff24f2165e6e2758e47008e7faba4c`.
Its bundled CPython licence file matched
`3b2f81fe21d181c499c59a256c8e1968455d6689d269aa85373bfb6af41da3bf`.
The pinned uv binary installed this interpreter into a separate isolated
temporary directory using a local `file://` mirror, `--no-bin --no-config
--no-cache --offline` and explicit-download-only policy. Aider would use a
separate managed agent interpreter; the workstation Python 3.14.7 default stays
selected. Resolve its complete Linux/Python-3.12 dependency graph, distribution
hashes, transitive terms and isolated uv-tool verifier before enabling Aider.

Claude Code needs a current signed Linux manifest or signed Ubuntu channel and
terms review. The Cline CLI-only closure does not install its published SDK
dependencies; SDK API use would need its own transitive review. No credentials, application profiles
or whole project directories are imported for any of these reviews.

## OpenCode

Reviewed 2026-09-15 for Ubuntu 26.04 LTS amd64. The selected terminal agent uses
the official stable v1.18.31 x64 **baseline GNU** archive (not its desktop package
or floating installer). [Publisher release metadata](https://github.com/anomalyco/opencode/releases/tag/v1.18.31)
identified it as a non-prerelease asset published 2026-09-14. Its archive SHA-256
`b283e8dbe9e6fc224bb4b79992ce3bd2174b8b7b0c3e7d1b4e6024a1d11edc84`
matched the downloaded bytes. The archive has one executable `opencode`, SHA-256
`f9dab32248695e9ebd56b16a1921798fd85112cf5a69c7dfd0cabc1e17be4a11`.
It is an amd64 ELF using the GNU loader and libc/pthread/dl/math dependencies;
the disposable VM must confirm actual execution. The
[immutable lock](../locks/opencode.json) fixes both hashes and this exact layout.

The [tagged source MIT licence](https://github.com/anomalyco/opencode/blob/v1.18.31/LICENSE)
was retrieved at SHA-256
`625f0f619133f89bbbb2abe37369613dfa1885eba1e50d02170deb62bb42cb6b`.
The binary reports embedded Bun 1.3.14. Its
[tagged component licence inventory](https://github.com/oven-sh/bun/blob/bun-v1.3.14/docs/project/license.mdx),
retrieved at SHA-256
`7305efadd1f8222666b20e8887ae22509e43e6f1484c017853d49ec738214371`,
describes MIT Bun code, statically linked LGPL-2 JavaScriptCore/WebKit and other
bundled free-software terms. This is the source/licence scope for personal
installation; the repository distributes neither binary nor modified runtime.

Ansible invokes the reviewed extraction/complete-payload guard as the explicit
target user after storage preflight. Existing changed payloads fail without
replacement. Chezmoi makes the versioned binary available in managed Zsh and
exports `OPENCODE_DISABLE_AUTOUPDATE=1`; the
[tagged upgrade code](https://github.com/anomalyco/opencode/blob/v1.18.31/packages/opencode/src/cli/upgrade.ts)
honors that flag. No global OpenCode profile is replaced or copied.
Independent verification hashes the binary and exact artifact file set without
launching it. OpenCode's `--version` itself may create XDG state; the synthetic
guest fixture uses private disposable config/cache/data/state locations.

The guest check is limited to local version/help, repeat apply, visibility through
NVM switching, deliberate payload drift/refusal and fixture restoration. It does
not log in, invoke models, download plugins or prove provider/session workflows.
The full workstation and remaining agents have separate readiness gates in
[TESTING.md](TESTING.md) and [TASKS.md](../TASKS.md).

## Codex

Reviewed 2026-09-15 for Ubuntu 26.04 LTS amd64. [Official OpenAI Docs](https://learn.chatgpt.com/docs/codex/cli)
describes Linux CLI installation and a separate sign-in step. The documented
standalone shell installer is excluded by this repository's no-pipe-shell policy.
The publisher's latest non-prerelease `openai/codex` release metadata reports
`rust-v0.154.0`, published 2026-09-09. Its single-file Linux x86_64 musl CLI
archive, SHA-256
`d7e18b2597ae8f242f5f31ee9e90deef48dbc9edd634d9868fb6435d08c07f02`,
matched the [release asset digest](https://github.com/openai/codex/releases/tag/rust-v0.154.0).
The extracted static-pie amd64 ELF hashes to
`3188814c35471432d4123203e0eb38e5bddc60226e3d7ddf0e59e649ea140022`.
The [immutable lock](../locks/codex.json) fixes the exact URL, archive and
executable digests and one-member layout.

The release's Sigstore bundle hashes to
`4bc2431d7535f2646c970d2f91f3fca76e64924468432f0faeed7c54b15fda22`.
Its Rekor body names the same extracted executable digest. The signature verifies
over those executable bytes using the bundled certificate's public key; the
certificate identifies `openai/codex`'s tagged `rust-release` GitHub workflow.
The certificate chain and transparency log signature have **not** been independently
validated here; the pinned publisher release digest is the installation integrity
boundary. Do not call the bundle a fully verified provenance attestation.

The [tagged Apache-2.0 licence](https://github.com/openai/codex/blob/rust-v0.154.0/LICENSE)
hashes to `d17f227e4df5da1600391338865ce0f3055211760a36688f816941d58232d8dc`.
The [tagged NOTICE](https://github.com/openai/codex/blob/rust-v0.154.0/NOTICE)
hashes to `9d71575ecfd9a843fc1677b0efb08053c6ba9fd686a0de1a6f5382fd3c220915`
and names Ratatui-derived MIT code. These are source/notice terms for personal
installation; the repository does not redistribute the CLI binary.

Ansible runs the locked artifact worker as the explicit target user only after
storage preflight. It refuses changed installed payloads. Chezmoi adds the versioned
executable directory without replacing existing Codex configuration or credentials.
Independent verification reads the complete artifact payload without executing
Codex. The guest passed unauthenticated version/help, stable shell visibility,
two applies and deliberate drift/recovery twice, including after reboot, using
private disposable state. Codex warned that helper aliases could not be created
under the temporary `CODEX_HOME`; the local version/help checks still passed.
Sign-in, account access, model calls and project sessions remain operator work.

## Cline

Reviewed 2026-09-15 for Ubuntu 26.04 LTS amd64. The official
[CLI distribution description](https://github.com/cline/cline/blob/cli-v3.0.62/apps/cli/DISTRIBUTION.md)
defines a Node wrapper plus platform-specific, compiled Bun binary and a
separate Cline VS Code extension. The latest non-prerelease npm CLI release at
review was **3.0.62**, published 2026-09-15T06:04Z and tagged
[`cli-v3.0.62`](https://github.com/cline/cline/releases/tag/cli-v3.0.62).
Its npm `latest` metadata and the corresponding platform metadata both named
3.0.62; the prior 3.0.61 source-ledger observation is superseded for delivery.

The exact `cline` wrapper archive hashes to SHA-256
`7a4df4ecf7613cb872c5c8916d82d247af13a69b4033bef88d41c5f13820802c`
and SHA-512
`f571f56e93e28bdc9e4768cd9f8bc41275d723b261de6aad41d84f02225749c3d1304a4509be2114a630138b547cde9d8867a6c5af0b11df2478827a8c190c64`.
The `@cline/cli-linux-x64` archive hashes to SHA-256
`f1fdf64dab9ea37546fe39662ad0336712e31497eee954fd82003d7c79b35320`
and SHA-512
`1d18ffdec158ffcd6d3afdf2ce75624ae4ba1b994457b1919442ef3e2d64d1e01fcec825847ea480f9c508cfa3309ec2ddebf07fc9d5cefadc3fec62a4f9478b`.
Both SHA-512 values match their [npm registry package metadata](https://registry.npmjs.org/cline/3.0.62)
and [platform package metadata](https://registry.npmjs.org/@cline%2Fcli-linux-x64/3.0.62),
respectively. The platform archive is 52,599,487 bytes and contains 142
regular members: one 151,320,896-byte Linux amd64 ELF, package metadata,
the Hub webview/assets and a plugin sandbox bootstrap. The ELF itself hashes
to `2057f88bda64726ef38f5ab43902bd98f3f96caa68837ce00bd7b83287d3c810`.
The wrapper has six regular members including its binary resolver, CA-store
helper, licence, README and postinstall. The [immutable lock](../locks/cline.json)
fixes both URLs, both archive hashes and every one of the 148 extracted file
names, lengths, SHA-256 hashes and normalized executable modes.

The npm provenance payloads for both exact archives name the publisher's
`cline/cline` `cli-publish.yml` workflow and commit
`d718dd16f850c4c915a8214441a831e00cb28c75`; the annotated release tag
points to that same commit. Their attestation subjects name the same SHA-512
archives. The attestation signatures, npm signing-key chain and Rekor inclusion
proofs were **not independently cryptographically verified**. The locked
registry-published SHA-512 digests and exact archive/file hashes form the
installation integrity boundary. No reproducible-build claim is made.

The [tagged root Apache-2.0 licence](https://github.com/cline/cline/blob/cli-v3.0.62/LICENSE)
and the wrapper's bundled licence have identical SHA-256
`f704446a5f1271608805598b557e4288cf8580477ea038c9c3d8b361f693f6b8`.
The platform package itself has no `license` metadata field or licence file;
its publisher's tagged source declares Apache-2.0. The tagged
[publish workflow](https://github.com/cline/cline/blob/cli-v3.0.62/.github/workflows/cli-publish.yml)
pins Bun 1.3.13, also reported by the embedded binary. Bun's
[version-specific licence inventory](https://github.com/oven-sh/bun/blob/bun-v1.3.13/docs/project/license.mdx)
describes MIT Bun code and statically linked LGPL-2 JavaScriptCore/WebKit,
along with other linked free-software terms. This review covers personal
installation, not redistribution or a full compiled-dependency SBOM.

The published wrapper declares five exact `@cline` SDK/core dependencies and
six optional platform packages, but its `bin/cline` source uses only Node
built-ins to locate and spawn the compiled binary. The approved CLI-only
delivery installs the wrapper and matching Linux binary package in the
publisher's `node_modules` layout. It does **not** install the SDK package
graph or expose the npm JavaScript API; a future SDK use needs its own complete
transitive lock. The published postinstall can rename an existing Hub discovery
record and cache a duplicate executable, so the role never runs it. The tagged
[updater source](https://github.com/cline/cline/blob/cli-v3.0.62/apps/cli/src/commands/update.ts)
checks `CLINE_NO_AUTO_UPDATE=1` before a registry fetch or detached update.
The managed launcher sets that variable and executes the unmodified wrapper
with the reviewed NVM default Node binary, independent of active project
selection. The wrapper's OS CA helper may write ordinary private Cline state
on a user invocation; independent verification never invokes it.

Ansible sequences acquisition and placement as the explicit target user after
storage and Node guards. Chezmoi owns only the launcher PATH declaration.
Changed managed files fail independent read-only verification and repeat apply
without replacement. Guest version/help, runtime switching, repeat apply,
drift refusal/recovery and reboot evidence passed in the
[testing checkpoint](TESTING.md); provider sign-in, Hub sessions, model calls,
extension integration and actual projects remain separate acceptance work.
