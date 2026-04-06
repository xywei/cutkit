## Context

`geometry_map` semantics are currently implicit in formdsl lowering. To stage
NURBS rollout safely, the backend matrix needs explicit geometry-map capability
checks and deterministic diagnostics.

This MVP focuses on single-patch support boundaries, not full rational basis
execution redesign.

## Goals / Non-Goals

**Goals**

- Make geometry-map capability checks explicit and deterministic.
- Allow `nurbs` geometry-map requests on IGA backend in single-patch mode.
- Keep DG-SEM constrained to `bspline` geometry-map with deterministic
  diagnostics for unsupported map requests.
- Expose effective geometry-map metadata in backend payloads.

**Non-Goals**

- Multipatch geometry interfaces.
- DG-SEM NURBS lowering semantics.
- High-order rational basis algorithm rewrites.

## Decisions

1. Use metadata key `geometry_map` with default `bspline`.
   - Rationale: keeps behavior deterministic and backward compatible.

2. Add capability diagnostic code `unsupported_geometry_map`.
   - Rationale: keeps strict/permissive behavior consistent with existing
     capability checks.

3. Thread normalized geometry-map string into IGA and DG payloads.
   - Rationale: downstream consumers and tests can assert lowering intent.

4. Keep MVP scoped to single-patch semantics.
   - Rationale: avoids coupling this change to multipatch architecture work.

## Risks / Trade-offs

- [Risk] `nurbs` on IGA may be interpreted as full rational implementation.
  - Mitigation: document MVP scope clearly and preserve existing numerical path
    while adding explicit geometry-map semantics.
- [Risk] permissive DG-SEM behavior could hide unsupported requests.
  - Mitigation: deterministic diagnostics remain surfaced in `AssemblyResult`.

## Migration Plan

1. Add geometry-map capability matrix and diagnostics.
2. Thread geometry-map into backend payload dataclasses.
3. Add strict/permissive tests for IGA and DG-SEM geometry-map behavior.
4. Update support docs and OpenSpec tracking artifacts.
