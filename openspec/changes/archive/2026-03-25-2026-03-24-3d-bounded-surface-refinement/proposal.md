## Why

Current 3D coverage in CUTKIT still has practical gaps for broader folded
integration workflows:

1. Cartesian graph-surface integration is one-sided (`surface -> 1`) and cannot
   represent bounded slabs between two trim surfaces.
2. Section 6.1.3 boundary construction disallows `side_resolution > 1`, limiting
   side-face refinement even in conforming cases.
3. CAD-native 3D solid ingestion and clipping are not exposed as reusable core
   adapter utilities for folded-volume workflows.

Closing these gaps improves 3D integration flexibility while keeping the
existing paper-reproduction APIs stable.

## What Changes

- Add bounded Cartesian 3D graph-surface integration APIs that integrate between
  lower and upper trim surfaces for x/y/z axis modes.
- Keep existing one-sided integration APIs unchanged for backward compatibility.
- Allow `build_section_6_1_3_boundary_triangles(..., side_resolution>1)` and add
  regression coverage for seed-invariant signed volume under side refinement.
- Add OpenCascade 3D adapters to ingest solids, clip with axis-aligned boxes,
  and extract oriented boundary triangles for folded-volume reconstruction.
- Update docs that describe remaining 3D follow-ups and current 3D capabilities.

## Capabilities

### Modified Capabilities

- `cartesian-3d-axis-clipping`
- `folded-decomposition-3d`

### New Capabilities

- None.

## Impact

- Affected code:
  - `src/cutkit/quadrature/folded3d.py`
  - `src/cutkit/quadrature/__init__.py`
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py`
  - `tests/quadrature/test_folded3d.py`
  - `tests/evals/test_antolin_examples_3d.py`
  - `README.md`
  - `docs/folded-decomposition-followups.md`
- No breaking API removals; existing one-sided integration entry points remain
  available.
