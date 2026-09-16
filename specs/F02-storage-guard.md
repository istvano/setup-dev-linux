# F02 — Live platform, target user and storage guard


> **Withdrawn 2026-09-16.** Every requirement in this document concerning
> transferred disks, handoff receipts, witnesses and machine binding is
> withdrawn. Files move by copy; see [F14](F14-file-migration.md). What
> remains in force is the standard single-disk and split-layout preflight.

## Behavior

`./bootstrap preflight --config PATH [--format text|json]` checks a non-example input
without changing state. Ubuntu 26.04 amd64 and an existing non-root target user are
required. Never run install as root or redirect HOME to impersonate the target.

Use machine-readable lsblk/findmnt output. Match private /dev/disk/by-id paths to
whole disks; require configured capacity, distinct split roles and unambiguous
filesystem UUIDs. Each required path must be an exact live mount of the configured
filesystem on the correct physical disk, not a bind-mounted subdirectory or a parent
mount fallback. /var/lib must resolve to root when not separately selected. Reject
unexpected intermediate mounts and read-only filesystems for managed destinations.

The guard precedes all APT, logs, cache, controller or managed-home writes. A failure
is exit 1, missing inspection prerequisite/unsupported input exit 2. Checks must not
escalate read privileges. Transfer mode remains explicitly blocked until the
fresh-target handoff producer and verifier below have fixture and guest evidence.
Accepting a UUID or done marker is forbidden. Standard layouts do not require
transfer evidence.

## Fresh-target transfer handoff contract (F02-T6)

This is a separate offline/maintenance operation, performed after the new Ubuntu
installation and before enabling transferred mounts for normal boot. It never runs
inside post-install apply and never modifies, formats or partitions the transferred
disk. The operator first retains an independent backup of the old data and the
fresh target's own `/var/lib` source. A comparison producer reads that fresh source
and the prepared destination with writers stopped, verifies the intended package
baseline and a complete content/ownership/mode/ACL/xattr comparison, then writes
private, versioned evidence only after an exact match. Selected application data
restored through per-service procedures is recorded separately; old dpkg/apt/systemd
state must not overwrite the fresh baseline.

Evidence binds to the fresh target's root filesystem UUID, a hash of its machine
identity, Ubuntu release/architecture, the configured system/data whole-disk
identities, `/home` and optional `/var/lib` filesystem UUIDs, intended roles,
baseline package-state digest, comparison manifest digest, producer version, time,
and source/destination paths. The producer retains an independent fresh-source
witness on the system disk; the private receipt alone is insufficient. It refuses
unreadable metadata, changing trees, mismatched filesystems or package state, and
must not leave a success receipt after failure. A guest test must use synthetic
disks and an actual maintenance-to-boot transition; inventory injection alone
cannot enable transferred installation.

Before every APT prerequisite, controller/log or managed-home write, the live
guard reads receipt and witness without privilege escalation, checks their integrity
and target bindings, rechecks disk/mount identities, and confirms current OS/package
database consistency. On first apply, the current package baseline matches the
handoff baseline. After legitimate package changes, an explicit apply-owned
checkpoint ties the changed package state to the same witness; an unrecorded
baseline mismatch fails. Verification never creates or repairs evidence. Missing
witness, changed root/machine identity, old `/var/lib` or unrecorded package changes
fail before any managed write.

Transferred `/home` without a separate `/var/lib` still needs fresh-target identity,
prepared-home account/ownership comparison and current mount evidence, but no
`/var/lib` package checkpoint. Retained unrelated home data is not required to
match an empty fresh home. Standard layouts never read transfer receipts.

### Tasks and acceptance cases

The current T6a evidence parser uses two bounded JSON documents. The private receipt has
`schema_version`, `producer_version`, `created_utc`, `target` (Ubuntu release,
architecture, root UUID and machine-ID hash), `disk_ids` (configured system/data
stable IDs), `mount_uuids` (`/home` and nullable `/var/lib`), `comparison`
(comparison-report digest and nullable fresh package-status digest), and
`witness_sha256`. The system-disk witness has the same target, roles, mounts and
comparison fields plus `home_source_path`, `home_prepared_path` and nullable
`var_lib_source_path`/`var_lib_prepared_path`. Schema/producer version 2 replaces
the fixture-only version 1 before any production evidence existed; version 1 is
rejected because it did not prove the transferred home baseline.
The receipt binds the exact witness bytes. The parser accepts only exact fields,
64-character lowercase SHA-256 values, an unambiguous UTC timestamp and the
selected transfer mount roles. It rejects symlinked/oversized/publicly writable
evidence and never prints its private contents. It checks config-to-evidence
binding and document agreement but does **not** authorize transfer apply: target
machine identity, offline tree comparison, current package state and live witness
location need T6b/T6c and real guest T6d acceptance.

