# F04 — Locked controller and guarded Ansible foundation

## Behavior

After the shared live storage guard passes, `bootstrap install` may establish a
repository-local controller as the invoking target user. It never executes a remote
installer script. A committed bootstrap lock fixes the uv Linux archive URL/hash;
verify bytes before extracting only the declared executable into private local state.
Distribution Python remains the Ansible managed-host interpreter. The controller
uses a separate pinned environment; no mutation of distribution Python or global pip.

Exact Python dependencies and their transitive graph are in pyproject.toml/uv.lock.
Sync frozen inputs only after preflight; require the expected interpreter version.
Ansible owns system sequencing and privilege. Selected delivery which remains
unverified cannot enter package tasks and must prevent whole-target success.

The first playbook slice verifies platform/interpreter and executes no application
roles. It must honestly return incomplete for the full target. Repeated foundation
apply must not replace unrelated user files. Read-only plan/preflight/verify never
bootstrap or sync this environment. No self-invocation of bootstrap from Ansible.

## Tasks and acceptance

- F04-T1: resolve/hash controller dependencies and review bootstrap artifact/licence.
- F04-T2: guarded per-target-user controller acquisition with digest-failure fixture.
- F04-T3: Ansible platform/interpreter assertions and scope-limited foundation run.
- F04-T4: guest apply twice; prove distribution apt bindings remain separate and
  read-only verification does not recreate a removed controller.
- F04-T5: role/source registry and per-capability readiness aggregation, added with
  F05; no successful skips for missing roles or unverified selected delivery.

Do not collapse foundation success into a full workstation-ready result. Subsequent
roles require their own source review and positive/negative verification.
