## Context

Multipatch descriptors are now parsed and threaded through `WeakFormIR`, and
IGA payloads expose deterministic `interface_lowering` metadata. However,
assembly operators are still unchanged by interface descriptors.

This phase adds deterministic interface-coupling matrix contributions on backend
`iga` using descriptor boundaries and orientation.

## Goals / Non-Goals

**Goals**

- Add deterministic numerical interface coupling contributions for IGA
  multipatch descriptors.
- Respect descriptor orientation (`aligned`/`reversed`) during plus/minus point
  pairing.
- Keep behavior unchanged when `multipatch` metadata is absent.
- Emit deterministic validation errors for interface segment pairing failures.

**Non-Goals**

- DG-SEM multipatch numerical coupling.
- Full multipatch patch-graph inference from geometry.
- Physics-complete flux-family expansion beyond deterministic penalty-style
  coupling for this phase.

## Decisions

1. Assemble deterministic symmetric penalty-style interface coupling terms.
   - Rationale: provides stable numerical impact and clear regression behavior
     without introducing broader flux-family complexity.

2. Pair plus/minus boundary segments deterministically by ordered segment lists
   and enforce segment count/length compatibility.
   - Rationale: avoids implicit geometry heuristics and makes failure modes
     explicit.

3. Apply orientation to quadrature parameter mapping (`t` vs `1-t`) on the
   minus side.
   - Rationale: deterministic and directly testable orientation semantics.

## Risks / Trade-offs

- [Risk] Segment list pairing may reject certain valid but irregular boundary
  layouts.
  - Mitigation: enforce deterministic validation and iterate schema/geometry
    assumptions in future phases.
- [Risk] Interface penalties can over-constrain certain synthetic forms.
  - Mitigation: use deterministic defaults and expose configurable metadata in a
    follow-up phase if needed.

## Migration Plan

1. Extend OpenSpec requirements for numerical interface coupling behavior.
2. Implement deterministic interface segment pairing and coupling accumulation
   in IGA assembly.
3. Add regression tests for operator deltas, orientation behavior, and pairing
   validation errors.
4. Update docs and tracking artifacts.
