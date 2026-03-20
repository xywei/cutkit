# Paper 2D Example Reproduction

## Objective

Reproduce the 2D examples in Antolin-Wei-Buffa (2022) within the current
CUTKIT folded-decomposition implementation and add them as scriptable examples
and regression tests in the active PR.

## Scope

- Add reusable experiment helpers for Section 6.1.1, 6.1.2, and 6.2 in 2D.
- Add a script to run and print reproduction tables.
- Add tests that validate the qualitative behaviors reported in the paper.

## Non-Goals

- Reproducing 3D examples.
- Adding CAD-kernel-backed exact B-rep trimming.

## Acceptance Criteria

- New script runs in the development environment.
- New tests pass in CI-style checks.
- Existing checks (`make check`) still pass.

## Checklist

- [x] Add 2D paper-example helper module in `cutkit.evals`.
- [x] Add script to run the reproductions and print tabulated errors.
- [x] Add tests for polynomial and non-polynomial 2D experiments.
- [x] Run full repository checks.
