# JVM build-tool source review

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

## Mandrel next slice

[Mandrel 25.0.4.1-Final](https://github.com/graalvm/mandrel/releases/tag/mandrel-25.0.4.1-Final)
is the current reviewed candidate, superseding the historical 25.0.0.1 inventory.
The Linux amd64 archive was downloaded and matches publisher SHA-256
`e47ff6bfe6a8dbb482fdc65c9a49fc6f3ba2fa61ef3cc8fb6229a88989054c31`.
Its release notes identify Ubuntu prerequisites `g++`, `zlib1g-dev` and
`libfreetype6-dev`. These need source-approved dependency delivery before a native-image
build; none is silently installed by the current JVM tool role. Mandrel remains
unverified in the catalogue pending complete archive/licence/dependency and build
acceptance. It must never replace the Temurin 25 default.
