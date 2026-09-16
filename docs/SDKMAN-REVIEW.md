# SDKMAN source-pair review

Reviewed 2026-09-14. The SDKMAN manager now has Ansible delivery, independent verification and guest
role evidence. The Java role has separate evidence in JAVA-REVIEW.md; other JVM tools
retain their delivery gates.

The [CLI 5.23.0 release](https://github.com/sdkman/sdkman-cli/releases/tag/5.23.0)
and [native 0.7.35 release](https://github.com/sdkman/sdkman-cli-native/releases/tag/v0.7.35)
provide the selected Linux x64 ZIP inputs. Their download SHA-256 values match the
publisher release metadata. Exact URLs, hashes, Apache-2.0 licence-document hashes
and complete extracted file manifests are in [sdkman-review.json](../locks/sdkman-review.json).
The CLI/native licence documents are from their respective exact release tags.

The inspected floating installer named native 0.7.34. It was read only; it is not an
installation input and was never executed. The newer native release was tested with
the current CLI before any production approval. ZIP extraction rejects unsafe paths,
duplicate normalized names, links and special files, and preserves executable status
without privileged permission bits. Payload verification includes every regular file.

## Source findings and implementation constraints

- Initialization loads modules using `find -type f`. Symlinking the entire source
  directory or individual module files does not satisfy that loader. The implemented role
  delivers verified regular module files and independently verifies them.
- The CLI has no supported offline-mode setting in this release. Disabling health
  checks does not make arbitrary commands offline. Do not advertise an offline
  manager or invent an `sdk offline` command/configuration value.
- Public `sdk install` can validate versions remotely and execute fetched hooks.
  Production registration must avoid that unreviewed chain. The pinned internal
  `__sdkman_install_local_version` function only registers an existing local folder;
  it was inspected and exercised with synthetic local candidates. This is a
  pin-specific internal API dependency, requiring renewed review on manager updates.
- The native `sdk current java` reports the global default, even after `sdk use`
  changes the active shell. Verify `JAVA_HOME` and executable behavior independently.
  Native default links may be absolute; verify their resolved target.
- Disable self-update, automatic environment selection/installation and health-check
  requests in the managed configuration. Chezmoi owns shell initialization. Ansible owns the dedicated manager code and bootstrap policy/metadata; chezmoi
  does not also declare those files. Candidate/temp state is separately mutable.

## Actual guest experiment

`./script/test-vm --sdkman-review` passed on Ubuntu 26.04 with all 119 static/behavioral
tests. The dedicated fixture checks guest identity, actual target user and live
storage preflight before creating its temporary state. It downloads only the reviewed
archives, checks their digests/manifests and runs the CLI/native pair in both Bash and
Zsh. Local registration, global default, shell switching, effective JAVA_HOME,
executable selection and home lookup passed. Candidate and broker endpoints point to
an unavailable loopback address for these checks. Temporary candidates are small
shell scripts, not Java runtimes; no JVM compilation or production-role claim follows.

The subsequent manager role test passed with 127 host/guest behavioral tests, repeat
apply, fresh Zsh version output, verification with the controller absent and deliberate
module drift. Installation refused to overwrite the changed module; restoring the
fixture bytes recovered verification. Managed policy drift and injected extension
fixtures fail read-only unit verification. Existing `~/.sdkman` is preserved; the
managed directory is `~/.local/share/linux-os-setup/sdkman`.

The lock filename retains `review` for continuity, but now backs the approved manager
role. CLI 5.23.0 and native 0.7.35 are acquired through Ansible after storage guards,
then regular files and policy are staged and atomically placed. Neither vendor
bootstrap nor remote candidate hooks run. A changed managed manager/policy fails
without replacement. Normal shell startup does not choose a different project JDK.

Next: complete Java-role guest acceptance and Maven/Gradle/Kotlin/Mandrel delivery.
Temurin 25 remains the required default.

### Dangling-default recovery

The native 0.7.35 `default` implementation checks `Path.exists()`, which misses a
dangling symlink. Creating the new link then fails and triggers a copy fallback;
the guest recovery fixture reproduced this and left temporary copied state. The
wrapper now records a private backup and removes only that dangling managed default
link before invoking SDKMAN. Existing valid links remain SDKMAN-owned operations;
ordinary directories still fail without replacement. Java and JVM-tool unit fixtures
assert backup bytes/permissions exist before native recovery executes.
The reviewed implementation is [native default.rs](https://github.com/sdkman/sdkman-cli-native/blob/v0.7.35/src/bin/default.rs).
