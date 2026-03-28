## Why

Folded far-field quadrature can represent compact-support source densities as
point potentials, but it is not sufficient for robust near-field interactions
(`self`, `list1`, and close `list3/list4`) where kernel behavior becomes
difficult for direct far-style evaluation.

To support QBFEM-style local correction workflows, CUTKIT needs a
dimension-independent local-box assembly path that uses boundary values sampled
from far-field quadrature and emits local IGA-style Galerkin operators for
near-region correction in 2D and 3D.

## What Changes

- Add a dimension-independent local boxed Poisson/Green correction assembly
  workflow for near-field interactions in 2D and 3D.
- Add boundary-trace sampling API(s) that evaluate far-field values on local box
  boundaries.
- Support object-mode and array-mode inputs for local boxes, boundary traces,
  restricted source sets, and near-target batches.
- Add tensor-product B-spline Galerkin local-operator assembly over
  axis-aligned correction boxes in 2D and 3D.
- Assemble local forcing by integrating compact trimmed source support against
  box test functions via folded quadrature coupling.
- Add vectorized APIs that emit local assembled systems (matrix/RHS + metadata)
  or matrix-free matvec operators plus RHS for target batches and deterministic
  diagnostics.
- Add tests/docs for near-correction behavior and composition with far-field
  contributions.

## Capabilities

### New Capabilities

- `local-nearfield-galerkin`: QBFEM-style boxed near-field correction using
  boundary traces plus local IGA operator assembly (assembled or matrix-free)
  with one 2D/3D contract.

### Modified Capabilities

- `immersed-poisson-galerkin-solver`: extend from benchmark-focused 2D immersed
  solve workflow to reusable local-box correction components in 2D/3D.
- `volumential-signed-source-cloud`: compose with local correction workflow for
  far/near potential evaluation.

## Impact

- Affected code:
  - new local correction module(s) under `src/cutkit/`
  - possible shared linear-solver/assembly helpers reused from existing
    Galerkin workflows
  - tests under `tests/` for local correction accuracy and deterministic output
  - docs/README updates for near-field correction usage
- No mandatory dependency changes expected.
