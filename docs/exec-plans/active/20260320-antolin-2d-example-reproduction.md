# Antolin Example Reproduction

## Objective

Reproduce the Section 6 examples in Antolin-Wei-Buffa (2022) in a CAD-native
CUTKIT folded-decomposition workflow (OpenCascade as CAD core) and add them as
scriptable examples and regression tests in the active PR.

## Scope

- Add reusable experiment helpers for Section 6.1.1, 6.1.2, and 6.2 in 2D.
- Match Section 6 elementwise Cartesian-grid/cell protocol for 2D tests with
  exact CAD clipping (OpenCascade).
- Implement Eq. (18) error definition for polynomial integration on trimmed cells.
- Add reusable Section 6.1.3 and Section 6.2-style 3D experiment helpers.
- Match Section 6.2 3D Cartesian cut-cell refinement workflow.
- Add a script to run and print reproduction tables.
- Add tests that validate the qualitative behaviors reported by Antolin-Wei-Buffa (2022).

## Non-Goals

- Replacing polygonized fallback helpers used for lightweight local iteration.

## Acceptance Criteria

- New script runs in the development environment.
- New tests pass in CI-style checks.
- Existing checks (`make check`) still pass.

## Checklist

- [x] Add 2D Antolin-Wei-Buffa example helper module in `cutkit.evals`.
- [x] Implement Cartesian cell clipping/classification for Section 6 protocol.
- [x] Implement Eq. (18) absolute/relative polynomial error reporting.
- [x] Implement Section 6.2 elementwise grid-refinement convergence protocol.
- [x] Add OpenCascade exact clipping path for Section 6.1.1/6.1.2 2D cells.
- [x] Add CAD-native folded quadrature over curved edges.
- [x] Add 3D Section 6.1.3 boundary-based polynomial reproduction helpers.
- [x] Add 3D Section 6.2 single-cell order sweep helpers.
- [x] Add 3D Section 6.2 Cartesian cut-cell refinement experiment helpers.
- [x] Add script to run the reproductions and print tabulated errors.
- [x] Add tests for polynomial and non-polynomial 2D and 3D experiments.
- [x] Run full repository checks.
