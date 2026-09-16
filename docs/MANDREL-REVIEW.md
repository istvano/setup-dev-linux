# Mandrel source and native prerequisite review

Reviewed 2026-09-14. The role and native build/reboot acceptance are implemented;
the exact evidence and limits are recorded in TESTING.md.

[Mandrel 25.0.4.1-Final](https://github.com/graalvm/mandrel/releases/tag/mandrel-25.0.4.1-Final)
is the current stable security update based on JDK 25.0.4.1+1. The Linux amd64 archive
matched publisher SHA-256 `e47ff6bfe6a8dbb482fdc65c9a49fc6f3ba2fa61ef3cc8fb6229a88989054c31`.
The archive and complete file manifest are in [mandrel.json](../locks/mandrel.json).
Its main licence bytes match the exact release-tag LICENSE: GPLv2 with Classpath
exception and bundled component terms. All notices, legal files and library payloads
are retained. The historical 25.0.0.1 inventory is not an installation pin.

## Ubuntu 26.04 dependencies

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

## Role and acceptance contract

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
