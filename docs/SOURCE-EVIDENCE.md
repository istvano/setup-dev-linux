# Source evidence

Source, licence and integrity review for what this repository installs outside the
Ubuntu archive. The machine-readable authority is `catalogue/source-review.json`,
rendered to [SOURCE-REVIEW.md](SOURCE-REVIEW.md); the pins themselves live in
`manifest/binaries.json` (zed, obsidian), `manifest/repositories.json` (signing-key
fingerprints) and `locks/bootstrap.json` (the controller toolchain).

The review covers third-party sources only: 25 host capabilities across upstream
releases, the VS Code marketplace, vendor APT repositories, snaps and the
controller's PyPI dependencies. Ubuntu archive packages carry no per-item record: the
archive signature is the guarantee, and checking each one repeats it. See
[D018](DECISIONS.md).

## Command-line tools moved out (2026-11-26)

This document used to carry sections for SDKMAN, the Temurin and Microsoft JDKs,
Maven, Gradle and Kotlin, Mandrel, uv and CPython, the agent CLIs (Aider, OpenCode,
Codex, Cline, Claude Code, Copilot) and their locks. All of them are command-line
tools, which setup-dev-linux-wsl now installs on a Linux machine as well as in WSL;
[MOVED.md](MOVED.md) records where each one went. Their review was removed with the
roles and locks it justified. It remains in this repository's history (before the host
refactor) for anyone who needs the reasoning; it is not an input to anything here.

Go and Rust had sections before that. Both roles were omitted on 2026-09-16 (D019),
and their review was dropped with them.

## The shared Anthropic key

claude-desktop's repository is signed by the Anthropic release key. setup-dev-linux-wsl
installs Claude Code from Anthropic's claude-code repository with the same key, at
`/etc/apt/keyrings/anthropic.asc`. This repository vendors that key byte-for-byte as
`manifest/keys/anthropic.asc` (fingerprint `31DDDE24DDFAB679F42D7BD2BAA929FF1A7ECACE`)
and places it at the same path, armoured and unchanged, so the two repositories never
rewrite each other's keyring. The two sources use different URIs
(`claude-desktop/apt/stable` here, `claude-code/apt/stable` there), so APT never sees
one URI with two `Signed-By` values. `tests/test_host_only.py` checks the key's
SHA-256 against setup-dev-linux-wsl's copy.
