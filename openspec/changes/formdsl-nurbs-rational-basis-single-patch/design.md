## Context

`geometry_map=nurbs` is now accepted for single-patch IGA workflows, but that
support is still metadata-level. The backend needs deterministic rational basis
execution internals so accepted geometry-map requests map to explicit numerical
behavior.

## Goals / Non-Goals

**Goals**

- Introduce deterministic rational-basis execution for single-patch
  `geometry_map=nurbs` in the IGA backend.
- Preserve existing scalar B-spline lowering semantics for
  `geometry_map=bspline`.
- Surface enough payload metadata to make NURBS vs B-spline execution path
  observable in tests.

**Non-Goals**

- Multipatch interface terms or patch-coupling semantics.
- DG-SEM NURBS execution behavior.
- Vector/tensor expansion beyond current value-shape support policy.

## Decisions

1. Keep this phase single-patch and IGA-only.
   - Rationale: aligns with current capability boundaries and avoids coupling to
     multipatch architecture.

2. Add explicit execution-path metadata for IGA lowering results.
   - Rationale: preserves deterministic diagnostics and enables precise
     regression assertions.

3. Preserve B-spline defaults for callers that omit `geometry_map`.
   - Rationale: backward compatibility with existing scalar formdsl clients.

## Risks / Trade-offs

- [Risk] Rational execution internals may expose numerical edge cases not seen
  in metadata-only mode.
  - Mitigation: add focused regression tests for representative single-patch
    forms and retain deterministic diagnostics.
- [Risk] Metadata surface could become unstable if underspecified.
  - Mitigation: codify deterministic payload semantics in OpenSpec scenarios.

## Migration Plan

1. Extend OpenSpec requirements for IGA rational execution behavior.
2. Implement NURBS execution-path internals and deterministic metadata threading.
3. Add strict/permissive tests for capability and payload behavior.
4. Update support docs and execution-plan tracking.
