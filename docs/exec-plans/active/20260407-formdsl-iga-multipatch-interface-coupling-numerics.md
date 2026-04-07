# Form DSL IGA Multipatch Interface Coupling Numerics

## Objective

Implement deterministic numerical interface coupling contributions for formdsl
IGA assembly when multipatch descriptors are present.

## Scope

- Add deterministic plus/minus interface segment pairing with explicit
  validation checks.
- Assemble deterministic interface coupling contributions in IGA operators using
  descriptor boundaries and orientation.
- Keep assembly unchanged for forms without multipatch descriptors.
- Add regression tests and docs updates for numerical coupling semantics.

## Non-Goals

- DG-SEM multipatch numerical coupling.
- Automated patch graph inference from geometry.
- Broader flux-family expansion beyond deterministic penalty-style coupling.

## Acceptance Criteria

- Multipatch descriptors produce deterministic numerical operator deltas on
  backend `iga`.
- Orientation `aligned` vs `reversed` changes coupling contributions
  deterministically.
- Segment pairing mismatches fail with deterministic validation errors.
- Regression coverage and docs reflect implemented behavior.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks artifacts for this phase.
- [ ] Implement deterministic interface segment pairing and validation.
- [ ] Implement numerical interface coupling accumulation in IGA assembly.
- [ ] Add regression tests and docs updates for numerical coupling semantics.

## Risks / Open Questions

- Segment pairing assumptions may be too strict for irregular boundaries and may
  need schema refinement in a follow-up.
- Penalty-style coupling parameters are currently fixed and may need explicit
  metadata controls in a future phase.
