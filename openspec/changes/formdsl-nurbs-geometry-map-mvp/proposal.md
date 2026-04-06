## Why

The formdsl vector phases are complete, but NURBS geometry-map rollout is still
pending. Current form assembly behavior does not expose explicit geometry-map
capability diagnostics, so backend support boundaries for `bspline` vs `nurbs`
are not first-class.

We need a single-patch NURBS geometry-map MVP that introduces deterministic
geometry-map capability semantics before deeper rational/multipatch execution
work.

## What Changes

- Add explicit `geometry_map` capability checks for form backends.
- Support `geometry_map=nurbs` on IGA for single-patch workflows.
- Keep DG-SEM geometry-map support at `bspline` and emit deterministic
  `unsupported_geometry_map` diagnostics for `nurbs`.
- Thread effective geometry-map metadata into backend payload results.
- Add regression tests/docs for strict/permissive geometry-map behavior.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: geometry-map-aware backend capabilities.
- `grudge-dgsem-assembly-adapter`: deterministic diagnostics when geometry-map
  requests exceed current support.

## Impact

- Affected code:
  - `src/cutkit/formdsl/capabilities.py`
  - `src/cutkit/formdsl/iga_backend.py`
  - `src/cutkit/formdsl/dgsem_backend.py`
  - regression tests under `tests/formdsl/`
  - support docs under `docs/`
- This phase does not add multipatch interfaces or full rational basis
  implementation internals.
