## 1. Core Geometry and Topology Primitives

- [x] 1.1 Add `TrimmedPanel2D` and loop dataclasses in `src/cutkit/geometry/`.
- [x] 1.2 Add orientation normalization and loop validation in `src/cutkit/topology/`.
- [x] 1.3 Add interior-anchor selection with fallback and invariants.

## 2. Folded Decomposition and Rule Construction

- [x] 2.1 Implement signed-triangle folded decomposition in `src/cutkit/quadrature/`.
- [x] 2.2 Implement triangle quadrature mapping and panel rule aggregation.
- [x] 2.3 Define a stable `QuadratureRule2D` output structure.

## 3. Diagnostics and Verification

- [x] 3.1 Add area consistency checks (panel vs aggregated signed triangles).
- [x] 3.2 Add low-order moment verification utilities in `src/cutkit/diagnostics/`.
- [x] 3.3 Integrate folded metrics into eval harness output.

## 4. Tests and Eval Corpus

- [x] 4.1 Add unit tests for orientation normalization and anchor validity.
- [x] 4.2 Add tests for decomposition correctness on hole, concave, and thin cases.
- [x] 4.3 Add quadrature accuracy tests for constant, linear, and quadratic monomials.

## 5. Documentation and Quality Gate

- [x] 5.1 Update docs to describe folded-decomposition MVP scope and limits.
- [x] 5.2 Ensure `make check` and cut-panel eval pass with new paths.
- [x] 5.3 Record follow-up issues for 3D and singular-kernel extensions.
