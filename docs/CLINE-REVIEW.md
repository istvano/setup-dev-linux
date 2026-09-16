# Cline CLI-only source and delivery review

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
