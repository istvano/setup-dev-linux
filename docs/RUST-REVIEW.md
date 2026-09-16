# Rust source and delivery review

Reviewed 2026-09-14. The selected current stable toolchain is Rust **1.98.1**
(`48a229cea`, dated 2026-09-03) for `x86_64-unknown-linux-gnu`. The selected manager
is rustup **1.29.1**. The official versioned channel manifest and rustup stable-release
manifest are published under <https://static.rust-lang.org/>.

`locks/rust.json` binds the exact rustup-init binary, versioned channel manifest and
its checksum sidecar, and the minimal Cargo, rust-std and rustc component archives.
Each input has a publisher SHA-256. It also records the two release-specific licence
texts for rustup and Rust, and all 153 files in the resulting minimal toolchain.
Rust and rustup are dual-licensed under Apache-2.0 or MIT; distributed components carry
their own notices.

Ansible downloads and validates every input before execution. It invokes rustup-init
directly with shell modification and toolchain installation disabled, then lets that
exact manager install the pinned toolchain from a staged local file distribution.
The complete state is validated before one rename into
`~/.local/share/linux-os-setup/rust/1.29.1-1.98.1`. Chezmoi exports the dedicated
RUSTUP_HOME and CARGO_HOME and adds the Cargo shim directory to PATH. Conventional
`~/.rustup`, `~/.cargo` and project toolchain files remain outside the managed state.

Independent verification hashes rustup and the full toolchain, checks the exact shim
set and reads the default/profile settings without executing Rust tools, downloading
or repairing. Existing modified state causes installation to fail rather than replace
it. The selected Ubuntu `g++` prerequisite is shared with Mandrel and deduplicated in
the package transaction.

The disposable Ubuntu 26.04 guest passed the complete suite before and after reboot:
167 behavioral tests, zero Ansible lint findings across 11 playbooks, two applies,
read-only verification, a local offline Cargo test/build/run, exact project selection,
and Rust availability after Node switching. Toolchain/default drift and removal of the
shared linker failed without repair; explicit fixture/package restoration recovered
verification. This does not prove crates.io/private registries, cross targets, native
libraries or real projects.
