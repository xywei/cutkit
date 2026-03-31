# No-Triangulation Evals/Parity Refactor

## Objective

Remove triangulation-based boundary handling from legacy 3D eval/parity workflows
and switch them to direct boundary-face folded quadrature.

## Scope

- Refactor `cutkit.evals.antolin_wei_buffa_2022_3d` to represent Section 6.1.3
  boundaries as parametric face patches instead of triangle meshes.
- Replace boundary-triangle Bernstein/general integrals with no-triangulation
  folded face-quadrature integration.
- Update `cutkit.evals.poisson_benchmarks` to consume the new 3D boundary
  integration path.
- Update eval tests to validate the new pathway and remove core triangle
  integrator coupling.

## Acceptance Criteria

- 3D eval/parity modules no longer import/use triangle boundary integrators.
- Poisson volume benchmarks run through no-triangulation folded boundary helpers.
- Eval regression tests pass after interface updates.
- Full `make dev` passes.

## Checklist

- [x] Refactor Section 6.1.3 boundary builder to direct parametric patch descriptor.
- [x] Implement no-triangulation folded volume rule and Bernstein/general integrators.
- [x] Update Poisson benchmark volume integration path.
- [x] Update eval tests and remove triangle-core coupling checks.
- [x] Run focused eval/cad/potentials/io tests.
- [x] Run full `make dev`.

## Final Outcome

- Status: completed; ready for review.
- Validation: focused eval/cad/potentials/io tests passed and full `make dev`
  passed.
- Key changes:
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py` now uses
    `Section613Boundary` parametric patches + folded face quadrature.
  - `src/cutkit/evals/poisson_benchmarks.py` now integrates volume benchmarks via
    `integrate_general_over_section_6_1_3_boundary`.
  - `tests/evals/test_antolin_examples_3d.py` now validates the new non-triangle
    integration flow.
