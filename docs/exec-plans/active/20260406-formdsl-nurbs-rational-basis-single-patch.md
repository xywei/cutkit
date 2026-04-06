# Form DSL Single-Patch NURBS Rational Basis

## Objective

Implement deterministic single-patch rational basis execution internals for IGA
when formdsl requests `geometry_map=nurbs`, moving support beyond metadata-only
acceptance.

## Scope

- Implement an explicit rational execution path for IGA lowering with
  `geometry_map=nurbs`.
- Thread deterministic execution-path metadata through IGA payloads.
- Preserve existing scalar B-spline behavior for default/`bspline` geometry-map
  requests.
- Add regression tests and docs updates.

## Non-Goals

- Multipatch interface coupling semantics.
- DG-SEM NURBS execution support.
- Broad vector/tensor backend expansion.

## Acceptance Criteria

- IGA lowering selects a deterministic rational execution path for
  `geometry_map=nurbs` requests.
- Payload metadata makes NURBS-vs-B-spline execution behavior observable and
  reproducible.
- Existing B-spline behavior remains stable for unaffected callers.
- OpenSpec artifacts validate and targeted regression tests pass.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks artifacts for this phase.
- [ ] Implement rational execution internals and payload metadata threading.
- [ ] Add regression tests for NURBS rational path and B-spline stability.
- [ ] Update docs and finalize OpenSpec task tracking.

## Risks / Open Questions

- Rational execution internals may require additional numerical guardrails once
  representative NURBS fixtures are exercised.
