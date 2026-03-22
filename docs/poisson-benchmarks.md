# Poisson Benchmark Workflows

This repository includes Poisson-oriented benchmark runners over trimmed planar
and trimmed volume domains.

## Entry Point

```bash
uv run python scripts/run_poisson_benchmarks.py --profile quick --backend-mode jplus
```

Options:

- `--profile quick|dense`
- `--backend-mode jplus|folded`
- `--manifest-path <path>` for machine-readable output

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
