# Broaden 3D Clipping and Paper Parity Coverage

## Objective

Close current 3D workflow gaps by broadening Cartesian clipping classes,
instrumenting Section 6.2 3D monotonicity behavior, and promoting
antolin-paper fixtures to full 2D+3D scope.

Related issue: `#10`

## Scope

- Add axis-general x/y/z 3D clipping and Cartesian graph-surface integration
  wrappers.
- Add explicit monotonicity diagnostics for Section 6.2 3D grid rows.
- Update antolin-paper parity fixtures from 2d-only to full-scope matrix.
- Document singular quadrature status relative to the Antolin paper and QBFEM
  deferral.

## Non-Goals

- Implementing singular or near-singular quadrature kernels.
- Replacing Section 6 benchmark protocols.

## Acceptance Criteria

- New clipping/quadrature APIs support x/y/z aligned classes with test coverage.
- Section 6.2 3D manifests include monotonicity diagnostics per order row.
- antolin-paper fixture matrix includes full polygonized and full CAD tracks.
- Docs/tests updated and `make dev` passes.

## Implementation Checklist

- [x] Create OpenSpec artifacts for this change.
- [x] Implement axis-general clipping wrappers and tests.
- [x] Implement axis-general Cartesian integration wrappers and tests.
- [x] Add Section 6.2 3D monotonicity diagnostics + serialization/tests.
- [x] Generate full antolin-paper polygonized fixture.
- [x] Replace antolin-paper CAD fixture with full-scope placeholder.
- [x] Update docs/tests for fixture matrix and singular-quadrature status.
- [x] Run focused tests.
- [x] Run `make dev`.
- [x] Prepare PR.

## Risks

- Axis permutations can introduce subtle coordinate-order bugs.
- Full-profile fixture generation can be expensive.
- Diagnostics may surface instability without immediate numerical remedy.

## Final Outcome

- Status: merged.
- Delivered via: `https://github.com/xywei/cutkit/pull/11`
- Follow-ups: none open from this plan.
