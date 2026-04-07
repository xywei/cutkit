# Form DSL Backend Parity Benchmarks

This workflow provides a lightweight convergence + parity example for the shared
form DSL path across:

- `iga` assembly (manufactured-solution error rows), and
- `dgsem` lowering (deterministic operator signatures).

## Entry Point

```bash
uv run python scripts/run_formdsl_parity_benchmark.py --resolutions 8,16
```

Common options:

- `--resolutions 8,16,24`
- `--max-iga-error 2e-4`
- `--manifest-path <path>` for machine-readable output
- `--allow-fail` to return zero regardless of tolerance outcome
- `--include-multipatch-stress` to run deterministic IGA multipatch stress
  fixtures (3-patch mixed orientations + patch-local selector overrides +
  per-interface penalty controls)

## What Is Reported

- per-resolution IGA absolute error (`iga_abs_error`) for a shared Poisson-like
  manufactured problem,
- shared IR term, boundary, and metadata signatures (must match across
  backends),
- DG-SEM lowering signatures (volume/trace) and DG flux signatures.

When `--include-multipatch-stress` is enabled, the script also reports:

- multipatch fixture rows with execution-path, interface count, nnz, and
  repeatability diffs,
- aligned-vs-reversed orientation matrix delta metric
  (`orientation_delta_max_abs`).

The benchmark enforces that `iga` and `dgsem` assemble from identical parsed IR
signatures before returning results.

## Validation

- Benchmark helper coverage: `tests/evals/test_formdsl_benchmarks.py`
- Shared backend parity coverage: `tests/formdsl/test_formdsl_assembly.py`
- Full repository gate: `make dev`
