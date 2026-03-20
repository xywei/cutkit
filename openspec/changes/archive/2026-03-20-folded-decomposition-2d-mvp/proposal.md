## Why

CUTKIT needs an in-repo folded decomposition implementation for trimmed-domain quadrature. Related public work is useful background, but there is no direct reusable implementation in this repository, which blocks robust cut-cell quadrature workflows.

## What Changes

- Add a 2D folded-decomposition MVP for polygonized trimmed panels (one outer loop with optional holes).
- Add topology normalization utilities for loop orientation, validation, and interior anchor selection.
- Add quadrature rule generation from signed triangle decomposition.
- Add diagnostics for area consistency and low-order polynomial moments.
- Add focused tests and eval cases for baseline, hole, concave, and thin/sliver panel configurations.

## Capabilities

### New Capabilities
- `folded-decomposition-2d`: Topology-normalized folded decomposition and quadrature generation for trimmed 2D panels, with diagnostics and verification hooks.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/geometry/`
  - `src/cutkit/topology/`
  - `src/cutkit/quadrature/`
  - `src/cutkit/diagnostics/`
  - `src/cutkit/evals/`
  - `tests/`
- No new external runtime dependencies are required for the MVP.
- Creates a clean adapter path for future integration into `volumential`.
