## Context

The repository has robust integration-level parity checks, but lacks a direct
assembled immersed Galerkin solve path for Poisson. We need a deterministic
solver benchmark that consumes existing clipping and quadrature APIs and reports
solver-level accuracy metrics.

## Goals / Non-Goals

**Goals**

- Assemble trimmed-domain tensor-product B-spline (IGA-style) Galerkin
  stiffness/load systems using CUTKIT cell clipping and jplus/folded quadrature
  backends.
- Solve the linear system with a dependency-light iterative method.
- Validate folded/jplus solver outputs against a fine-grid reference solve with
  reproducible pass/fail metrics.
- Generate paper-style figure packs (geometry + solution + convergence) via
  reusable visualization modules in `src/`.

**Non-Goals**

- A full-purpose FEM framework with broad boundary-condition support.
- Singular/near-singular quadrature coupling.
- 3D solver assembly in this change.

## Decisions

1. Place solver in `cutkit.evals`.
   - Rationale: application-level workflow, similar to existing reproducibility
     and benchmark modules.

2. Use trimmed-cell tensor-product B-spline assembly with existing clipped-cell
   helpers.
   - Rationale: reuse deterministic clipping and quadrature paths already used
     by Section 6 reproductions.

3. Use a pure-Python conjugate-gradient solver.
   - Rationale: avoids adding hard linear-algebra dependencies while keeping
     solve behavior deterministic for benchmark-size systems.

4. Use profile-driven fine-grid reference comparisons.
   - Rationale: avoids requiring closed-form exact solutions for mixed immersed
     boundary treatment while preserving convergence/accuracy signal.

5. Implement deterministic SVG plotting helpers in `cutkit.diagnostics`.
   - Rationale: avoids mandatory plotting dependencies while providing
     script-consumable, reusable visualization primitives.

## Risks / Trade-offs

- Pure-Python assembly/CG can be slower than NumPy/SciPy solves.
- Current boundary treatment is benchmark-focused and not a full BC policy
  surface.
- Reference-grid comparison requires compatible resolution ratios.
- SVG-only plotting is intentionally lightweight and not a full charting stack.

## Validation Plan

- Unit tests for profile validation, backend support, determinism, and residual
  quality.
- Diagnostics tests for deterministic SVG chart rendering and plot-file output.
- Script-level manifest checks.
- Full repository gate via `make dev`.
