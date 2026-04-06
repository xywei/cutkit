# Form DSL Vector Backend Phase 2

## Objective

Build on the vector `value_shape` MVP by adding deterministic component-aware
backend semantics for rank-1 vector forms, primarily in DG-SEM lowering.

## Scope

- Define component-aware DG-SEM lowering structure for vector forms.
- Add deterministic vector source handling conventions in lowering payloads.
- Tighten vector-shape consistency checks for mapping and UFL-like parser paths.
- Add regression tests for vector lowering behavior and diagnostics.
- Update support docs and OpenSpec artifacts.

## Non-Goals

- Rank-2 tensor execution support.
- Full vector IGA execution support.
- NURBS/multipatch implementation.

## Acceptance Criteria

- Rank-1 vector DG-SEM lowering includes deterministic component-aware entries.
- Vector source lowering behavior is deterministic and regression-tested.
- Shape mismatch diagnostics remain deterministic in strict and permissive modes.
- Docs and OpenSpec artifacts reflect current vector execution semantics.

## Implementation Checklist

- [x] Create OpenSpec proposal `formdsl-vector-valued-backend-phase2`.
- [ ] Add design/spec/tasks artifacts for the new change.
- [ ] Implement component-aware DG-SEM vector lowering.
- [ ] Add vector source lowering semantics and tests.
- [ ] Update docs/support matrix and close checklist.

## Risks / Open Questions

- Component-order conventions must be explicit to avoid parity drift.
- The boundary between shape metadata and execution semantics should stay clear
  to keep parser behavior stable.
