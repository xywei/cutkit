## Context

`geometry_map=nurbs` is implemented for deterministic single-patch IGA
execution, but multipatch assembly remains staged because the form IR does not
yet carry explicit patch/interface descriptors and the backend does not define
deterministic interface orientation handling.

`docs/formdsl-nurbs-multipatch-evaluation.md` recommends introducing
multipatch identifiers and interface descriptors before broader backend
expansion.

## Goals / Non-Goals

**Goals**

- Add deterministic multipatch patch/interface descriptors to formdsl IR
  metadata.
- Lower supported multipatch interface couplings for backend `iga` with stable
  orientation semantics.
- Keep strict/permissive diagnostics deterministic for malformed descriptors and
  unsupported backend combinations.
- Preserve current single-patch lowering behavior for forms that do not declare
  multipatch metadata.

**Non-Goals**

- DG-SEM multipatch interface execution.
- Automatic patch decomposition or patch graph inference from CAD geometry.
- Vector/tensor capability expansion beyond current formdsl policy.

## Decisions

1. Use explicit descriptor-driven metadata for multipatch semantics.
   - Rationale: avoids hidden topology inference and keeps assembly behavior
     reproducible across parsers and backends.

2. Normalize interface orientation before backend integration.
   - Rationale: deterministic orientation handling prevents sign/order drift in
     interface couplings.

3. Keep rollout IGA-only and capability-gated.
   - Rationale: aligns with current backend maturity and avoids premature DG-SEM
     coupling semantics.

## Risks / Trade-offs

- [Risk] Descriptor schema may be underspecified for edge interfaces.
  - Mitigation: define required keys explicitly and add payload-validation tests.
- [Risk] Interface orientation mistakes can silently perturb operators.
  - Mitigation: centralize normalization and assert deterministic diagnostics on
    inconsistent orientation metadata.
- [Risk] Multipatch fixtures can increase maintenance burden.
  - Mitigation: keep initial fixture set small and representative, then grow via
    parity benchmarks.

## Migration Plan

1. Extend OpenSpec requirements for multipatch descriptors and IGA interface
   coupling diagnostics.
2. Add IR/parser descriptor support and deterministic validation errors.
3. Implement IGA interface lowering with orientation normalization and payload
   execution-path metadata.
4. Add regression fixtures/tests and update support documentation.
