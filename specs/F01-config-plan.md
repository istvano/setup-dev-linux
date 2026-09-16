# F01 — Strict configuration, pure plan and reports

## Behavior

`./bootstrap plan --config PATH [--format text|json]` runs with distribution Python
and its standard library only. It validates the exact committed JSON schemas and
shared semantic rules, resolves the selection relative to its configuration and
prints declared changes and delivery blockers. Example inputs may be previewed,
but the report labels them non-operational. `install` must reject them.

Unknown arguments, duplicate keys (including nested objects), non-finite JSON
numbers, unknown fields/IDs, unsupported schema/release/architecture, bad types,
conflicting selections and impossible layouts fail with exit 2. Booleans are not
integers. Unsupported schema vocabulary fails closed rather than weakening checks.
Private values and parser exception contents never appear in reports.

Every report has a version, command, config/selection hashes, catalogue revision,
aggregate outcome and per-check/per-capability results. Successful planning means
the plan was rendered, not that the host is ready. No subprocess, environment sync,
sudo, network, bytecode, cache, log or managed-home writes occur during pure plan.

## Tasks and acceptance

- F01-T1: standard-library schema validation and strict UTF-8 JSON parsing.
- F01-T2: one semantic validator shared by runtime commands and static QA.
- F01-T3: explicit config CLI, redacted report and deterministic plan.
- F01-T4: negative fixtures for types, duplicate keys, selections, paths and layouts.
- F01-T5: subprocess test under isolated Python (`-I -S -B`) and a read-only tree;
  check unchanged file hashes and no new files. Missing config and invalid CLI emit
  redacted structured failure when JSON is requested. Report source blockers
  separately from plan completion.

Operational reports never echo target username, disk identity, UUID, receipt content
or arbitrary input values. No environment variable supplies a default config.
