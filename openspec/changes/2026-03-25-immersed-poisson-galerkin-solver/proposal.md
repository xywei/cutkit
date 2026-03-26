## Why

CUTKIT currently provides Poisson-oriented integration benchmarks, but it does
not yet include a solver-level immersed Galerkin workflow that assembles and
solves a trimmed-domain Poisson system end-to-end. This leaves a gap relative
to the paper-style application path.

## What Changes

- Add an immersed tensor-product B-spline (IGA-style) Poisson Galerkin
  assembler/solver over trimmed 2D domains using CUTKIT cell clipping +
  quadrature.
- Add profile-driven solver benchmark runs with explicit jplus/folded backend
  selection.
- Add deterministic solver-level validation against a fine-grid reference solve.
- Add reusable visualization modules and script workflows that generate
  paper-style geometry, cell-classification, solution-field, and convergence
  plots from solver benchmark outputs.
- Add tests, script entry point, and docs for solver workflow usage.

## Capabilities

### New Capabilities

- `immersed-poisson-galerkin-solver`: trimmed-domain immersed Poisson solve and
  solver-level validation metrics.

### Modified Capabilities

- `immersed-iga-poisson`: now includes solver-level (not integration-only)
  validation workflow coverage.

## Impact

- Affected code:
  - `src/cutkit/evals/poisson_galerkin.py`
  - reusable visualization modules under `src/cutkit/diagnostics/`
  - `src/cutkit/evals/__init__.py`
  - `scripts/run_poisson_galerkin_benchmark.py`
  - `scripts/plot_poisson_galerkin_benchmark.py`
  - `tests/evals/test_poisson_galerkin.py`
  - diagnostics plot tests under `tests/diagnostics/`
  - `README.md`, `docs/index.md`, and Poisson docs
- No new mandatory dependencies.
