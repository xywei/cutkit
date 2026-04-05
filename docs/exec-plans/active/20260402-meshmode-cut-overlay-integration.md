# Meshmode Cut-Overlay Integration

## Objective

Define and implement a first-class CUTKIT adapter that maps trimmed/cut-cell
integration outputs onto meshmode-friendly overlay payloads for DG assembly
without body-fitted meshing.

This plan is a prerequisite for DG-SEM backend work documented in
`docs/exec-plans/completed/20260402-ufl-iga-and-grudge-dgsem-assembly.md`.

## Scope

- Add a stable public overlay API and typed result/status objects.
- Implement deterministic element mapping from CUTKIT outputs to meshmode target
  element identifiers.
- Add strict/permissive validation modes and actionable diagnostics.
- Add docs/examples/tests for nominal and mixed-status behavior.

## Non-Goals

- Replacing grudge/meshmode discretization internals.
- Introducing meshmode as a mandatory dependency for all CUTKIT users.
- Building distributed overlay exchange in this phase.

## Acceptance Criteria

- OpenSpec change artifacts exist and validate in strict mode.
- Overlay API returns deterministic per-element statuses and diagnostics.
- Strict mode fails fast on blocking mismatches; permissive mode returns partial
  success payloads with failure details.
- Integration tests cover valid mapping, mapping mismatch, orientation mismatch,
  and mixed batches.
- Overlay payload includes explicit contract versioning and deterministic
  ordering guarantees.
- `make dev` passes.

## Implementation Checklist

- [x] Define overlay dataclasses/contracts at a stable public boundary.
- [x] Implement overlay assembly entrypoint with explicit mapping inputs.
- [x] Implement deterministic mapping + validation checks.
- [x] Implement strict/permissive modes and status population.
- [x] Add unit tests for mapping, statuses, and diagnostics.
- [x] Add integration tests with representative meshmode-style layouts.
- [x] Add docs usage section and minimal end-to-end example.
- [x] Run `make dev`.

## Phase Gates

- Phase A gate: contract + deterministic validation + strict/permissive tests.
- Phase B gate: downstream-consumer readiness for DG-SEM adapter consumption.

## OpenSpec Link

- `openspec/changes/meshmode-cut-overlay-integration/`

## Risks / Open Questions

- Initial scope of meshmode workflow support (nodal only vs nodal+modal).
- Boundary orientation conventions across 2D/3D adapters.
- Trade-off between deep validation cost and batch throughput.
