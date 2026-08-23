# Architecture

## Data flow

```mermaid
flowchart LR
    P[Producer] -->|JSON task card| I[inbox]
    I -->|atomic rename| W[Worker / processing]
    W -->|result| A{Approval required?}
    A -->|no| D[processed]
    A -->|yes| R[awaiting_approval]
    R -->|approve| D
    R -->|reject| F[failed]
    W -->|error| F
    O[Human observer] -. reads .-> I
    O -. reads .-> W
    O -. reads .-> R
```

`TaskBus` owns lane creation, JSON serialization, transitions, digest generation, and watching. State is implied by the directory and repeated in the task card for portability.

## Reliability properties

- Workers claim an inbox card with a same-volume filesystem rename.
- JSON updates use a temporary sibling followed by `os.replace`.
- Invalid transitions fail visibly and preserve the current card.
- IDs are unique across all lanes.
- Events preserve who moved a task and when.

The implementation does not promise network-filesystem locking semantics or distributed exactly-once execution. Use it as a local coordination primitive and make worker operations idempotent.

## Package layout

```text
src/file_task_bus/
  bus.py       lifecycle and persistence
  cli.py       dependency-free CLI
tests/         success and failure fixtures
examples/      reproducible PowerShell demo
```
