# linux-os-setup

Reusable automation for Ubuntu 26.04 LTS amd64 workstations with GNOME.
Automate selected applications and settings; provide a separate manual guide for
data restoration. Hardware, disk roles and optional features come from machine
configuration. The repository does not require a particular CPU, GPU, disk size,
NVMe device name or an existing drive to transfer.

## Storage layouts

| Layout | System disk | Data disk |
|---|---|---|
| Single disk | EFI, separate /boot, / and /home; /var/lib within / | Not required |
| Split system/data | EFI, separate /boot and / | /home; optionally separate /var/lib |

Physical-drive transfer is a separate opt-in, disabled by default. Disk roles are
selected using verified stable identities supplied in private configuration;
“system disk” and “data disk” never mean the first/second enumerated device.
Normal setup does not partition disks or move data. Existing transferred drives
are preserved. No target disk encryption is selected in the current design.

## Implementation documents

- [Capability matrix](docs/CAPABILITY-MATRIX.md): confirmed selections and complete Mac/Linux mapping.
- [Architecture](docs/ARCHITECTURE.md): configuration, storage guards, command and update contracts.
- [Testing specification](docs/TESTING.md): static catalogue checks and future installation acceptance.

- [Implementation plan](docs/IMPLEMENTATION-PLAN.md): milestones, interfaces and acceptance criteria.
- [Tool selection](docs/TOOL-SELECTION.md): Ansible, chezmoi, SDKMAN, NVM and supporting tools.
- [Confirmed decisions](docs/DECISIONS.md): reusable architecture and selected defaults.
- [TASKS.md](TASKS.md): unfinished implementation work.
- [Manual migration guide](docs/manual-migration.md): optional operator-run restoration.

## Current migration example

[Current migration](docs/migrations/current.md) records the first target's hardware,
source-drive observations and transfer procedure. It does not define requirements
for other machines. [Reviewed software selections](docs/software-review.md) remain
unchanged as decision evidence; later confirmed decisions supersede stale entries.

The P0 revision includes a normalized JSON catalogue, explicit default/target selections,
structural schemas and three storage examples under `config/`. Examples contain placeholders
and are not installation inputs. Delivery sources/licences/pins remain explicitly unverified;
see TASKS for remaining evidence. Run `python3 script/check-catalogue` for static validation
(Python 3 and jsonschema required). Static negative tests run with `python3 -B -m unittest discover -s tests`.
Bootstrap, Ansible roles and workstation tests remain
to be implemented. No installer or migration command has
been run. Keep private disk identifiers, inventories, credentials and backups out
of the repository. No commit or push is performed automatically.
