## Why

Formdsl now parses deterministic multipatch descriptors and IGA lowering records
interface metadata, but assembly still does not add numerical interface
coupling contributions. This leaves a semantic gap: multipatch descriptors are
observable, but they do not yet affect operators.

We need a focused phase that adds deterministic numerical interface coupling
contributions for backend `iga`, while preserving current behavior for forms
without multipatch metadata.

## What Changes

- Add deterministic IGA interface coupling assembly terms driven by multipatch
  interface descriptors.
- Honor interface orientation when mapping plus/minus interface quadrature
  points.
- Add deterministic validation for incompatible paired interface segments (for
  example mismatched segment counts or lengths).
- Add regression coverage validating operator deltas and orientation-dependent
  behavior.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: multipatch interface support expands from lowering
  metadata-only to deterministic numerical coupling contributions.

### Unchanged Capabilities

- `ufl-dgsem-form-dsl`: remains unsupported for multipatch interface execution
  and continues deterministic diagnostics.

## Impact

- Affected code:
  - `src/cutkit/formdsl/iga_backend.py`
  - `src/cutkit/formdsl/capabilities.py`
  - regression tests under `tests/formdsl/`
  - support docs under `docs/`
- This phase does not add DG-SEM multipatch execution.
