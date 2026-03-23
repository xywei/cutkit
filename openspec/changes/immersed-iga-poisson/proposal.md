## Why

The folded-decomposition paper includes Poisson immersed-IGA applications in trimmed planar and trimmed volume settings, but CUTKIT currently stops at integration reproductions. We need benchmark-level Poisson workflows to validate solver-facing impact and close the remaining paper-coverage gap.

## What Changes

- Add benchmark runners for Poisson problems on trimmed planar geometries using folded quadrature.
- Add benchmark runners for Poisson problems on trimmed volumes using folded quadrature.
- Add convergence and accuracy metrics with deterministic reporting suitable for regression tests.
- Add tests and docs that define required benchmark behavior and acceptance criteria.

## Capabilities

### New Capabilities
- `immersed-iga-poisson`: Poisson benchmark workflows over trimmed domains that use CUTKIT folded quadrature and report reproducible convergence metrics.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - new benchmark modules under `src/cutkit/evals/` (or a dedicated application package)
  - `src/cutkit/quadrature/` and related adapter paths
  - new Poisson regression tests under `tests/`
  - reproduction and docs updates in `scripts/` and `README.md`
- May require optional solver dependencies for benchmark execution.
- Adds application-level validation beyond raw integration tests.
