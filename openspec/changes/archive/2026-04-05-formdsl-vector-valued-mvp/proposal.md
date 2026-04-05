## Why

The archived UFL + IGA + DG-SEM assembly change established a stable scalar
formdsl baseline. Current parser guardrails prevent vector/tensor form spaces,
which blocks incremental rollout of vector-valued workflows and keeps backend
shape capability logic implicit.

We need a minimal vector-valued MVP that preserves deterministic behavior while
starting real shape-aware support in the shared form pipeline.

## What Changes

- Extend `WeakFormIR` with explicit `value_shape` metadata.
- Allow parser ingestion of vector-valued mapping payloads and UFL-like argument
  shapes.
- Add backend capability diagnostics for unsupported value shapes.
- Keep `iga` scalar-only, and allow `dgsem` scalar + rank-1 vector forms.
- Thread `value_shape` through DG-SEM lowering payloads for deterministic
  backend consumption.
- Add tests/docs for vector parsing and capability behavior.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: shape-aware IR parsing with deterministic value-shape
  metadata.
- `grudge-dgsem-assembly-adapter`: initial rank-1 vector value-shape support in
  lowering payloads.

## Impact

- Affected code:
  - `src/cutkit/formdsl/ir.py`
  - `src/cutkit/formdsl/adapter.py`
  - `src/cutkit/formdsl/capabilities.py`
  - `src/cutkit/formdsl/dgsem_backend.py`
  - tests under `tests/formdsl/`
  - support docs under `docs/`
- Behavioral impact:
  - parser no longer globally rejects vector-valued spaces when explicit
    `value_shape` is available,
  - backend capability checks become explicit for shape support boundaries.
