## Why

`dgsem` remains multipatch execution unsupported, but compatibility diagnostics
are currently coarse (`unsupported_multipatch_interface` only). Callers cannot
reliably distinguish descriptor features that block DG-SEM lowering (for
example interface orientation variants or per-interface penalty controls).

We need deterministic diagnostic semantics so DG-SEM users get actionable,
structured feedback while execution remains out of scope.

## What Changes

- Keep DG-SEM multipatch execution unsupported.
- Add deterministic compatibility-profile diagnostics for DG-SEM when
  multipatch descriptors are present.
- Emit structured diagnostics for orientation variants and per-interface penalty
  controls under DG-SEM.
- Add regression tests for strict/permissive behavior and diagnostics payload
  stability.

## Capabilities

### Modified Capabilities

- `ufl-dgsem-form-dsl`: expands diagnostics from one generic unsupported code
  to a deterministic compatibility profile for multipatch descriptors.

### Unchanged Capabilities

- `ufl-iga-form-dsl`: unchanged execution semantics.
- DG-SEM multipatch execution remains unsupported in this phase.

## Impact

- Affected code:
  - `src/cutkit/formdsl/capabilities.py`
  - tests under `tests/formdsl/`
  - support docs under `docs/`
