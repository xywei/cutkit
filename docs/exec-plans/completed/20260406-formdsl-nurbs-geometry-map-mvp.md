# Form DSL NURBS Geometry-Map MVP

## Objective

Implement a single-patch NURBS geometry-map MVP for formdsl by introducing
deterministic backend capability semantics and payload metadata threading for
`geometry_map` requests.

## Scope

- Add explicit geometry-map capability checks by backend.
- Allow `geometry_map=nurbs` on IGA backend (single-patch scope).
- Keep DG-SEM geometry-map support constrained to `bspline` with deterministic
  diagnostics for unsupported requests.
- Thread normalized geometry-map metadata into backend payloads.
- Add strict/permissive tests and doc updates.

## Non-Goals

- Multipatch interface support.
- DG-SEM NURBS execution semantics.
- Rational basis algorithm overhaul.

## Acceptance Criteria

- Geometry-map capability mismatches are deterministic (`unsupported_geometry_map`).
- IGA accepts `geometry_map=nurbs` and reports it in payload metadata.
- DG-SEM strict/permissive behavior for unsupported geometry maps is covered by
  regression tests.
- OpenSpec artifacts validate and docs are updated.

## Implementation Checklist

- [x] Add proposal/design/spec/tasks artifacts for this change.
- [x] Add geometry-map capability checks and payload threading.
- [x] Add tests for strict/permissive geometry-map behavior.
- [x] Update docs and finalize OpenSpec task tracking.

## Final Outcome

- Status: completed and archived.
- Validation: targeted regression checks and PR CI passed.
- Key PRs:
  - `https://github.com/xywei/cutkit/pull/41`
  - `https://github.com/xywei/cutkit/pull/40`
- OpenSpec archive:
  - `openspec/changes/archive/2026-04-06-formdsl-nurbs-geometry-map-mvp/`

## Risks / Open Questions

- Users may assume full rational basis implementation from metadata acceptance;
  docs must state MVP scope clearly.
