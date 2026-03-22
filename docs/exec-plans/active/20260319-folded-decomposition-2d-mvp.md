# Folded Decomposition 2D MVP

## Objective

Implement a first folded-decomposition quadrature path for polygonized trimmed
2D panels in CUTKIT, with diagnostics and tests suitable for CI.

## Scope

- New 2D geometry/topology primitives for trimmed panels.
- Folded signed-triangle decomposition and quadrature rule aggregation.
- Area and low-order moment diagnostics.
- Eval harness integration and test coverage.

## Non-Goals

- 3D folded decomposition.
- CAD trimming kernels.
- Singular-kernel-focused quadrature.

## Acceptance Criteria

- Baseline and new tests pass.
- Architecture contract remains valid.
- Cut-panel eval script reports folded diagnostics and passes.
- OpenSpec change tasks are fully checked off.

## Checklist

- [x] Add geometry data classes for loops and trimmed panels.
- [x] Add topology normalization and anchor selection.
- [x] Add folded decomposition and quadrature rule generation.
- [x] Add area/moment diagnostics.
- [x] Integrate diagnostics into eval harness.
- [x] Add tests for topology, decomposition, and moments.
- [x] Document MVP limits and follow-up roadmap.
- [x] Run full validation and close OpenSpec tasks.

## Risks

- Cancellation in thin features can magnify floating-point error.
- Anchor selection robustness for pathological panels may need extra heuristics.
