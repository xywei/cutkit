## Context

`cutkit.formdsl` currently parses/scaffolds scalar forms and lowers them to IGA
assembly and DG-SEM lowering payloads. Vector-form expansion was previously
captured as a backlog evaluation item; this change starts implementation with a
constrained MVP.

## Goals / Non-Goals

**Goals**

- Add explicit value-shape metadata to method-neutral IR.
- Support deterministic vector-valued parsing for mapping and UFL-like inputs.
- Enforce backend shape capability diagnostics (`iga` scalar-only;
  `dgsem` scalar + rank-1 vectors).
- Surface shape metadata in DG-SEM lowering payloads.

**Non-Goals**

- Rank-2 tensor execution support.
- Vector/tensor IGA matrix assembly.
- Flux-family redesign or multipatch/NURBS implementation.

## Decisions

1. Add `value_shape: tuple[int, ...]` to `WeakFormIR`.
   - Rationale: preserves backend-neutral shape intent without introducing
     backend-specific vector semantics in the parser.

2. Require explicit `value_shape` in mapping payloads when vector/tensor labels
   are used.
   - Rationale: avoids brittle implicit dimension inference from free-form space
     strings.

3. Parse UFL-like argument shapes directly from argument metadata.
   - Rationale: UFL inputs can carry shape information that should flow into IR.

4. Keep `iga` scalar-only for this MVP and report deterministic
   `unsupported_value_shape` diagnostics.
   - Rationale: vector IGA assembly requires block-operator semantics outside
     this slice.

5. Allow rank-1 vector shapes in `dgsem` lowering and include shape metadata in
   lowering payloads.
   - Rationale: DG lowering payloads are operator-plan oriented and can carry
     shape metadata without requiring full solver-side vector execution changes.

## Risks / Trade-offs

- [Risk] permissive mode could mask unsupported-shape semantics.
  - Mitigation: emit deterministic shape diagnostics and keep strict-mode
    behavior as default.
- [Risk] UFL shape extraction variability across wrappers.
  - Mitigation: treat invalid/inconsistent shapes as deterministic parse errors.

## Migration Plan

1. Land IR/parser/capability shape metadata changes with regression tests.
2. Land DG-SEM payload shape threading and backend behavior tests.
3. Update backend support docs and OpenSpec/task tracking.
