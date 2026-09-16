# F14 — File migration

## Purpose

Move the operator's files from the old workstation to the new one, and prove
the copy arrived complete.

This replaces the withdrawn automated disk-transfer design. There is no
receipt, witness or machine binding: files are copied over SSH, and the proof
is that a second pass finds nothing left to send.

## Contract

- Copies only the trees declared in `manifest/migrate.json`.
- Never deletes on the destination. A tree that already exists is updated.
- Never partitions, formats or mounts anything on either machine.
- Excludes regenerable output — `node_modules`, `.venv`, build directories,
  package caches — and reports what it excluded.
- Credential paths are excluded from the ordinary copy. They move only under
  the explicit `--secrets` command.
- Resumable: an interrupted copy continues where it stopped.
- Completeness is proved, not assumed. After copying, the same rsync runs in
  dry-run mode; any outstanding item fails the command.

## Tasks

- T1 Declare what moves and what does not. **Done** — `manifest/migrate.json`.
- T2 Build and run the copy. **Done** — `script/workstation/migrate.py`.
- T3 Prove completeness. **Done** — second-pass verification.
- T4 Separate credential pass. **Done** — `--secrets`.
- T5 Rehearse against the real home in a VM. **Done** —
  `script/test-manifest-vm`.
- T6 Physical machine-to-machine move. **Unfinished** — awaits the new machine.

## Acceptance

| Case | Expectation |
|---|---|
| Ordinary copy | Credential paths absent on the destination |
| Ordinary copy | `node_modules` and caches absent on the destination |
| Ordinary copy | Real files present on the destination |
| Destination given as `host:/path` | Refused |
| Tree not declared in the manifest | Refused |
| Empty source | Refused rather than reporting success |
| Complete copy | Second pass reports nothing outstanding |
| File missing on the destination | Second pass reports it and the command fails |
| `--dry-run` | Nothing written |
| Interrupted copy | Resumes on the next run |

## Limits

Copying does not make the new machine usable on its own: authentication, VPN
profiles, backup destinations and application sign-in stay manual. See
[NEW-MACHINE.md](../docs/NEW-MACHINE.md).
