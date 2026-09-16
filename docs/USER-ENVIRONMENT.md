# User environment configuration

The first F06 slice manages shell integration, private Git identity scopes and Git
LFS filters when their individual capabilities and delivery prerequisites are selected.
NVM initialization, Node default selection and a stable pnpm path are implemented.
SDKMAN initialization is implemented. Browser separation remains unfinished. The source contract
is [F06](../specs/F06-user-environment.md); guest results are in [TESTING.md](TESTING.md).

Ansible delivers Zsh and its two external plugins from the approved Ubuntu channel.
Pinned chezmoi and Oh My Zsh payloads live in versioned directories below
`~/.local/share/linux-os-setup/tools`. Their complete manifests are in
[the user-tool lock](../locks/user-tools.json). Payload drift fails without replacement.
Chezmoi writes only the generated finite set of user files. Existing .zshrc and
.gitconfig content is retained around one marked include. Replacements have private
backups under `~/.local/state/linux-os-setup/user-files/backup-*`, with original bytes,
modes and a restoration manifest. Restoring a backup is a manual file operation;
it is not package rollback. Never commit backup files or private settings.

## Private Git identities

Optionally add `"user_settings_file": "user-settings.local.json"` to the explicit
machine configuration. The path resolves relative to that machine file. The settings
file must be owned by the invoking user, with no group/other access (for example,
mode 0600). It uses the committed [schema](../config/user-settings.schema.json):

```json
{
  "schema_version": 1,
  "identities": [
    {
      "scope": "personal",
      "directory": "/absolute/path/to/personal/projects",
      "name": "Your personal Git name",
      "email": "your-personal-address@example.invalid"
    },
    {
      "scope": "work",
      "directory": "/absolute/path/to/work/projects",
      "name": "Your work Git name",
      "email": "your-work-address@example.invalid"
    }
  ]
}
```

Supply actual private values locally. Directories must not overlap or use glob
patterns. Missing identity settings are reported as incomplete; no identity is guessed.
Verification reports contain a settings digest, never the identity values.

## Private proxy settings

`proxyon` reads `~/.config/linux-os-setup/proxy.local.json`, or an explicit
`WORKSTATION_PROXY_SETTINGS` path. This runtime JSON file must be owned by the current
user, have no group/other access and be a regular file rather than a symlink. It
contains exactly four string keys: `http_proxy`, `https_proxy`, `all_proxy`, `no_proxy`.
Nonempty proxy URLs use http, https, socks5 or socks5h. Empty strings explicitly clear
that proxy during activation. Control characters and duplicate/unknown keys fail.
The helpers export both lowercase and uppercase forms and never evaluate shell code.

The first `proxyon` saves prior values, unset state and export attributes. Repeated
activation retains that original snapshot. `proxyoff` restores it; repeated deactivation
is harmless. Missing/invalid settings leave the environment unchanged. Do not put
proxy credentials in the repository or copy old secret-bearing shell function bodies.

## Guest acceptance

```bash
./script/test-vm --controller --packages --user-environment
```

This uses synthetic identities, repositories and loopback proxy values in the dedicated
guest. It does not read existing projects, authenticate to services or restore credentials.
The test exercises plugin initialization, proxy transitions, Git scope readback, actual
LFS payload filtering, unrelated-file preservation, repeat apply, drift and explicit repair.

## Node and pnpm

NVM 0.40.7 manages the reviewed Node 26.8.2 runtime in
`~/.local/share/linux-os-setup/nvm`. The exact archive and extracted payload are
recorded in [the Node lock](../locks/node.json). Installation seeds a verified cache
and invokes NVM in offline binary-only mode. Chezmoi initializes NVM and selects its
default only when Node is selected. Existing project `.nvmrc` files remain untouched.

pnpm 12.4.1 has its own versioned executable directory on the managed shell PATH,
independent of the selected Node version. The guest tests local dependency install,
frozen lockfiles, tests and builds without registry credentials. Node runtime file
drift fails without replacement; an explicitly reapplied changed default alias is
privately backed up before restoration. No real-project compatibility is claimed.

## SDKMAN and Java

The managed SDKMAN directory is `~/.local/share/linux-os-setup/sdkman`; the original
`~/.sdkman` remains untouched. Ansible owns reviewed manager code and bootstrap
policy/metadata; chezmoi owns the shell include. Automatic self-update, auto-env and
health checks are disabled. Other SDK commands are not promised to be offline.

Java delivery registers the four reviewed archives through SDKMAN's inspected local
registration function, with these candidate IDs:

| Variant | SDKMAN candidate |
|---|---|
| Temurin 25 default | `25.0.4.1.1-ws-tem` |
| Temurin 21 | `21.0.12.1.1-ws-tem` |
| Microsoft 25 | `25.0.4.1.1-ws-ms` |
| Microsoft 21 | `21.0.12.1.1-ws-ms` |

Use `sdk use java CANDIDATE` for an explicit shell selection. Native `sdk current`
reports the global default; inspect `JAVA_HOME` and `java -version` for the active
shell. Explicit reapply restores the selected Temurin 25 global default and privately
backs up a changed default link under `~/.local/state/linux-os-setup/java-default-backups`.
Modified runtime payloads or candidate registrations fail without replacement.
Maven/Gradle/Kotlin delivery is implemented; Mandrel native-build acceptance and full
workstation acceptance remain unfinished.

Maven `3.9.16-ws`, Gradle `9.7.1-ws` and Kotlin `2.4.20-ws` are registered as their
own SDKMAN candidates/defaults. Their executable paths remain available across Java
selection. They do not rewrite existing Maven/Gradle settings or project wrappers.
The role requires selected SDKMAN and Java and independently verifies their prerequisites,
payloads, registrations and defaults. See [build-tool review](JVM-TOOLS-REVIEW.md).

Mandrel is an additional Java candidate, `25.0.4.1-ws-mandrel`, for explicit project
selection. It requires reviewed native development packages; it does not replace the
Temurin 25 default. See [Mandrel review](MANDREL-REVIEW.md) and actual testing evidence.
