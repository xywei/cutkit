# FormDSL Step Simulations

This page provides dealii `step-xxx` style end-to-end examples for CUTKIT
FormDSL workflows.

## Step 001: Single-Patch Poisson (IGA)

Run a full trimmed-domain Poisson solve through:

- FormDSL parsing,
- IGA assembly,
- CG linear solve,
- and reference-error check against a higher-order solve.

```bash
uv run python scripts/run_formdsl_step_001_iga_poisson.py --resolution 16
```

Useful options:

- `--backend-mode jplus|folded`
- `--artifact-dir <path>`
- `--skip-plots`
- `--manifest-path <path>`
- `--max-abs-error <tol>`

By default this script writes an SVG figure pack under
`.artifacts/formdsl-step-001`.

## Step 002: Multipatch Interface-Coupled Poisson (IGA)

Run a full multipatch-flavored solve with deterministic interface coupling
metadata in the payload and repeated-assembly determinism checks.

```bash
uv run python scripts/run_formdsl_step_002_iga_multipatch_poisson.py --resolution 8
```

Useful options:

- `--artifact-dir <path>`
- `--skip-plots`
- `--manifest-path <path>`
- `--max-residual <tol>`
- `--max-repeat-coeff-diff <tol>`

By default this script writes an SVG figure pack under
`.artifacts/formdsl-step-002`.

## Step 003: DGSEM Convection-Diffusion Prototype (End-To-End Solve)

Run a DGSEM-style end-to-end convection-diffusion solve through FormDSL DG
lowering and a linear solve path with a real CUTKIT trimmed overlay built from
the Section 6.1.1 B-spline panel clipped against a Cartesian background grid:

```bash
uv run python scripts/run_formdsl_step_003_dgsem_poisson.py --resolution 24
```

Useful options:

- `--resolution <n>`
- `--sample-count <n>`
- `--overlay-quadrature-order <n>`
- `--artifact-dir <path>`
- `--skip-plots`
- `--manifest-path <path>`

By default this script writes SVG artifacts under `.artifacts/formdsl-step-003`:

- trimmed overlay geometry,
- clipped-cell classification,
- and a DG solve profile chart.

`grudge` mode requires the `dgsem` extra plus a working
OpenCL platform (`uv sync --extra dgsem`).

No CUTKIT runtime compatibility shims are applied. The `dgsem` extra pins a
tested grudge compatibility window (`grudge==2021.1`, `meshmode==2021.2`,
`loopy==2024.1`, `modepy==2021.1`, `pymbolic==2024.2.2`,
`pytools==2024.1.21`).

## DG-SEM Status

The core `dgsem` backend contract remains deterministic lowering payload
first (operator-chain descriptors and diagnostics).

`solve_form(..., backend="dgsem")` now runs the grudge execution path only
(optional dependencies + OpenCL).

Production-grade grudge operator execution semantics are still evolving.

For lowering inspection:

```bash
uv run python scripts/run_formdsl_dgsem_lowering_example.py --flux sipg
```
