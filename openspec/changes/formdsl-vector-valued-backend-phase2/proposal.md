## Why

The vector-valued `value_shape` MVP is now landed and archived. It provides
shape-aware parsing, backend capability diagnostics, and DG-SEM payload shape
threading, but backend execution semantics are still largely scalar-equivalent.

To make vector forms practically useful, we need a second phase that defines and
implements deterministic backend behavior for vector components beyond metadata
propagation.

## What Changes

- Extend DG-SEM lowering to include deterministic component-aware operator plans
  for rank-1 vector forms.
- Define and implement vector source handling conventions (for example,
  component-wise source signatures and deterministic lowering order).
- Harden parser and capability shape consistency checks for vector form payloads
  and UFL-like inputs.
- Add backend behavior tests and parity-style checks for vector form lowering.
- Update docs/support matrix with explicit vector execution semantics and current
  limitations.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: stricter vector-form shape consistency checks.
- `grudge-dgsem-assembly-adapter`: component-aware vector lowering semantics for
  rank-1 forms.

## Impact

- Affected code:
  - `src/cutkit/formdsl/adapter.py`
  - `src/cutkit/formdsl/capabilities.py`
  - `src/cutkit/formdsl/dgsem_backend.py`
  - regression tests under `tests/formdsl/`
  - support docs under `docs/`
- This phase intentionally does **not** add tensor-rank execution or NURBS/
  multipatch implementation.
