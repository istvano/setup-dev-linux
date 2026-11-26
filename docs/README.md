# Documents

## Read these

| Document | What it is |
|---|---|
| [NEW-MACHINE.md](NEW-MACHINE.md) | Fresh Ubuntu to a working machine: apply, the handoff, log in again, verify |
| [OPERATIONS.md](OPERATIONS.md) | Commands that work today, the firewall and the handoff, and how to keep versions current |
| [ARCHITECTURE.md](ARCHITECTURE.md) | The two repositories, the stages of a run, configuration, storage guards and the command contract |
| [DECISIONS.md](DECISIONS.md) | Every settled decision and why (D001–D030; D022–D030 make this the host repository) |
| [TESTING.md](TESTING.md) | What must be tested, the VM cycle and its checklist, and the current result |
| [MOVED.md](MOVED.md) | Where each command-line item this repository used to install went |
| [../TASKS.md](../TASKS.md) | What is done, what is not, and what is deliberately excluded |

## Evidence

| Document | What it is |
|---|---|
| [SOURCE-EVIDENCE.md](SOURCE-EVIDENCE.md) | Source, licence and integrity review per tool |
| [evidence-log.md](evidence-log.md) | Every acceptance run in order, with what each found |
| [software-review.md](software-review.md) | The original review. **Hash-verified by `check-catalogue`; do not edit.** |
| [migrations/current.md](migrations/current.md) | The first target machine's hardware, as one example |

## Generated — do not edit by hand

These are outputs. Editing one is undone by the next run, and `check-catalogue`
fails when the matrix no longer matches the catalogue.

| Document | Regenerate with |
|---|---|
| [CAPABILITY-MATRIX.md](CAPABILITY-MATRIX.md) | `python3 -B script/render-matrix --write` |
| [SOURCE-REVIEW.md](SOURCE-REVIEW.md) | `python3 -B script/render-source-review --write` |
| [INVENTORY-REVIEW.md](INVENTORY-REVIEW.md) | `make review` |

## Design

| Document | What it is |
|---|---|
| [TOOL-SELECTION.md](TOOL-SELECTION.md) | Why Ansible, chezmoi, SDKMAN and NVM were chosen (history: the command line moved to setup-dev-linux-wsl, see [MOVED.md](MOVED.md)) |
| [../specs/README.md](../specs/README.md) | Feature contracts and acceptance cases |
