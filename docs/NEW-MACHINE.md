# Setting up a new workstation

The operator runbook for a fresh machine: install Ubuntu, run `apply`, which sets up
the host and then hands off to setup-dev-linux-wsl for the command line, log in
again, verify. This repository installs software only; it copies nothing from
another machine, and nothing here partitions disks, formats filesystems or deletes
data.

## Before you start

- Ubuntu 26.04 LTS amd64, freshly installed, with your user account. The repository
  is for fresh installs only: a machine set up by an earlier version is reinstalled
  (D023 in [DECISIONS.md](DECISIONS.md)).
- Network access: `apply` downloads packages, and the handoff clones
  setup-dev-linux-wsl from GitHub.
- `git` and `gpg`, which a minimal install may lack. `preflight` and `apply` check
  for both on the system path and stop, before changing anything, with
  `prerequisite:git` or `prerequisite:gpg` naming the package to install:

  ```bash
  sudo apt install git gnupg
  ```

- This repository cloned, for example into `~/workspace/setup-dev-linux`. Run the
  commands below from its root.

## 1. Describe the machine

Copy the example for your disk layout, `config/standard-single.example.json` or
`config/standard-split.example.json`, to `config/your-machine.local.json` (Git
ignores `*.local.json`). Set `example_only` to `false`, `target.user` to your user,
and replace every `REPLACE_` value with the real stable disk identity
(`/dev/disk/by-id/...`), minimum size and filesystem UUID
(`findmnt -o TARGET,UUID`). Keep the file private: it holds this machine's disk
identities.

## 2. Check what will run

```bash
./bootstrap plan --config config/your-machine.local.json
```

`plan` writes nothing, downloads nothing and uses no privilege. It prints the
`Profiles:` line and its source, each selected capability with its delivery route,
and the stages `apply` would run, ending with `stage:handoff`. On a machine where
setup-dev-linux-wsl has recorded no profile choice yet, it also prints the `hint:`
line described in step 4.

To change the host profiles, pass `--profiles`. A server leaves out the desktop set
(`desktop,media,productivity,ai,network,dev-gui`); `firewall` can be selected on its
own. A server reached over SSH needs `--allow-ssh` (or, deliberately, `--no-allow-ssh`)
with the firewall: `plan` shows the decision as `firewall:ssh`, and `apply` over SSH
refuses without one:

```bash
./bootstrap plan --config config/your-machine.local.json --profiles gpu,firewall --allow-ssh
```

## 3. Check the target machine

```bash
./bootstrap preflight --config config/your-machine.local.json
```

This fails before any write if the declared disks and mounts do not match what is
actually there, or if `git` or `gpg` is missing.

## 4. Apply: the host, then the handoff

Run this **as your own user**, not as root, and not with `sudo`. The installer
raises privilege for the system tasks that need it and refuses to run as root.

After the preflight checks pass and before anything is written, `apply` asks for
your sudo password once:

```
[setup-dev-linux] sudo password for <you>:
```

It checks the password with sudo (three attempts, then `sudo-authentication-failed`)
and hands it to every privileged step of the host stages; it is not echoed, logged or
written anywhere. With passwordless sudo nothing is asked. Run `apply` from a
terminal: without one it stops before any change with `sudo-password-needs-terminal`.
The host stages then print nothing to the terminal until they finish; `apply` prints
one line naming the log, so follow it in a second terminal with
`tail -f .workstation/foundation.log`. When they finish, `apply` refreshes sudo's
cached credential for your terminal, so setup-dev-linux-wsl, which runs next,
normally does not ask for the password again.

setup-dev-linux-wsl records its command-line profile choice on its first run and
refuses a different list afterwards, so choose it now. For the command-line set this
repository used to install, give that list:

```bash
./bootstrap apply --config config/your-machine.local.json \
  --cli-profiles core,dev,security,kubernetes,backup,runtime-docker,ai-agents,cloud,cloud-aws,cloud-azure,cloud-gcp
```

