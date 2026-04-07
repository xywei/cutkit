# Form DSL IGA Multipatch Interface Controls

## Objective

Add deterministic per-interface coupling controls for IGA multipatch assembly
while preserving global fallback semantics.

## Scope

- Add optional per-interface penalty field in multipatch interface descriptors.
- Validate interface penalties deterministically during parsing/IR checks.
- Apply per-interface override precedence over global `multipatch_penalty`.
- Expose effective interface penalty values in IGA payload metadata.
- Add regression tests and docs updates.

## Non-Goals

- DG-SEM multipatch execution.
- New coupling families beyond current penalty-style model.
- Adaptive penalty tuning heuristics.

## Acceptance Criteria

- Valid per-interface penalties parse and propagate through IR.
- Per-interface penalties override global penalty for targeted interfaces only.
- Invalid penalty values fail deterministically.
- IGA payload metadata reports effective interface penalties.
- Regression tests and docs cover new behavior.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks artifacts.
- [ ] Implement descriptor and validation support for optional interface
  penalties.
- [ ] Implement IGA precedence and metadata exposure for effective penalties.
- [ ] Add regression tests and docs updates.

## Risks / Open Questions

- Interface duplicates remain invalid regardless of penalties; no merge policy is
  introduced in this phase.
