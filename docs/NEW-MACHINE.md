# Setting up a new workstation

This is the operator runbook for setting up a fresh machine. This repository
installs software only; it does not copy files from another machine.

Nothing here partitions disks, formats filesystems or deletes data.

## Before you start

- Ubuntu 26.04 LTS amd64 installed, with a user account.
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
just apply config/your-machine.json
```

Run this **as your own user**, not as root, and not with `sudo`. The installer
raises privilege for the system tasks that need it and refuses to run the whole
bootstrap as root.

It configures the signed third-party APT sources, installs the manifest's
packages and snaps, installs each pinned release binary after verifying its
SHA-256, then the VS Code extensions and the GNOME settings. Re-running it is
safe: the second run changes nothing that is already correct.

Command-line tools, runtimes, the shell, dotfiles and Docker are not installed
here: setup-dev-linux-wsl installs them on a Linux machine too
(`./bootstrap apply --target linux` in that repository; see [MOVED.md](MOVED.md)).

To install part of the host, name the profiles (a server leaves out the desktop
ones; `firewall` can be selected on its own):

```bash
just apply config/your-machine.json desktop,dev-gui,lab
```

The choice is recorded in `${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json`
(outside the clone, private to your user), and later runs without a profile list
reuse it; the output's `Profiles source:` line says which applied. Pass
`--profiles` again to change it. Deleting that file makes the next run without
`--profiles` select the default, which includes the desktop.

## 4. Verify

```bash
just verify config/your-machine.json
```

Verification reads the installed system and reports drift. It never repairs.
An `incomplete` result names what has no verification yet; it is not a pass.

## 5. Finish by hand

These are deliberately not automated:

- **Authenticate** the desktop applications that need it: Bitwarden, Slack,
  Thunderbird. Command-line tools (`gh`, cloud CLIs, agent CLIs) and the Git
  identity belong to setup-dev-linux-wsl.
- **VPN profiles** and their certificates.
- **Backup destination and schedule** on the new machine.
- **GPU**: confirm the NVIDIA driver loaded (`nvidia-smi`) and, if Secure Boot
  is on, enrol the module signing key. A reboot is required.

## What this cannot tell you

The VM acceptance cycle exercises everything except the GPU stack, because the
guest has no NVIDIA hardware. GPU delivery is proven only on the physical
machine.
