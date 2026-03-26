## Context

The current 3D quadrature layer already supports axis-general one-sided
graph-surface integration and Section 6.1.3 boundary reconstruction. However,
it still lacks:

- bounded slab integration between two trim surfaces on a selected axis;
- side-face refinement support in the Section 6.1.3 boundary builder.
- CAD-native 3D solid ingestion/clipping adapters that feed folded boundary
  triangulations.

These limitations constrain how far 3D workflows can be pushed beyond the
current benchmark-centered path.

## Goals / Non-Goals

**Goals**

- Add bounded two-surface Cartesian integration while preserving existing
  one-sided APIs.
- Enable Section 6.1.3 side-face refinement through `side_resolution >= 1`.
- Add reusable OpenCascade 3D ingest/clip adapters with graceful unavailable
  behavior.
- Add deterministic tests for new bounded integration semantics and side
  refinement behavior.

**Non-Goals**

- General CAD-native 3D trim ingestion.
- Singular/near-singular quadrature.
- Benchmark protocol redesign.

## Decisions

1. Add new bounded integration entry points instead of changing one-sided API
   semantics.
   - Rationale: keeps backward compatibility and avoids silent behavior changes.

2. Use per-column lower/upper callbacks with unit-cube clamping.
   - `None` lower -> `0`, `None` upper -> `1`.
   - If clamped upper <= clamped lower, skip the column.
   - Rationale: supports both full bounded slabs and partially bounded columns.

3. Remove the `side_resolution == 1` guard in Section 6.1.3 boundary building.
   - Rationale: side refinements are conforming for this topology and should be
     available for robustness experiments.

4. Add an `io.opencascade3d` adapter module rather than pushing CAD bindings
   into core layers.
   - Rationale: architecture keeps core layers independent of optional CAD IO;
     IO adapters can depend on topology/geometry utilities for normalization.

## Risks / Trade-offs

- Bounded semantics with `None` bounds need explicit docs/tests to avoid
  ambiguity.
- Side refinement increases triangle counts and may affect runtime.
- Higher side resolutions could expose orientation-manifold edge cases that were
  hidden at `side_resolution=1`.

## Validation Plan

- Quadrature unit tests for bounded slabs on x/y/z, bound clamping semantics,
  and invalid axis handling.
- Eval tests for Section 6.1.3 side refinement with seed-invariant signed volume.
- Run full repository quality gate (`make dev`).
