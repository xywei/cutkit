## Why

CUTKIT already provides deterministic folded quadrature over trimmed domains,
including signed weights induced by folded cells. However, there is no
consumer-facing adapter that converts clipped source regions and source-density
functions into a point-cloud form directly consumable by volumential-style
far-field potential evaluation across dimensions.

For volumetric potential workflows, we need a stable bridge from CUTKIT folded
decomposition outputs to a signed source cloud (`point`, `weight`, `charge`) so
far-field evaluation can be handled as a standard sum of point potentials.

## What Changes

- Add a dimension-independent signed source-cloud export workflow over one or
  many clipped axis-aligned boxes in 2D and 3D.
- Support object-mode and array-mode source-region inputs with deterministic
  broadcasting and flattening semantics.
- Preserve signed folded quadrature semantics (`weight` may be negative).
- Provide deterministic ordering, shape metadata, and per-box status behavior.
- Add adapter helpers for volumential-friendly array/materialization output.
- Add tests and docs for conservation/parity behavior and deterministic output.

## Capabilities

### New Capabilities

- `volumential-signed-source-cloud`: deterministic signed point-source export
  from folded clipped regions in 2D/3D.

### Modified Capabilities

- `cad-box-batch-interface`: extend 2D/3D clipped-box workflows with
  source-cloud export convenience APIs.
- `folded-decomposition-2d` and `folded-decomposition-3d`: expose signed
  quadrature rule outputs through one solver-facing adapter contract.

## Impact

- Affected code:
  - new adapter module(s) under `src/cutkit/` for signed source-cloud export
  - optional facade extensions in `src/cutkit/cad.py`
  - tests under `tests/` for adapter semantics and deterministic behavior
  - README/docs usage notes for volumential integration path
- No mandatory dependency changes expected.
