## 1. OpenSpec and Planning

- [x] 1.1 Add proposal/design/tasks/spec artifacts for immersed Poisson Galerkin solver.
- [x] 1.2 Add execution plan in `docs/exec-plans/active/`.

## 2. Solver Implementation

- [x] 2.1 Add immersed trimmed-domain tensor-product B-spline Poisson assembly
  and CG solve APIs.
- [x] 2.2 Add profile-driven solver benchmark API with jplus/folded backend selection.
- [x] 2.3 Add manifest serialization for solver benchmark outputs.

## 3. Integration Points

- [x] 3.1 Export solver APIs via `src/cutkit/evals/__init__.py`.
- [x] 3.2 Add script entry point for local/CI solver benchmark runs.

## 4. Visualization

- [x] 4.1 Add reusable SVG plotting helpers in `src/cutkit/diagnostics/`.
- [x] 4.2 Add Poisson Galerkin figure helpers (geometry/cell/solution/convergence) in `src/cutkit/diagnostics/`.
- [x] 4.3 Add script entry points for paper-style Poisson Galerkin plot and figure-pack generation.
- [x] 4.4 Add diagnostics tests for plotting helpers and generated SVG artifacts.

## 5. Validation and Docs

- [x] 5.1 Add solver tests for validation/determinism/backend support.
- [x] 5.2 Update README/docs index and Poisson docs references.
- [x] 5.3 Run focused tests and `make dev`.
