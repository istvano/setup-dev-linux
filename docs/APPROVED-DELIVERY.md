# Approved package and runtime delivery

Reviewed on 2026-09-13. The machine-readable authority is
[catalogue/approved-delivery.json](../catalogue/approved-delivery.json), checked against
catalogue ownership, identifiers and licence status. The larger source-review ledger
retains historical observations and unfinished research; its records alone authorize
no installer tasks.

| Capability | Reviewed Ubuntu source | Licence scope | Synthetic acceptance |
|---|---|---|---|
| Git | git | GPL-2.0-only main code and bundled free-software notices | Local index and staged diff |
| curl | curl | curl licence and bundled notices | Loopback HTTP JSON retrieval |
| jq | jq | MIT code, documentation notices | JSON extraction |
| Git LFS | git-lfs | MIT/Expat source and packaging | Local clean/smudge round trip |
| ripgrep | rust-ripgrep | MIT or Unlicense, BSD-3-Clause completion | Match and no-match exit behavior |
| ShellCheck | shellcheck | GPL-3.0-or-later | Valid script and SC2086 negative fixture |
| Zsh | zsh | Zsh with bundled notices | Fresh shell and managed initialization |
| zsh-autosuggestions | zsh-autosuggestions | MIT/Expat | Loaded plugin functions |
| zsh-syntax-highlighting | zsh-syntax-highlighting | BSD-3-Clause | Loaded last in managed initialization |

Exact reviewed copyright URLs and document SHA-256 values are recorded in the
registry. For example, Ubuntu publishes the
[ripgrep release and dependencies](https://packages.ubuntu.com/resolute/ripgrep),
[Git LFS copyright](https://changelogs.ubuntu.com/changelogs/pool/universe/g/git-lfs/git-lfs_3.7.1-1/copyright),
and [ShellCheck copyright](https://changelogs.ubuntu.com/changelogs/pool/universe/s/shellcheck/shellcheck_0.11.0-2/copyright).
These approvals use the reviewed Ubuntu supported channel rather than an exact
upstream-version pin, consistent with D013. Runtime inspection requires trusted
Ubuntu metadata for resolute, resolute-updates or resolute-security, amd64/all
architecture, the expected source-package name and SHA-256 metadata. APT enforces
signed metadata and downloaded package integrity.

The in-memory resolver also rejects broken solutions, removals and changed
dependencies from outside the approved Ubuntu suites. Existing APT trust
configuration is an input to that check; this feature does not yet implement
management of repository keys and source files. Third-party repository delivery and
system-security configuration remain separate unfinished work.

Read-only verification matches the installed version against available approved
repository metadata. It does not reconstruct historical installation provenance,
verify every installed file byte, refresh APT indexes or repair drift. Missing
metadata is a failure rather than an assumed pass. Actual guest pass/fail evidence
is recorded in [TESTING.md](TESTING.md).

## Immutable upstream tools and Node

Reviewed release URLs, archive SHA-256, licence-document SHA-256 and complete file
manifests are recorded in [user-tools.json](../locks/user-tools.json) and
[node.json](../locks/node.json). These are separate from Ubuntu channel approval.

| Capability | Reviewed version | Delivery | Licence scope |
|---|---|---|---|
| chezmoi | 2.72.1 | Ansible places verified Linux amd64 binary | MIT |
| Oh My Zsh | be8da5c77192eb3da3699ea7c5e47bdfaa5eea4e | Ansible places immutable source tree | MIT |
| NVM | 0.40.7 | Ansible places manager; chezmoi initializes it | MIT |
| Node | 26.8.2 | Verified archive installed through NVM offline binary mode | MIT with bundled notices |
| pnpm | 12.4.1 | Independent immutable Linux amd64 bundle | MIT with bundled notices |
| Go | 1.27.1 | Verified Linux amd64 archive and complete payload manifest | BSD-3-Clause with bundled notices |
| Rust/rustup | 1.98.1 / 1.29.1 | Exact minimal components installed by pinned rustup from local staged files | Apache-2.0 OR MIT with bundled notices |
| User uv | 0.12.13 | Verified immutable Linux amd64 binary pair; separate from controller uv | MIT |
| User Python | 3.14.7+20260901 | uv installs from a locked local mirror; complete sealed interpreter payload verified | CPython licence with bundled notices |
| OpenCode | 1.18.31 | Verified single-file Linux amd64 GNU CLI payload; no automatic update | MIT; bundled Bun/WebKit LGPL-2 and notices |
| Codex CLI | 0.154.0 | Verified single-file Linux amd64 musl CLI payload; archive member normalized to `codex` | Apache-2.0 with Ratatui MIT notice |
| Cline CLI | 3.0.62 | Two exact npm archives in a CLI-only prefix; fixed-Node launcher, no npm postinstall/SDK packages or automatic update | Apache-2.0; embedded Bun MIT/LGPL-2 scope |

Existing immutable payload drift is a failure, not permission to replace modified
files. Verification reads the installed payload against the committed manifest
without executing managers or repairing files. The managed Node default is also
verified. Synthetic feature results and their limits are in TESTING.md.

[sdkman-review.json](../locks/sdkman-review.json) backs the implemented SDKMAN
5.23.0/native 0.7.35 manager role (Apache-2.0). Its [source and guest review](SDKMAN-REVIEW.md)
records policy ownership, independent verification and drift refusal. Java archives
have [separate review](JAVA-REVIEW.md). The floating SDKMAN installer is not executed.
Go and Rust source, ownership and guest limits are recorded in
[GO-REVIEW.md](GO-REVIEW.md) and [RUST-REVIEW.md](RUST-REVIEW.md).
User uv/Python, OpenCode, Codex and Cline source, ownership and guest limits are recorded in
[PYTHON-REVIEW.md](PYTHON-REVIEW.md), [OPENCODE-REVIEW.md](OPENCODE-REVIEW.md)
and [CODEX-REVIEW.md](CODEX-REVIEW.md), [CLINE-REVIEW.md](CLINE-REVIEW.md).
The remaining selected agent candidates and their unresolved delivery gates are in
[AGENT-REVIEW.md](AGENT-REVIEW.md).
