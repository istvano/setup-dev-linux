# F05 — Source-approved package delivery and independent verification

## Initial slice

Deliver the Ubuntu-channel Git, curl and jq capabilities first. They exercise a
CLI/workflow, HTTP client and JSON tool without adding services or user dotfiles.
All other selections remain unchanged and cannot enter installation until their
delivery is separately approved and their role implemented.

## Behavior

A committed approved-delivery registry maps capability IDs to exact Ubuntu package
names, source-package names, licence evidence and supported release suites. It is
distinct from the historical candidate ledger. Catalogue delivery/licence state
must agree with that registry before a package can enter Ansible tasks.

Ansible owns APT cache refresh and package installation with privilege on those
tasks only. Before install, distribution Python checks candidate source package,
trusted Ubuntu origin, allowed suite, architecture and available SHA-256 metadata.
No candidate from another release/vendor or untrusted index is accepted. APT retains
signature/download integrity enforcement; never allow unauthenticated packages.
Resolve the selected roots together in memory before APT installation. Reject a
broken solution, package removal, or any changed dependency lacking trusted Ubuntu
metadata for an allowed suite, architecture and SHA-256. Distribution dependency
resolution must not silently introduce a third-party source.

Verification is independent and read-only: check installed status/version against
the approved source policy, report missing/unsupported packages as failures and
never run APT repair/update/install. Require fully installed dpkg status; unpacked
or half-configured packages cannot pass from their version metadata alone. Exact historical candidate versions do not
freeze permitted security updates. Installed-version provenance is assessed against
available signed APT metadata; stale/missing metadata is not an automatic pass.

Only explicitly selected approved IDs enter package tasks. Unknown/unverified or
unimplemented selected capabilities remain failed/incomplete in the aggregate report;
they must not be successful skips. The approved-package fixture may complete, while
the full workstation profile remains blocked on its other source/role requirements.

## Tasks and acceptance

- F05-T1: review Git/curl/jq Ubuntu source/licence evidence and create a checked registry.
- F05-T2: implement candidate/installed-state inspection using distribution apt bindings.
- F05-T3: implement privileged APT tasks under the shared guard and independent verify.
- F05-T4: negative fixtures for untrusted/wrong-suite/missing package and unapproved IDs.
- F05-T5: guest first/second apply, synthetic Git/curl/jq workflows, deliberate jq removal,
  verification failure without repair, and successful reapply/verification.
- F05-T6: extend approved delivery and roles to remaining packages, plus separately
  specified AppArmor/UFW/security-update policy and failure recovery cases.

The initial slice does not configure Git identity, credential storage, browser profiles
or global shell files. Those belong to later features and their declared owners.


## CLI extension slice

Extend the same package policy to Git LFS, ripgrep and ShellCheck after reviewing
Ubuntu source-package licence notices. Acceptance uses only a disposable directory:
Git LFS clean/smudge must round-trip a synthetic payload with local repository
configuration; ripgrep must find the expected text and return 1 for missing text;
ShellCheck must accept quoted variables and reject a known unquoted variable.
This does not configure global LFS filters (the separate F06 capability), contact
an LFS server, or install user shell configuration.
## Capability-scoped native prerequisites

F05-T7: add a separate reviewed prerequisite registry for application roles whose
runtime artifacts are not APT-owned. Internal dependency records do not become new
user-selectable capabilities or implicit profile selections. Resolve them only for
an explicitly selected, source-approved capability. Use the same signed Ubuntu suite,
architecture, source-package, combined-transaction and independent installed-state
checks as selected APT roots. Deduplicate shared package requests. Missing/modified
required dependencies fail the owning capability's verification; disabled capabilities
cause no prerequisite installation or probe. Ansible installs system prerequisites
before invoking target-user runtime roles, after the shared storage guard.

First acceptance: Mandrel selects approved C++/zlib/FreeType development dependencies;
unselected Mandrel produces no requests. Reject unknown prerequisite mappings, duplicate
IDs/packages and mappings to unapproved capabilities. Exercise native-image build/run
in the disposable guest and verify dependency failure without automatic repair.
