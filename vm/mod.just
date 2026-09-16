# Disposable Ubuntu test VM. Invoked as `just vm <recipe>` or `just vm::<recipe>`.
# The Makefile spells the same subcommands `make vm/<recipe>`.

[doc("Fetch and verify the Ubuntu image")]
fetch:
  python3 -B script/vm fetch

[doc("Discard the guest and its disks")]
reset:
  python3 -B script/vm reset

[doc("Build a fresh guest from the verified image and boot it")]
up:
  python3 -B script/vm prepare
  python3 -B script/vm start

[doc("Report whether the guest is prepared and running")]
status:
  python3 -B script/vm status

[doc("Stop the guest")]
stop:
  python3 -B script/vm stop

[doc("Run a command in the guest")]
ssh *ARGS:
  python3 -B script/vm ssh {{ARGS}}

[doc("Apply the manifest, rehearse the migration, reboot and repeat")]
accept:
  python3 -B script/test-manifest-vm

[doc("Run the F01-F07 guest suite: storage preflight negatives and runtime fixtures")]
foundation *ARGS:
  python3 -B script/test-vm {{ARGS}}

[doc("Destroy the guest, rebuild it, apply and accept")]
clean-cycle: reset up
  python3 -B script/test-manifest-vm
