# User Python and uv source and delivery review

Reviewed 2026-09-15 for the selected Ubuntu 26.04 LTS amd64 user runtime. The
automation controller has its own repository-local pinned Python/uv environment;
`/usr/bin/python3` is still Ubuntu's bootstrap and managed-host interpreter.

The immutable [lock](../locks/python-user.json) fixes uv 0.12.13's official
Linux x86_64 GNU archive at SHA-256
`745765a3b6e360ad76743599ae5c42e9278c7edf8bbff9fc76d05bf2623a04dd`,
both executable digests and the tagged MIT licence document digest
`860e3d7a86b84e6a7012c7a635fc64df475cebc6cce34dfeb73a5982ec58176c`.
It fixes the `python-build-standalone` CPython 3.14.7 archive from its
2026-09-01 release at SHA-256
`3959f92825141e04adf44982d3a83ee57af0877e893b0796e04c1468749d9b04`.
The archive's CPython licence file hashes to
`b0e25a78cffb43f4d92de8b61ccfa1f1f98ecbc22330b54b5251e7b6ba010231`;
its bundled dependencies and notices have varied terms. The complete installed
interpreter tree, including the bundled notices, has 4,571 locked file/link
entries. The lock is scoped to these exact reviewed releases and amd64 GNU layout.

Ansible runs the worker as the explicit target user after the live storage guard.
It installs the uv payload under a versioned user-tool directory, downloads and
hashes the Python archive, and presents it from a temporary `file://` mirror
to the pinned uv binary with `--offline --no-cache --no-config --no-bin`.
The install permits explicit Python acquisition only during this operation.
The experiment found that uv's default executable-link mode can return success
despite failing to write conventional `~/.local/bin` links; `--no-bin` avoids that
ambiguous behavior. Its installed minor-version alias points at the temporary
directory, so the worker replaces it with a relative alias before placement.

uv writes the installation location into one `_sysconfigdata` file. Two
isolated installations produced identical SHA-256
`e140e2c3c2b5fe3d8c9280b0ed682b7b062483ad4f4704286e4003932b9d188b`
after substituting their prefix with the lock's marker. The worker rewrites only
that generated prefix to the final managed directory before an atomic directory
rename. Read-only verification checks the *final* prefix, the normalized hash,
the alias, all other file contents and executable modes, and the exact file/link
set. The interpreter files and directories are sealed read-only so normal module
imports cannot create bytecode in the source tree. Changed payloads block
installation without repair.

Chezmoi exports the managed interpreter and uv executable directories plus
`UV_PYTHON_INSTALL_DIR` and disables automatic Python downloads. It does not
set `PYTHONPATH`, replace Ubuntu Python, add global packages or modify user
projects. An uv-only selection does not acquire the interpreter; Python selection
requires uv explicitly. Existing conventional user uv/Python locations remain outside the
managed tree. A separate synthetic local-wheel project tests uv's project lock,
venv, dependency, unittest and run workflow without contacting PyPI; it gives
no real-project or native-extension compatibility claim.

Primary documentation: [uv Python command and mirror flags](https://docs.astral.sh/uv/reference/cli/),
[Python download policy](https://docs.astral.sh/uv/concepts/python-versions/),
[standalone distribution licensing](https://github.com/astral-sh/python-build-standalone/blob/main/docs/running.rst).
Guest acceptance and its limits are recorded in [TESTING.md](TESTING.md).
