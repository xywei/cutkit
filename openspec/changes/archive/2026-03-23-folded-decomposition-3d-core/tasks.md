## 1. Core 3D Data Model and Topology

- [x] 1.1 Add 3D geometry primitives for boundary triangles, seeds, and folded cell descriptors in `src/cutkit/geometry/`.
- [x] 1.2 Add topology utilities for outward-orientation normalization and boundary consistency checks in `src/cutkit/topology/`.
- [x] 1.3 Add clipping-layer entry points for 3D cut-cell classification in `src/cutkit/clipping/`.

## 2. 3D Folded Quadrature and Diagnostics

- [x] 2.1 Add `QuadratureRule3D` and folded 3D rule builders in `src/cutkit/quadrature/`.
- [x] 2.2 Implement jplus/folded seed policies with explicit non-jplus folded-best handling.
- [x] 2.3 Add 3D diagnostics for signed-volume reconstruction and seed invariance in `src/cutkit/diagnostics/`.

## 3. Reproduction Integration and Migration

- [x] 3.1 Refactor `src/cutkit/evals/antolin_wei_buffa_2022_3d.py` to use the new core APIs.
- [x] 3.2 Keep existing public eval entry points stable while switching internals to core implementations.
- [x] 3.3 Remove or deprecate superseded eval-private 3D helper logic after parity checks pass.

## 4. Tests and Validation

- [x] 4.1 Add unit tests for 3D orientation normalization, folded cell generation, and rule determinism.
- [x] 4.2 Expand `tests/evals/test_antolin_examples_3d.py` to validate parity with core 3D paths.
- [x] 4.3 Run `uv run pytest tests/evals/test_antolin_examples_3d.py` and related quadrature tests.

## 5. Documentation and Quality Gate

- [x] 5.1 Update `README.md` and folded follow-up docs to reflect core 3D support status.
- [x] 5.2 Update architecture notes if new 3D module boundaries are introduced.
- [x] 5.3 Run `make dev` and ensure all checks pass.
