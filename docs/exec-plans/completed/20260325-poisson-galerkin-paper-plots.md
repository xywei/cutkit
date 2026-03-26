# Poisson Galerkin Paper Plots

## Objective

Add paper-style convergence plots for immersed Poisson Galerkin benchmarks and
implement reusable visualization modules in `src/`.

## Scope

- Add deterministic reusable SVG plotting helpers in diagnostics.
- Add Poisson Galerkin-specific convergence plotting helpers and script.
- Add diagnostics tests for rendering and file generation.
- Update docs and OpenSpec artifacts to capture plotting capability.

## Acceptance Criteria

- Plot script generates absolute and relative error SVG artifacts for jplus and
  folded runs.
- Reusable plotting helpers exist under `src/cutkit/diagnostics/`.
- Plot tests pass and full `make dev` remains green.

## Implementation Checklist

- [x] Add reusable SVG plotting helper module.
- [x] Add Poisson Galerkin plot helper module and script entry point.
- [x] Add diagnostics tests for plotting behavior.
- [x] Update docs and OpenSpec requirements/tasks.
- [x] Run focused tests and `make dev`.

## Final Outcome

- Status: completed; ready for review.
- Validation: plotting-focused tests and full `make dev` passed.
- Deliverables include reusable modules under `src/cutkit/diagnostics/` and the
  script `scripts/plot_poisson_galerkin_benchmark.py`.
