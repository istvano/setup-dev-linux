# F03 — Disposable Ubuntu VM and guest tests

## Behavior

`script/vm` owns test VM prepare/start/status/ssh/stop operations. All state is under
ignored private `vm/state` and `vm/disks` directories. No physical disk is passed to
QEMU. Use an official Ubuntu 26.04 amd64 image, verify its signed SHA256SUMS using
the installed Ubuntu cloud-image keyring, then verify image bytes before booting.
Record the dated URL and digest in a public image lock; never use an unchecked
floating download for a subsequent VM run.

Use an immutable base plus a writable qcow2 overlay, dedicated guest SSH key and
pinned known-host file. User-mode networking forwards SSH only to 127.0.0.1; no host
home, Docker socket or production credentials are shared. QEMU uses KVM when present;
report missing acceleration clearly. Existing state is not silently reset or deleted.

The first guest is the official Ubuntu cloud image for foundation tests. Prepare
separate /home on a synthetic second disk; keep /var/lib on root. Cloud-init provisioning
is test-fixture setup, not the production OS installer. Desktop acceptance requires
GNOME installation/session validation later; a server-image boot is not desktop E2E.

## Tasks and acceptance

- F03-T1: pinned signed image acquisition and integrity failure tests.
- F03-T2: private NoCloud seed, synthetic disks, dedicated key, loopback SSH.
- F03-T3: idempotent status/start/stop with owned-process identity checks.
- F03-T4: guest OS/architecture/boot identity and cloud-init completion checks.
- F03-T5: copy a secret-free repository bundle, run static/fixture/runtime tests,
  preserve private logs and return the actual guest exit status.
- F03-T6: add desktop golden image/sealing, disposable clones and full-install,
  reboot/second-apply/drift tests as F04–F11 become available.

Never call partial foundation smoke tests a full workstation installation test.
KVM host access and VM networking may require the execution tool's sandbox approval;
this does not authorize changing physical workstation configuration.

The guest test workspace is an owned directory under `/var/tmp`, not `/tmp`, so
it survives the required reboot. Retry SSH readiness only; a failed acceptance
command after reboot fails the run immediately. Test reports must not hide earlier
failed cases behind automatic retries.
