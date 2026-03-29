# No-Triangulation 3D Folded Refactor

## Objective

Refactor CUTKIT 3D CAD folded workflows to avoid boundary triangulation and use
direct CAD face-parameter quadrature, while preserving object-or-arrays box
batch semantics and far-field source-cloud plumbing.

## Scope

- Replace triangulation-based 3D boundary integration in `cutkit.cad` and
  `cutkit.potentials` with face-parameter folded quadrature over clipped solids.
- Add OpenCascade 3D face-sampling helpers that produce deterministic quadrature
  points/weights without mesh generation.
- Update tests to validate no-triangulation pathways and retain existing
  strict/non-strict batch behavior.
- Update docs references that still describe triangulation as part of the 3D
  core workflow.

## Non-Goals

- Singular/near-singular quadrature treatment for BIE/QBX.
- Full replacement of every historical paper-eval helper in one change.
- Performance tuning beyond correctness and deterministic behavior.

## Acceptance Criteria

- 3D `CadSolid3D.integrate_folded_boundary`,
  `CadSolid3D.integrate_over_boxes`, and
  `source_cloud_over_boxes_3d` run without calling triangulation extractors.
- `cutkit.io` exposes a non-triangulated clipped-solid boundary quadrature path.
- Updated tests cover normal flow, strict/non-strict failures, and object-vs-array
  parity for the new pathway.
- `make dev` passes.

## Checklist

- [x] Add OpenCascade 3D boundary-face quadrature primitives.
- [x] Refactor `cutkit.cad` 3D integration to use boundary-face quadrature.
- [x] Refactor `cutkit.potentials` 3D source-cloud generation to use the same path.
- [x] Update tests that monkeypatch triangulation calls.
- [x] Update docs references to triangulation-based workflow wording.
- [x] Run `make dev`.

## Final Outcome

- Status: completed; ready for review.
- Validation: focused CAD/potentials/io tests passed and full `make dev` passed.
- Key API shifts:
  - `cutkit.io.opencascade3d` now provides direct boundary-face quadrature and
    folded solid quadrature without mesh triangulation.
  - `cutkit.cad.CadSolid3D` integration and boundary validation now use
    no-triangulation folded face quadrature.
  - `cutkit.potentials` 3D signed source-cloud generation now consumes
    clipped solids directly through folded face quadrature.
