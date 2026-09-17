# Version refresh. Invoked as `just update <recipe>` or `just update::<recipe>`.
# The Makefile spells the same subcommands `make update/<recipe>`.

[doc("Show what a refresh would change; writes nothing")]
report:
  python3 -B script/update-report

[doc("Re-pin everything that can be re-pinned automatically, then check")]
apply:
  python3 -B script/update-report --write
  python3 -B script/check-catalogue
  python3 -B script/check-manifest
  python3 -B -m unittest discover -s tests

[doc("Re-pin the third-party release binaries only")]
binaries:
  python3 -B script/resolve-binaries --write

[doc("Re-record the repository signing-key fingerprints only")]
keys:
  python3 -B script/resolve-repository-keys --write