Add `,gpu-nvidia` when you selected the `gpu` host profile. Add `--allow-ssh` if you
reach this machine over SSH: the firewall closes incoming SSH otherwise. Over SSH,
`apply` refuses before any change until you pass `--allow-ssh` or `--no-allow-ssh`
(which warns that new logins will be refused). `--allow-ssh` opens port 22 only (UFW's
`OpenSSH` profile) and needs `openssh-server` installed. Both choices, the host
profiles and `--allow-ssh`, are recorded in
`${XDG_STATE_HOME:-$HOME/.local/state}/setup-dev-linux/state.json` and kept by later
runs.

What happens, in order:

1. The host stages: the distribution checks, the signed third-party APT sources,
   the manifest's packages and snaps, each pinned release binary after its SHA-256 is
   verified, the VS Code extensions (with `dev-gui`), the GNOME settings (with
   `desktop`), then the firewall: UFW enabled with incoming denied, and OpenSnitch
   running in allow mode, which you switch to deny later.
2. The handoff: `~/workspace/setup-dev-linux-wsl` is cloned (or updated) and its
   `./bootstrap apply --target linux` runs as you, interactively. It asks for your
   git name and email, then installs the command line: CLI tools, runtimes, the
   shell, dotfiles and, with `runtime-docker`, Docker and the `docker` group.

Without `--cli-profiles`, setup-dev-linux-wsl installs its own default without
asking. `apply` prints a `hint:` line with the list above before the host stages and
again just before the handoff, so you can interrupt (Ctrl-C; `apply` exits 130) and
re-run with `--cli-profiles`. Later runs need no `--cli-profiles`; to change a
recorded choice, edit `[data] profiles` in `~/.config/chezmoi/chezmoi.toml` (as the
hint says), not the flag.

Other options: `--linux-ref REF` checks out another branch, tag or commit of
setup-dev-linux-wsl; `--no-handoff` stops after the host. If
`~/workspace/setup-dev-linux-wsl` already exists but is not a clone of
setup-dev-linux-wsl, or has local changes, `apply` stops and leaves it untouched.

Re-running `apply` is safe at any point: the second run changes nothing that is
already correct, and the handoff updates the clone and passes no profile list.

## 5. Log out and back in

Group memberships added during `apply`, such as the `docker` group, take effect only
in a new login session. Log out and back in (or reboot) before using Docker without
`sudo`.

## 6. Verify

```bash
./bootstrap verify --config config/your-machine.local.json
```

Verification reads the installed system and reports drift. It never repairs. It
checks the recorded profiles unless you pass `--profiles`, and ends with
setup-dev-linux-wsl's own `script/verify --target linux` (`cli:verify`;
`--no-handoff` skips it). The UFW check needs `sudo -n`: run `sudo -v` first, or it
is reported as deferred. An `incomplete` result names what has no verification yet;
it is not a pass.

## 7. Finish by hand

These are deliberately not automated:

- **Authenticate** the desktop applications that need it: Bitwarden, Slack,
  Thunderbird. Command-line tools (`gh`, cloud CLIs, agent CLIs), the git signing
  key and SSH keys belong to setup-dev-linux-wsl.
- **OpenSnitch**: once your rules exist, switch the default action to deny in the
  OpenSnitch UI. Later `apply` runs keep your choice, and may then prompt.
- **VPN profiles** and their certificates.
- **Backup destination and schedule** on the new machine.
- **GPU**: confirm the NVIDIA driver loaded (`nvidia-smi`) and, if Secure Boot is on,
  enrol the module signing key. A reboot is required.
- **Your data**: restore it yourself from your own backup.

## What this cannot tell you

The VM acceptance cycle exercises the host and the handoff, but not the GPU stack
(the guest has no NVIDIA hardware) or a rendered desktop session (it runs a server
image). Those are proven only on the physical machine.
