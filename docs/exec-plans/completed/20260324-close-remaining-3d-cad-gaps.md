# Close Remaining 3D CAD Gaps

## Objective

Close the remaining 3D follow-up gap by adding CAD-native 3D geometry ingestion
and clipping paths that feed the folded 3D boundary workflow.

## Scope

- Add optional OpenCascade 3D adapters to ingest solids and extract boundary
  triangulations.
- Add CAD-native clipping helpers for axis-aligned box clipping and boundary
  extraction.
- Add tests that validate unavailable-mode behavior and, when CAD is available,
  validate clipped-volume reconstruction through folded signed-volume checks.
- Update docs and OpenSpec artifacts to mark the 3D follow-up gap as closed.

## Non-Goals

- Singular/near-singular quadrature.
- Full unstructured CAD boolean workflow matrix.
- Volumential downstream adapters.

## Acceptance Criteria

- `cutkit.io` exposes CAD-native 3D ingest + clip APIs with graceful
  unavailable-mode behavior.
- Boundary triangles extracted from CAD solids are usable by existing folded 3D
  signed-volume reconstruction utilities.
- Tests pass in both unavailable mode (error/skip behavior) and available mode
  (numeric reconstruction checks).
- Docs and OpenSpec artifacts no longer list unresolved 3D coverage gaps.
- `make dev` passes.

## Implementation Checklist

- [x] Update OpenSpec change artifacts for CAD-native 3D ingest/clip closure.
- [x] Implement `src/cutkit/io/opencascade3d.py` and export APIs.
- [x] Add tests under `tests/io/` for availability + clipping volume behavior.
- [x] Update README/follow-up docs to remove remaining 3D-gap language.
- [x] Run focused tests and `make dev`.
- [x] Move this plan to completed with final outcome.

## Final Outcome

- Status: completed; ready for review.
- Validation: focused 3D tests passed and full `make dev` passed.
- OpenSpec: change artifacts updated under
  `openspec/changes/2026-03-24-3d-bounded-surface-refinement/`.
