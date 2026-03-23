## Why

CUTKIT has 3D Section 6.1.3 and 6.2 reproduction helpers, but they are eval-local and explicitly adapted rather than a first-class core folded-decomposition implementation. We need a spec-governed 3D core so 3D folded rules are reusable across evals, diagnostics, and downstream consumers.

## What Changes

- Add core 3D geometry, topology, clipping, and quadrature APIs for folded decomposition on curved polyhedra.
- Add 3D quadrature rule containers and diagnostics for volume reconstruction and integration consistency.
- Refactor 3D Section 6 reproduction runners to consume core 3D APIs instead of eval-private implementations.
- Add focused unit, integration, and regression tests for 3D seed policies, folded cells, and convergence behavior.

## Capabilities

### New Capabilities
- `folded-decomposition-3d`: Core folded decomposition and quadrature generation for 3D curved polyhedra with deterministic seed handling and diagnostics.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/geometry/`
  - `src/cutkit/topology/`
  - `src/cutkit/clipping/`
  - `src/cutkit/quadrature/`
  - `src/cutkit/diagnostics/`
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py`
  - `tests/quadrature/`
  - `tests/evals/test_antolin_examples_3d.py`
- May add optional 3D helper dependencies for robust clipping and triangulation.
- Establishes a cleaner path for solver-facing 3D quadrature rule export.
