# Selected agent CLI delivery gates

The target selects Aider, Claude Code, Cline, Codex and OpenCode. The implemented
OpenCode and Codex sources and unauthenticated guest checks are in
[OPENCODE-REVIEW.md](OPENCODE-REVIEW.md) and [CODEX-REVIEW.md](CODEX-REVIEW.md).
The [Cline CLI-only source review](CLINE-REVIEW.md) now fixes its 3.0.62
wrapper and Linux binary package without npm lifecycle scripts or an SDK
package graph. Guest unauthenticated acceptance passed before and after reboot;
see [testing](TESTING.md). The other
two remain blocked by their
individual source/dependency/licence and integrity reviews, and authentication
or model sessions remain operator work.

## Aider candidate — 2026-09-15

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
