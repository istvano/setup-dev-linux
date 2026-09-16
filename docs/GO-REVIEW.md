# Go source and delivery review

Reviewed 2026-09-14. Go **1.27.1** is the current stable release selected for
Ubuntu 26.04 amd64. The publisher release page is <https://go.dev/dl/>. The selected
Linux amd64 archive is
`https://go.dev/dl/go1.27.1.linux-amd64.tar.gz`, with publisher SHA-256
`63d339f0da5ab53635a56f2490a7984dfe12dfcff22ad749f63edaf590168445`.
Go is distributed under the BSD 3-Clause licence; the archive also carries bundled
component notices.

`locks/go.json` binds the exact URL, archive checksum, licence checksum, entrypoint
and all 15,639 archive entries. Installation rejects unsafe archive paths and places
the verified payload at
`~/.local/share/linux-os-setup/tools/go/go1.27.1`, rather than `/usr/local/go`.
Chezmoi adds that versioned `bin` directory to PATH. The role does not define GOROOT,
GOPATH, module proxies or authentication, and does not edit project files.

Independent verification hashes the complete installed payload without executing Go,
downloading modules or repairing state. An existing changed payload fails both verify
and install; the operator must restore the fixture or approve a future versioned update.

The disposable Ubuntu guest passed the 158-test controller and user-environment suite.
A fresh managed Zsh reported Go 1.27.1 for linux/amd64, then initialized, tested, built
and ran a local module with `GOPROXY=off`, `GOSUMDB=off` and `GOTOOLCHAIN=local`.
Deliberate VERSION-file drift failed verification and replacement, and restoring the
fixture recovered it. The combined Rust runtime suite later repeated this acceptance
successfully after a real guest reboot. It does not prove
external modules, private proxies, CGO libraries, cross-compilation or real projects.
