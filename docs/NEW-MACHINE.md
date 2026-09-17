# Setting up a new workstation

This is the operator runbook for moving to a new machine. It assumes the old
machine is still running and reachable over the network.

Nothing here partitions disks, formats filesystems or deletes data on either
machine. The copy never deletes on the destination.

## Before you start

On the **new** machine:

- Ubuntu 26.04 LTS amd64 installed, with a user account and an SSH server
  (`sudo apt install openssh-server`).
- Your SSH public key from the old machine in `~/.ssh/authorized_keys`.

On the **old** machine:

- An independently verified backup. The migration reads, never moves, but a
  workstation move is the wrong moment to discover a backup gap.
- This repository checked out, and `just verify-static` passing.

## 1. Check what will be installed

```bash
just plan config/your-machine.json
```

`plan` writes nothing, downloads nothing and uses no privilege. It lists each
selection with its delivery route and names anything blocked.

The set of software comes from `manifest/`, which records decisions made in
[the inventory review](INVENTORY-REVIEW.md). To change what a new machine gets,
change the manifest — not the machine, and then the manifest.

## 2. Check the target machine

```bash
just preflight config/your-machine.json
```

This runs on the new machine and fails before any write if the declared disks
and mounts do not match what is actually there.

## 3. Install

```bash
just install config/your-machine.json
```

Run this **as your own user**, not as root, and not with `sudo`. The installer
raises privilege for the system tasks that need it and refuses to run the whole
bootstrap as root.

It configures the signed third-party APT sources, installs the manifest's
packages and snaps, installs each pinned release binary after verifying its
SHA-256, then sets up the user runtimes. Re-running it is safe: the second run
changes nothing that is already correct.

To install part of the manifest, name the groups:

```bash
just install config/your-machine.json core,dev,kubernetes
```

## 4. Verify

```bash
just verify config/your-machine.json
```

Verification reads the installed system and reports drift. It never repairs.
An `incomplete` result names what has no verification yet; it is not a pass.

## 5. Move your files

From the **old** machine, preview first:

```bash
just migrate-plan config/your-machine.json newbox
```

Then copy:

```bash
just migrate config/your-machine.json newbox
```

This copies the trees declared in `manifest/migrate.json`, excluding build
output and package caches that regenerate themselves. It is resumable: if it is
interrupted, run it again and it continues.

When the copy finishes, migrate runs rsync a second time in dry-run mode. A
byte-complete copy has nothing left to transfer, so anything still outstanding
is reported as a failure rather than a warning.

Credentials do not travel in that copy. Move them deliberately:

```bash
just migrate-secrets config/your-machine.json newbox
```

This covers `~/.ssh`, `~/.gnupg`, `~/secure`, `~/.aws`, `~/.azure`, `~/.kube`,
`~/.docker`, `~/.config/gh` and the agent CLI session files, with permissions
preserved.

One file is deliberately never copied: `~/.ssh/authorized_keys`. It is what
grants you access to the new machine, so replacing it mid-migration revokes the
key the copy is running over and locks you out with the transfer half done.
Set up your keys on the new machine before you start — step 0 above — and add
anything else you need there by hand afterwards.

## 6. Finish by hand

These are deliberately not automated:

- **Authenticate** every tool that needs it: `gh auth login`, cloud CLIs, the
  agent CLIs, Bitwarden, Slack, Thunderbird.
- **VPN profiles** and their certificates.
- **Backup destination and schedule** on the new machine.
- **GPU**: confirm the NVIDIA driver loaded (`nvidia-smi`) and, if Secure Boot
  is on, enrol the module signing key. A reboot is required.
- **Docker group**: log out and back in before the group membership applies.
- **IntelliJ IDEA**: install fresh rather than using the copy in `~/Apps`.

## Private Git identities

Optionally add `"user_settings_file": "user-settings.local.json"` to the explicit
machine configuration. The path resolves relative to that machine file. The settings
file must be owned by the invoking user, with no group/other access (for example,
mode 0600). It uses the committed [schema](../config/user-settings.schema.json):

```json
{
  "schema_version": 1,
  "identities": [
    {
      "scope": "personal",
      "directory": "/absolute/path/to/personal/projects",
      "name": "Your personal Git name",
      "email": "your-personal-address@example.invalid"
    },
    {
      "scope": "work",
      "directory": "/absolute/path/to/work/projects",
      "name": "Your work Git name",
      "email": "your-work-address@example.invalid"
    }
  ]
}
```

Supply actual private values locally. Directories must not overlap or use glob
patterns. Missing identity settings are reported as incomplete; no identity is guessed.
Verification reports contain a settings digest, never the identity values.

## Private proxy settings

`proxyon` reads `~/.config/linux-os-setup/proxy.local.json`, or an explicit
`WORKSTATION_PROXY_SETTINGS` path. This runtime JSON file must be owned by the current
user, have no group/other access and be a regular file rather than a symlink. It
contains exactly four string keys: `http_proxy`, `https_proxy`, `all_proxy`, `no_proxy`.
Nonempty proxy URLs use http, https, socks5 or socks5h. Empty strings explicitly clear
that proxy during activation. Control characters and duplicate/unknown keys fail.
The helpers export both lowercase and uppercase forms and never evaluate shell code.

The first `proxyon` saves prior values, unset state and export attributes. Repeated
activation retains that original snapshot. `proxyoff` restores it; repeated deactivation
is harmless. Missing/invalid settings leave the environment unchanged. Do not put
proxy credentials in the repository or copy old secret-bearing shell function bodies.

## What this cannot tell you

The VM acceptance cycle exercises everything except the GPU stack, because the
guest has no NVIDIA hardware. GPU delivery is proven only on the physical
machine.
