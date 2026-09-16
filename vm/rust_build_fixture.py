"""Synthetic offline Rust workflow for the dedicated guest acceptance suite."""
from pathlib import Path
import os
import subprocess


def check(fixture):
    root = fixture / 'rust-build'
    source = root / 'src'
    source.mkdir(parents=True)
    (root / 'Cargo.toml').write_text(
        '[package]\nname = "offline-fixture"\nversion = "0.1.0"\nedition = "2024"\n')
    (source / 'lib.rs').write_text(
        'pub fn answer() -> u32 { 6 * 7 }\n'
        '#[cfg(test)] mod tests { use super::*; '
        '#[test] fn expected() { assert_eq!(answer(), 42); } }\n')
    (source / 'main.rs').write_text(
        'fn main() { println!("{}", offline_fixture::answer()); }\n')
    (root / 'rust-toolchain.toml').write_text(
        '[toolchain]\nchannel = "1.98.1"\nprofile = "minimal"\n')
    command = r'''
set -e
cd "$1"
rustup --version | grep -F 'rustup 1.29.1'
rustc --version | grep -F 'rustc 1.98.1 (48a229cea 2026-09-01)'
cargo --version | grep -F 'cargo 1.98.1 (797e8a9bc 2026-08-05)'
[[ "$RUSTUP_HOME" == "$HOME/.local/share/linux-os-setup/rust/1.29.1-1.98.1/rustup" ]]
[[ "$CARGO_HOME" == "$HOME/.local/share/linux-os-setup/rust/1.29.1-1.98.1/cargo" ]]
rustup show active-toolchain | grep -F '1.98.1-x86_64-unknown-linux-gnu'
cargo generate-lockfile --offline
cargo test --offline --locked
cargo build --offline --locked
[[ "$(./target/debug/offline-fixture)" == 42 ]]
nvm use --silent default
rustc --version | grep -F 'rustc 1.98.1'
cargo --version | grep -F 'cargo 1.98.1'
rustup default | grep -F '1.98.1-x86_64-unknown-linux-gnu (default)'
'''
    environment = {
        key: value for key, value in os.environ.items()
        if not key.startswith(('CARGO_', 'RUSTUP_')) and
        key not in ('RUSTC', 'RUSTDOC', 'RUSTFLAGS')
    }
    environment.update(CARGO_NET_OFFLINE='true')
    result = subprocess.run(
        ['zsh', '-i', '-c', command, '--', str(root)], env=environment,
        capture_output=True, text=True, timeout=180)
    if result.returncode:
        print(result.stdout[-4000:])
        print(result.stderr[-2000:])
        raise AssertionError('Rust build fixture failed')
    binary = root / 'target/debug/offline-fixture'
    assert binary.read_bytes().startswith(b'\x7fELF')
    print('PASS: Rust 1.98.1 Cargo test/build/run, project pin and Node-switch stability with registry networking disabled')
