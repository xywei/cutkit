# Volumential + QBFEM Foundation

## Objective

Define and deliver two solver-facing CUTKIT extensions for volumetric potential
workflows: (1) signed folded source-cloud export for far-field evaluation, and
(2) a dimension-independent (2D/3D) local IGA-style Galerkin correction
operator workflow for near-field self/list1/list3/4 interactions.

## Scope

- Add OpenSpec change artifacts for both workstreams.
- Implement a deterministic signed source-cloud adapter compatible with
  volumential-style point-potential consumption.
- Implement a local-box 2D/3D Poisson/Green correction workflow that consumes
  boundary values from far-field quadrature and emits assembled local linear
  systems (small, boxed) or matrix-free local matvec operators for near-field
  correction.
- Keep both workstreams aligned with CUTKIT object-or-arrays batch semantics for
  vectorized source, box, and target workflows.
- Resolve compact-support/source-space vs box-solution-space mismatch through
  weak-form coupling: folded support quadrature assembles local load terms
  against box basis/test functions.
- Add tests, docs, and validation commands for both paths.

## Non-Goals

- Replacing volumential FMM internals.
- Shipping a full general-purpose PDE framework with broad BC/stabilization
  policies.
- Introducing singular/near-singular boundary-integral kernels in this step.

## Acceptance Criteria

- Two OpenSpec changes exist with proposal/design/tasks/spec artifacts.
- CUTKIT can export deterministic signed point sources (`point`, `weight`,
  `charge`) from folded clipped regions in 2D/3D for far-field use.
- CUTKIT can emit deterministic batched local boxed Galerkin linear systems or
  matrix-free operators in 2D/3D from supplied boundary traces and restricted
  source support.
- Both APIs support object-mode and array-mode inputs with deterministic
  broadcasting/ordering and mode-equivalent results within tolerance.
- Focused tests and `make dev` pass.

## Implementation Checklist

- [x] Add OpenSpec artifacts for signed source-cloud adapter.
- [x] Add OpenSpec artifacts for local near-field Galerkin correction.
- [x] Implement source-cloud export module/API and typed result container.
- [x] Implement local boxed Galerkin correction module/API for 2D/3D.
- [x] Implement local operator-mode selection (`assembled` and `matrix_free`) with
  equivalent action checks.
- [x] Implement shared object-or-arrays normalization and vectorized evaluation
  pathways for both far and near workflows.
- [x] Add integration tests that verify far/near composition and no
  double-counting.
- [x] Update README/docs index with usage references.
- [x] Run focused tests and `make dev`.

## Outcomes

- Implemented dim-independent far-field signed source-cloud export and batch
  APIs with deterministic pointer/index metadata and volumential-friendly
  materialization helpers.
- Implemented 2D/3D local boxed spline Galerkin near-field operator assembly in
  assembled and matrix-free modes, plus deterministic local solve helpers.
- Added interaction-list plumbing (`self/list1/list3/list4`) for restricted
  source selection and vectorized near-target mapping helpers.
- Added optional target evaluation and composition helpers for reference/debug
  workflows while keeping production composition ownership external.
- Added a dedicated handoff contract doc and README/docs-index links for
  downstream volumential integration.
- Added extensive coverage for object-vs-array equivalence, sign/conservation
  semantics, assembled-vs-matrix-free equivalence, manufactured local solves,
  compact-support edge cases, and far+near regression behavior.

## OpenSpec Archive Notes

- Change: `openspec/changes/archive/2026-03-28-2026-03-27-volumential-signed-source-cloud/`
- Change: `openspec/changes/archive/2026-03-28-2026-03-27-local-3d-nearfield-galerkin/`
- Suggested archive commands:
  - `/opsx-archive 2026-03-27-volumential-signed-source-cloud`
  - `/opsx-archive 2026-03-27-local-3d-nearfield-galerkin`

## Risks / Open Questions

- Signed folded weights can amplify cancellation error in extreme geometries;
  accumulation strategy and tolerances should be explicit.
- Interface boundary between CUTKIT and volumential (ownership of list
  construction, batching, and tree metadata) needs a stable adapter contract.
- Local-box solve cost scaling and preconditioning policy may dominate runtime,
  especially for high-order 3D near corrections.
