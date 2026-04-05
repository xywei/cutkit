# UFL IGA + DG-SEM Assembly Plan

## Objective

Add a UFL-based form DSL path that can assemble trimmed-domain systems through
either:

- CUTKIT smooth spline IGA backend, or
- meshmode+grudge DG-SEM backend.

## Scope

- Introduce UFL adapter and method-neutral weak-form IR.
- Implement backend lowering for an initial shared scalar-form subset.
- Integrate meshmode cut-overlay mapping into DG-SEM backend assembly path.
- Add deterministic diagnostics and backend capability checks.

## Dependency

- `meshmode-cut-overlay-integration` must land before DG-SEM backend slice.

## Non-Goals

- Replacing grudge internals.
- Full UFL language support in first release.
- Distributed-memory redesign.

## Acceptance Criteria

- OpenSpec artifacts validate in strict mode.
- Same supported form can be lowered to both `iga` and `dgsem` backends.
- Unsupported terms fail with deterministic backend-specific diagnostics.
- Backend tests cover shared manufactured solutions and expected convergence.
- `make dev` passes.

MVP sequencing:

- Phase 1: UFL + IR + IGA scalar subset.
- Phase 2: DG-SEM backend on same subset via overlay contract.

## Implementation Checklist

- [x] Add UFL adapter entrypoint + IR.
- [x] Add IGA lowering for supported scalar terms.
- [x] Add DG-SEM lowering via meshmode+grudge adapters.
- [x] Add strict/permissive validation behavior.
- [x] Add shared-form backend parity tests.
- [x] Add convergence/parity benchmark examples.
- [x] Update docs and support matrix.
- [x] Run `make dev`.

## Phase Gates

- Phase 1 gate: deterministic UFL->IR + IGA correctness on manufactured tests.
- Phase 2 gate: DG-SEM lowering parity + deterministic diagnostics.

## OpenSpec Link

- `openspec/changes/ufl-iga-and-grudge-dgsem-assembly/`

## Risks / Open Questions

- UFL subset boundary for first release.
- Flux policy defaults for DG-SEM backend.
- B-spline-only vs NURBS-in-first-slice rollout.
