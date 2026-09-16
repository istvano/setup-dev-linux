# Target machine record

Hardware and account facts for the machine this repository is first being
installed on. This is a record of one machine, not a requirement for any other:
nothing here is a default, and no other installation needs a matching CPU, GPU,
disk capacity or device name.

## Hardware

| | |
|---|---|
| CPU | Intel i7-13700 |
| Memory | 128 GB |
| GPU | NVIDIA RTX 4090, external enclosure |
| OS | Ubuntu 26.04 LTS amd64, GNOME |
| Disk encryption | Not selected |
| Dual boot | Not selected |

## Storage

Split system/data layout: EFI, `/boot` and `/` on the system disk, `/home` on
the data disk. `/var/lib` stays on root.

Disk roles are resolved from verified stable identities supplied in private
configuration, and mounts from filesystem UUIDs. Device enumeration names are
not portable and are never used to select a role.

## How data gets here

By copy, over SSH, from the old machine — see
[NEW-MACHINE.md](../NEW-MACHINE.md). The automated physical-disk transfer design
was withdrawn on 2026-09-16 (D017), so there is no drive handoff, no receipt and
no preserved source partition layout to account for.

## What stays manual

Credentials, VPN profiles, backup destination and schedule, GPU verification
after first boot, and application sign-in. The checklist is in
[NEW-MACHINE.md](../NEW-MACHINE.md).
