# Immersed Poisson Galerkin Solver

This repository includes a paper-style immersed Poisson Galerkin workflow over
trimmed 2D domains, assembled with CUTKIT cell clipping and folded quadrature.

## Entry Point

```bash
uv run python scripts/run_poisson_galerkin_benchmark.py --profile quick --backend-mode folded
```

Options:

- `--profile quick|dense`
- `--backend-mode jplus|folded`
- `--manifest-path <path>` for machine-readable output

## What Is Solved

- Weak form: `\int_\Omega \nabla u \cdot \nabla v = \int_\Omega f v`
- Background space: tensor-product open-uniform B-spline (IGA) basis on a
  structured background grid.
- Immersed integration: each active cut/inside cell is integrated on
  `\Omega \cap K` using CUTKIT quadrature (jplus or folded mode).
- Boundary treatment: zero Dirichlet on outer background-box boundaries;
  trimmed-boundary segments are natural (Neumann) in this workflow.

## Validation Strategy

- Solver rows compare each benchmark solve against a same-resolution,
  higher-order jplus reference solve.
- Reported metrics include absolute/relative solution error, CG residual,
  iteration count, and free-DOF count.
- Benchmark pass/fail is profile-threshold based.

## Paper-Style Convergence Plots

Generate reusable SVG convergence plots (absolute and relative error):

```bash
uv run python scripts/plot_poisson_galerkin_benchmark.py --profile quick
```

This writes deterministic SVG artifacts under the configured `--output-dir`.

- `poisson-galerkin-abs_error.svg`
- `poisson-galerkin-rel_error.svg`

Generate a full paper-style figure pack (geometry, cell classification,
solution fields, and convergence plots):

```bash
uv run python scripts/plot_poisson_galerkin_figure_pack.py --profile quick
```

## Related Modules

- Solver implementation: `src/cutkit/evals/poisson_galerkin.py`
- Tests: `tests/evals/test_poisson_galerkin.py`
- Script runner: `scripts/run_poisson_galerkin_benchmark.py`
- Plot runner: `scripts/plot_poisson_galerkin_benchmark.py`
- Figure-pack runner: `scripts/plot_poisson_galerkin_figure_pack.py`
- Reusable plot helpers:
  - `src/cutkit/diagnostics/svg_plot.py`
  - `src/cutkit/diagnostics/poisson_galerkin_plots.py`
  - `src/cutkit/diagnostics/poisson_galerkin_figures.py`
