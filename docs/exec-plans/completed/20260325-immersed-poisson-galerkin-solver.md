# Immersed Poisson Galerkin Solver

## Objective

Implement a paper-style immersed Poisson Galerkin solve workflow in CUTKIT and
add solver-level validation that compares folded assembly against a fine-grid
reference solve.

## Scope

- Add a trimmed-domain immersed tensor-product B-spline (IGA-style) Galerkin
  Poisson assembler/solver module.
- Add profile-driven solver benchmark runner with jplus/folded backend selection.
- Add tests for solver determinism, backend support, and residual quality.
- Add docs + script entry point for local/CI validation.
- Define and track the change using OpenSpec artifacts.

## Non-Goals

- Singular/near-singular kernel quadrature.
- Full PDE framework generalization beyond the benchmark protocol.
- 3D Poisson Galerkin solve in this change.

## Acceptance Criteria

- Solver module assembles and solves immersed Poisson systems on Section 6.1.1
  trimmed geometry with deterministic output.
- `run_poisson_galerkin_benchmark` supports jplus/folded assembly modes and
  emits profile-based pass/fail metadata.
- Focused solver tests and full `make dev` pass.
- OpenSpec proposal/design/tasks/spec artifacts are present and aligned with the
  implementation.

## Implementation Checklist

- [x] Add OpenSpec change artifacts for immersed Poisson Galerkin solver.
- [x] Implement solver + benchmark APIs in `src/cutkit/evals/poisson_galerkin.py`.
- [x] Add script entry point and exports.
- [x] Add solver regression tests under `tests/evals/`.
- [x] Update README/docs index and Poisson docs cross-links.
- [x] Run focused tests and full `make dev`.

## Final Outcome

- Status: completed; ready for review.
- Validation: focused Poisson solver tests and full `make dev` passed.
- OpenSpec change: `openspec/changes/archive/2026-03-28-2026-03-25-immersed-poisson-galerkin-solver/`.
