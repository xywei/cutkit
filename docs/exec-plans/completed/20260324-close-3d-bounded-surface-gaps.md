# Close 3D Bounded-Surface Gaps

## Objective

Close two concrete 3D workflow gaps still limiting paper-aligned coverage in
CUTKIT:

1. Cartesian 3D integration currently only supports one-sided graph surfaces
   (`surface -> 1`) and cannot integrate bounded slabs between two trim
   surfaces.
2. Section 6.1.3 boundary construction rejects side-face refinement
   (`side_resolution != 1`) even when the refined side meshes are conforming.

## Scope

- Add bounded two-surface Cartesian 3D integration APIs (axis-general and
  x/y/z wrappers) in `src/cutkit/quadrature/folded3d.py`.
- Keep existing one-sided APIs stable for backward compatibility.
- Remove the Section 6.1.3 side-resolution restriction and validate refined side
  meshes via tests.
- Update docs and OpenSpec artifacts for the narrowed remaining 3D follow-ups.

## Non-Goals

- Full CAD-native 3D boundary extraction and ingestion pipeline.
- Singular or near-singular quadrature algorithms.
- Changing Section 6 benchmark definitions.

## Acceptance Criteria

- New bounded-surface integration APIs return expected volume fractions for
  deterministic slab fixtures on x/y/z modes.
- Existing one-sided Cartesian integration behavior remains unchanged.
- Section 6.1.3 boundary generation supports `side_resolution > 1` with positive,
  seed-invariant signed volume.
- Docs and OpenSpec artifacts are updated to reflect the new 3D coverage.
- `make dev` passes.

## Implementation Checklist

- [x] Create OpenSpec change artifacts for this work.
- [x] Implement bounded Cartesian 3D surface integration APIs and exports.
- [x] Add quadrature tests for bounded slab semantics and axis behavior.
- [x] Lift Section 6.1.3 side-resolution restriction and add regression tests.
- [x] Update README/follow-up docs for 3D status.
- [x] Run focused tests and `make dev`.
- [x] Finalize plan outcome and move to completed after validation.

## Risks

- Bounded-interval semantics around `None` bounds may be interpreted
  inconsistently if not documented clearly.
- Additional side-face refinement may expose orientation/manifold edge cases at
  higher resolutions.

## Final Outcome

- Status: completed; ready for review.
- Validation: focused 3D tests passed and full `make dev` passed.
- Spec workflow: OpenSpec change artifacts added under
  `openspec/changes/archive/2026-03-25-2026-03-24-3d-bounded-surface-refinement/`.
