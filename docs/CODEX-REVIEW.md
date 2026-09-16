# Codex CLI source and delivery review

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
