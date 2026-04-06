## Why

Formdsl now exposes explicit `geometry_map` capability semantics and accepts
single-patch `geometry_map=nurbs` on the IGA backend, but lowering still relies
on the existing non-rational execution internals. That leaves a semantics gap
between accepted metadata and execution behavior.

We need a focused single-patch NURBS phase that adds deterministic rational
basis execution internals for IGA while preserving current B-spline behavior.

## What Changes

- Add an explicit rational execution path for `geometry_map=nurbs` in IGA
  lowering/assembly internals.
- Thread deterministic rational-basis metadata through IGA payloads for testable
  behavior.
- Keep scalar `geometry_map=bspline` execution behavior stable.
- Add regression coverage for strict/permissive semantics around rational
  execution prerequisites and metadata.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: single-patch NURBS support expands from metadata-only
  acceptance to deterministic rational execution internals.

## Impact

- Affected code:
  - `src/cutkit/formdsl/iga_backend.py`
  - `src/cutkit/formdsl/capabilities.py`
  - IGA assembly internals under `src/cutkit/`
  - regression tests under `tests/formdsl/`
  - support docs under `docs/`
- This phase does not add DG-SEM NURBS execution support or multipatch
  interface semantics.
