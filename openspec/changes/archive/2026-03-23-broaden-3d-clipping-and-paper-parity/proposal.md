## Why

CUTKIT's current 3D clipping/integration path is too narrowly tied to
x-aligned Section 6.1.3-style workflows, Section 6.2 3D non-monotonic rows are
under-instrumented, and antolin-paper parity fixtures are not yet full 2D+3D.

## What Changes

- Add axis-general 3D clipping and Cartesian graph-surface integration APIs for
  x/y/z-aligned classes.
- Add Section 6.2 3D monotonicity diagnostics to expose and track row-level
  non-monotonic behavior.
- Promote antolin-paper fixture coverage to full-scope (`2D+3D`) for
  polygonized and CAD-native fixture tracks (CAD may remain placeholder when
  unavailable).
- Document singular quadrature status relative to the Antolin paper and defer
  QBFEM implementation.

## Capabilities

### New Capabilities
- `cartesian-3d-axis-clipping`: classify and integrate Cartesian 3D cut cells
  for x/y/z-aligned graph surfaces through one consistent API.
- `section6-3d-grid-diagnostics`: report monotonicity diagnostics for Section
  6.2 3D grid-refinement rows.
- `antolin-paper-full-parity-fixtures`: provide full-scope antolin-paper parity
  fixtures and fixture workflow guidance.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/clipping/cartesian3d.py`
  - `src/cutkit/quadrature/folded3d.py`
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py`
  - `scripts/reproduce_antolin_2022_examples.py`
  - `tests/clipping/test_cartesian3d.py`
  - `tests/quadrature/test_folded3d.py`
  - `tests/evals/test_antolin_examples_3d.py`
  - `tests/evals/test_antolin_parity.py`
  - `tests/fixtures/antolin-section6/*`
  - parity/benchmark docs and follow-up notes in `docs/`
- No new runtime dependencies.
