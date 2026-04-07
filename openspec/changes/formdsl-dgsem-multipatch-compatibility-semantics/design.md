## Context

Multipatch parsing and IGA execution are implemented, including per-interface
controls. For backend `dgsem`, multipatch remains unsupported by design, but
diagnostics currently provide only a single generic capability error.

This phase introduces deterministic DG-SEM compatibility diagnostics so callers
can understand exactly which multipatch semantics block lowering.

## Goals / Non-Goals

**Goals**

- Preserve strict unsupported behavior for DG-SEM multipatch requests.
- Add deterministic compatibility diagnostics in permissive mode.
- Distinguish base unsupported descriptor, orientation variants, and
  per-interface penalty controls.
- Keep diagnostics stable and easy to assert in tests.

**Non-Goals**

- DG-SEM multipatch execution.
- Changes to IGA multipatch behavior.
- Flux-family or trace-operator redesign.

## Decisions

1. Keep `unsupported_multipatch_interface` as the primary strict failure code.
   - Rationale: avoids compatibility break for existing strict-mode callers.

2. Append additional DG-SEM compatibility diagnostics in deterministic order.
   - Rationale: permissive users get actionable context while retaining stable
     payload semantics.

3. Detect unsupported descriptor features directly from IR multipatch
   interfaces (orientation and penalty controls).
   - Rationale: keeps diagnostics backend-agnostic but DG-SEM scoped.

## Risks / Trade-offs

- [Risk] Additional diagnostics may be noisy for simple unsupported requests.
  - Mitigation: keep code set compact and deterministic.
- [Risk] Future DG-SEM execution phases may require code deprecation.
  - Mitigation: use clearly scoped `dgsem_*` diagnostic codes.

## Migration Plan

1. Extend OpenSpec requirements for DG-SEM multipatch compatibility diagnostics.
2. Implement deterministic diagnostic generation in capability checks.
3. Add strict/permissive regression assertions and update docs.
