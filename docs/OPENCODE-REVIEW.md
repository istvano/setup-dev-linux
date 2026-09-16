# OpenCode CLI source and delivery review

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