- F02-T6a: bounded private evidence schema and read-only validation; reject
  duplicate/unknown fields, symlinks, oversized input, target mismatches, changed
  package baseline and missing system-disk witness.
- F02-T6b: offline comparison producer and retained fresh-source witness. Test
  exact clean destination, stale old dpkg state, divergent content/ownership/ACL/xattr
  and interruption before receipt placement.
- F02-T6c: receipt/witness/current-package checks in the initial guard and an
  explicit post-apply package checkpoint. Test first apply, legitimate package
  changes, unrecorded drift and read-only verify.
- F02-T6d: standard single/split and transferred split layouts on disposable
  Ubuntu disks through maintenance preparation, boot, repeat apply and negative
  old-state/missing-mount cases. Transfer retains its incomplete outcome until then.

T6a's strict parser and host/guest fixtures passed on 2026-09-15. It is an internal
read-only evidence-format API, not a working transfer preflight input or handoff
verifier. T6b's comparison/publication cores, live-path adapter and maintenance
command boundaries have host and guest fixtures, but the command has not run in
an actual rescue target with transferred disks. Home-baseline/home-only comparison,
initial live verification and checkpoint parsing have fixtures; checkpoint
publication, guard integration and T6d boot guest tests remain unfinished;
the live storage guard continues to return incomplete for transfer mode.

T6b starts with a read-only comparison core. It walks source and destination
without following directory symlinks, rejects identical/nested roots and special
files, and builds a deterministic manifest for every relative path. For regular
files it hashes bytes and records mode, uid/gid, size, mtime, xattrs and hardlink
relationships; directories and symlinks record their corresponding metadata,
and symlinks retain their exact link targets. POSIX ACLs are captured as xattrs,
not omitted when a separate `getfacl` executable is unavailable. Each file and
directory is rechecked after inspection for size/mtime/inode/metadata changes;
a second source and destination walk must yield the same manifest before the
comparison can report an exact match. Divergent trees, unreadable metadata,
writer races, root/parent symlink escapes and unsupported special files fail without emitting
success evidence. The core neither writes receipts nor enters live preflight;
the publication core below supplies package-baseline/evidence serialization,
while privileged maintenance discovery remains subsequent T6b work.

Every transferred layout also uses a home-baseline comparator. It requires each
entry from the fresh target user's home to exist in the prepared target home
with identical file bytes, symlink targets, uid/gid, mode, xattrs/ACLs and
hardlink relationships. It compares directory uid/gid, mode and xattrs but
ignores directory mtimes because restored extra children change them. Extra
prepared-home entries are intentionally allowed, scanned for unsupported files
and stability, and never included as private evidence. Both complete trees are
still scanned twice. Missing/changed baseline entries, baseline files hardlinked
to restored extras, metadata drift or writer races fail.

The next T6b slice is a publication core for transferred `/home` and optional
separate `/var/lib`. It accepts a target identity only from the maintenance adapter below,
requires that identity to match the selected Ubuntu release, architecture and
root UUID, and hashes the fresh source's regular, non-symlinked `dpkg/status`
file before and after all selected comparisons. It requires both reads to agree,
combines the home and optional `/var/lib` report digests, and serializes
canonical JSON without private tree contents. Output parent directories must
already exist without symlinked path components, and neither output may exist.

Publication stages and fsyncs both files in their destination directories,
places the system-owned witness first, and places the target-user-owned mode
`0600` receipt last. Failure before the final receipt placement cleans staged files
and can leave at most an independent witness; it cannot leave a success receipt.
The core does not discover the target, map paths to physical disks, create output
directories, stop writers, map the resolved receipt path to a disk, or enter live
preflight. The privileged maintenance command below supplies those guarantees.
Home-only transfer has a different account and
ownership comparison and also remains later T6b work.

The read-only T6b comparison core passed host fixtures and a disposable Ubuntu
guest's actual POSIX ACL divergence case on 2026-09-15. The publication core
passed host fixtures and emitted a parseable receipt/witness pair over that real
ACL guest fixture on 2026-09-16. Neither core identifies the selected physical
mounts, discovers target identity, proves stopped writers or enters the live
transfer guard.

Publication-core acceptance requires an exact copied `/var/lib` tree with a
regular `dpkg/status`, matching target bindings, privately owned output and an
independently parseable witness/receipt pair. Divergent trees, a symlinked or
changing package status, target mismatch, pre-existing output, symlinked output
parents and an injected interruption before receipt placement must fail without
creating a receipt. These fixtures do not prove disk placement or authorize
transfer apply.

