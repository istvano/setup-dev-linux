# Java archive review and source acceptance

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

## Implemented Java role

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
