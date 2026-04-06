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
- [x] Add design/spec/tasks artifacts for the new change.
- [x] Implement component-aware DG-SEM vector lowering.
- [x] Add vector source lowering semantics and tests.
- [x] Update docs/support matrix and close checklist.

## Final Outcome

- Status: completed and archived.
- Validation: pre-commit quality/test hooks and PR CI checks passed before merge.
- Key PRs:
  - `https://github.com/xywei/cutkit/pull/38`
  - `https://github.com/xywei/cutkit/pull/39`
- OpenSpec archive:
  - `openspec/changes/archive/2026-04-06-formdsl-vector-valued-backend-phase2/`

## Risks / Open Questions

- Component-order conventions must be explicit to avoid parity drift.
- The boundary between shape metadata and execution semantics should stay clear
  to keep parser behavior stable.
