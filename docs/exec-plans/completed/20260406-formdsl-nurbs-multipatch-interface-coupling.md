# Form DSL NURBS Multipatch Interface Coupling

## Objective

Introduce deterministic multipatch interface descriptor and coupling behavior
for formdsl lowering on backend `iga`, building on completed single-patch NURBS
rational execution support.

## Scope

- Add explicit multipatch patch/interface descriptor support in formdsl
  parsing/IR metadata.
- Implement capability-gated interface coupling lowering for backend `iga` with
  deterministic orientation handling.
- Keep strict/permissive diagnostics deterministic for malformed descriptors and
  unsupported backend combinations.
- Add regression tests and docs updates for multipatch semantics.

## Non-Goals

- DG-SEM multipatch execution support.
- Automatic patch decomposition or topology inference from CAD inputs.
- Vector/tensor capability expansion beyond current formdsl policy.

## Acceptance Criteria

- Supported multipatch descriptor payloads parse deterministically into IR
  metadata.
- Backend `iga` lowers supported multipatch interface couplings through a
  deterministic execution path with stable orientation semantics.
- Unsupported or malformed multipatch requests emit deterministic diagnostics in
  strict and permissive modes.
- Regression tests and docs capture multipatch behavior and boundaries.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks artifacts for this phase.
- [x] Implement multipatch descriptor parsing and IR threading.
- [x] Implement IGA multipatch interface lowering with deterministic
  orientation handling.
- [x] Add regression tests and update docs with completed semantics.

## Risks / Open Questions

- Interface descriptor schema may need refinement for edge-orientation and
  boundary-interface corner cases.
- Multipatch fixtures should stay small and deterministic to avoid brittle
  parity signals.
