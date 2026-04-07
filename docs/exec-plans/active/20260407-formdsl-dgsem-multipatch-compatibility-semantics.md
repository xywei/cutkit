# Form DSL DG-SEM Multipatch Compatibility Semantics

## Objective

Add deterministic compatibility diagnostics for DG-SEM multipatch requests while
keeping DG-SEM multipatch execution unsupported.

## Scope

- Preserve strict fail-fast behavior for multipatch on backend `dgsem`.
- Add deterministic permissive diagnostics describing unsupported multipatch
  semantics.
- Cover orientation variants and per-interface penalty controls.
- Add tests and docs updates for diagnostic stability.

## Non-Goals

- DG-SEM multipatch execution.
- Changes to IGA multipatch execution semantics.
- New DG flux/operator execution paths.

## Acceptance Criteria

- Strict mode still raises `unsupported_multipatch_interface`.
- Permissive mode includes deterministic DG-SEM compatibility diagnostics.
- Orientation and per-interface penalty controls each produce stable
  compatibility diagnostics.
- Regression tests and docs are updated.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks artifacts.
- [x] Implement DG-SEM compatibility diagnostics for multipatch descriptors.
- [x] Add strict/permissive regression tests.
- [x] Update docs and progress tracking.

## Risks / Open Questions

- Diagnostic code set should stay minimal and deterministic to avoid future
  churn when DG-SEM multipatch execution is introduced.
