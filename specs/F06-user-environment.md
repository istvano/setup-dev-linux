# F06 — Declared user files and retained shell behavior

## Ownership and inputs

Ansible installs reviewed chezmoi/Zsh/framework artifacts; chezmoi exclusively owns
its declared user files. Run as the explicit target user after live storage checks.
Do not change the login shell. No installer hook may rewrite shell files or install
packages, and no chezmoi hook may invoke bootstrap recursively.

Extend the strict machine schema with an optional reference to private user settings
only when its loader and redaction tests are implemented. Identity names, addresses,
work-directory matches and proxy endpoints never become committed defaults. Missing
identity settings make selected identity behavior incomplete; they do not prevent
unrelated approved package work. Credentials and browser data restoration remain manual.

## File conflict contract

Use a committed, finite manifest of destinations and owners. Never manage a whole
home directory, browser data tree or arbitrary directory recursively. Before a
replacement, preserve existing contents privately (directories 0700, files 0600),
with a deterministic restoration manifest. Reject symlinks that escape the declared
destination policy. Failure to back up prevents the replacement.

For existing .zshrc/.gitconfig, preserve unrelated content through a single declared
include block. A repeat apply must not duplicate the block. Existing conflicting
managed markers or destination ownership fail visibly. Chezmoi performs the file
render/apply operation; Ansible does not independently template the same files.
Verification compares owned content and effective settings without applying chezmoi.

## Shell behavior

Load the Oh My Zsh git plugin once, zsh-autosuggestions once and
zsh-syntax-highlighting last. Preserve unrelated customizations. Initialization must
not emit network requests, update managers automatically or conceal missing selected
tools. F07 adds SDKMAN/NVM initialization through this same owner and tests final PATH.

Proxy helpers read private local settings, validate them without eval or executing
shell source, and never print their values. `proxyon` snapshots original presence,
values and export attributes of supported proxy variables on the first activation;
repeated activation does not replace that snapshot. `proxyoff` restores the snapshot,
including previously unset variables, and is harmless when already inactive.
Missing/invalid settings fail without partially changing the environment. An invalid
refresh while active preserves the currently active environment and original snapshot.

## Git and browser behavior

Personal/work Git identities use explicit private includeIf paths. Disposable
repositories prove the effective identity in each scope; no global identity guess.
Git LFS filters are enabled only when their separate behavior capability is selected.
A local synthetic LFS checkout must contain the payload rather than only a pointer.

Browser launchers use declared separate data roots for personal/work contexts, with
loopback-only test content and no existing profile import. Exercise actual Firefox
and Chrome processes in the guest after their delivery is approved. A launcher file
alone does not prove browser isolation. Missing browser delivery keeps that behavior
unassessed. Never place browser credentials or whole profiles in chezmoi.

## Tasks and acceptance

- F06-T1: review/lock chezmoi, Zsh, Oh My Zsh and plugin sources and dependencies.
- F06-T2: define strict private settings schema, redaction and source-file permissions.
- F06-T3: implement finite ownership manifest, private backup and include-block conflict handling.
- F06-T4: implement shell templates and proxy on/off state behavior; validate Zsh parsing.
- F06-T5: implement private Git scopes and selected LFS filters with effective readback.
- F06-T6: implement browser launchers and effective profile separation after browser delivery.
- F06-T7: test fresh/existing/conflicting files, repeat apply, backup failure, symlink
  rejection, unset/empty/exported proxy values, repeated transitions, malformed or
  absent private settings, secret-free reports and deliberate managed-file drift.
- F06-T8: guest session tests, LFS payload checkout, browser separation and manual
  restoration of a replaced fixture file; report deferred prerequisites independently.

This specification defines work to implement. No F06 delivery or acceptance is
claimed by the existing package/controller tests.

## Pinned user-tool delivery contract

Install chezmoi and the Oh My Zsh tree under versioned directories in
`~/.local/share/linux-os-setup/tools/ID/VERSION`, without replacing existing tool
aliases or running vendor installers. A committed manifest binds each payload file
or symlink to the reviewed artifact. Ansible invokes the internal delivery worker
as the target user; the worker rechecks live storage before writes. Download into
private staging, verify SHA-256, safely extract and validate the tree before atomic
directory placement. Existing mismatched trees fail without automatic replacement.
Independent verification reads the committed manifest directly and needs neither
cached downloads nor a controller. Shell caches must live outside pinned trees.
