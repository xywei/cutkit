# Poisson Benchmark Workflows

This repository includes Poisson-oriented benchmark runners over trimmed planar
and trimmed volume domains.

For the immersed Galerkin solve workflow (assembly + linear solve), see
`docs/poisson-galerkin-solver.md`.

For paper-style convergence plot generation from solver benchmarks, use
`scripts/plot_poisson_galerkin_benchmark.py`.

For geometry + solution + convergence figure packs, use
`scripts/plot_poisson_galerkin_figure_pack.py`.

## Entry Point

```bash
uv run python scripts/run_poisson_benchmarks.py --profile quick --backend-mode jplus
```

Options:

- `--profile quick|dense`
- `--backend-mode jplus|folded`
- `--manifest-path <path>` for machine-readable output
- `--allow-fail` to report tolerance failures without a failing exit status

Both the PR smoke workflow and the scheduled dense workflow use `--allow-fail`.
Their green status confirms that the benchmark command completed, not that its
numerical tolerances passed. A tolerance failure emits a GitHub Actions warning
(or a stderr warning locally); inspect `overall_passed` and the scheduled JSON
manifest's `passed` field for numerical acceptance. Without `--allow-fail`, failed
tolerances return exit status 1.

## What Is Measured

- Planar and volume benchmark runs evaluate manufactured-solution integrands
  tied to Poisson forcing terms.
- Each run reports per-order absolute and relative error against a high-order
  reference value.
- Benchmarks return pass/fail based on profile tolerances.

## Profiles

- `quick`: CI- and local-friendly default profile.
- `dense`: heavier validation profile for deeper numerical checks.

## Validation

- Unit and integration coverage lives in `tests/evals/test_poisson_benchmarks.py`.
- Full repository gate remains `make dev`.