The following maintenance-adapter slice is read-only. For every transfer route
it first requires the ordinary live storage checks to pass up
to the deliberately deferred handoff result. It fixes the prepared path at
`/var/lib` and the system witness at
`/etc/linux-os-setup/transfer-witness.json`. Each retained fresh source and
the witness must resolve through the root mount; the configured receipt must be
inside the selected target user's home and resolve through `/home`; and the
prepared home must be that user's current home. When selected, the prepared
`/var/lib` path must resolve through its selected mount. Exact UUID,
physical-disk role, writable mount and unexpected-nested-mount checks remain
the ordinary storage guard's responsibility. The adapter reads a bounded,
root-owned, regular `/etc/machine-id` without following symlinks and converts
the observed live `x86_64` platform spelling to the evidence `amd64` spelling.

Adapter fixtures must reject a source on transferred storage, a receipt outside
the target home, a witness outside the fixed system location, a missing or
wrong `/var/lib` mount, failed base storage checks and malformed/symlinked
machine identity. Passing this adapter alone cannot publish; the command below
adds rescue/emergency quiescence, scoped privilege and secure output-directory
handling before it may call the publication core.

The privileged command slice runs only as UID 0 on the installed target and
accepts explicit `--config`, `--fresh-home` and conditionally required
`--fresh-var-lib` paths. It requires PID 1 to be
systemd, exactly one rescue/emergency target to be active or activating in the
isolation transaction, and graphical and multi-user targets to be inactive. The configured receipt parent must already
be target-user-owned and mode-private. The fixed witness directory is created
under an already verified `/etc` only after all read-only binding/quiescence
checks, or an existing root-owned non-writable directory is reused. The command
then calls the publication core as the only evidence writer and emits only a
redacted outcome. It never stops services, mounts, copies, formats or partitions
anything. Fixtures must reject ordinary multi-user state, non-root invocation,
unsafe output parents and any example/non-operational configuration.

This command is not an apply path and its success still does not enable transfer
preflight. T6c live evidence/package verification and T6d's actual synthetic-disk
maintenance-to-boot acceptance remain mandatory first.

T6c begins with an internal first-apply verifier. It independently reopens the
configured target-user-owned receipt and fixed root-owned witness through the
bounded T6a parser, reruns the ordinary storage/path bindings against current
inventory, hashes the current canonical machine ID and requires the active
regular `/var/lib/dpkg/status` to equal the recorded fresh baseline. The witness
must record `/var/lib` as its prepared destination. A changed machine identity,
receipt/witness byte mismatch, missing/unsafe evidence, mount binding failure,
changed package state or another prepared destination fails with a redacted code.

This initial verifier remains an internal API until its post-package checkpoint
companion and T6d pass. It has no repair or write behavior and is not called by
`bootstrap`; fixture success therefore cannot change transfer preflight's
incomplete outcome.

The T6c checkpoint parser uses a separate fixed root-owned private file at
`/etc/linux-os-setup/transfer-package-checkpoint.json`. Its exact fields are
`schema_version`, `checkpoint_version`, `created_utc`, `witness_sha256`,
`root_uuid`, `machine_id_sha256` and `package_status_sha256`. A checkpoint is
valid only when it binds the receipt's exact witness/root/machine values, is not
older than the handoff evidence and matches the current stable package-status
digest. Missing checkpoint means first-apply rules and requires the original
baseline; malformed, changed, public, symlinked or stale checkpoint fails.
Parsing and validation are read-only. Apply-owned atomic checkpoint publication,
interruption behavior and bootstrap integration remain later T6c work.

Checkpoint publication is an internal, root-owned operation after an authorized
apply. It builds the strict checkpoint from the original receipt and current
stable package digest. First publication requires the fixed path to be absent;
updates require the caller's SHA-256 of the exact previously verified checkpoint
bytes. It stages and fsyncs a mode-`0600` file in the fixed root-owned directory.
For update it hardlinks a private rollback name, atomically replaces the final
file, fsyncs the directory and removes the rollback link; a commit failure
restores the prior checkpoint. Missing/unexpected/concurrently changed state
fails. The writer is not a public command and cannot bless drift by itself;
bootstrap orchestration must pass authorization from a successful pre-apply
verification and remains unfinished.

## Tasks and acceptance

- F02-T1: injectable read-only system inventory adapter with bounded subprocesses.
- F02-T2: deterministic identity/mount/capacity validator.
- F02-T3: integration with preflight/install gates and redacted error codes.
- F02-T4: fixtures for reordered/duplicate disks, wrong role/UUID, subdirectory bind,
  read-only/missing mounts, intermediate mounts and transferred state.
- F02-T5: real guest positive preflight and intentionally wrong UUID negative test.
- F02-T6: producer, verifier, apply checkpoint and real transferred-disk guest
  acceptance above remain unfinished. Return incomplete until all parts pass.

Fixture inventory injection is an internal test API, never a CLI bypass for live apply.
