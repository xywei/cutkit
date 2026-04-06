## Context

The vector `value_shape` MVP adds deterministic shape metadata and backend
capability gating, but DG-SEM lowering still treats vector forms as scalar-like
plans with no component dimension in lowering entries.

Phase 2 introduces deterministic component-aware vector lowering semantics while
keeping scope constrained to rank-1 vectors and preserving strict/permissive
diagnostic behavior.

## Goals / Non-Goals

**Goals**

- Emit component-aware DG-SEM lowering entries for rank-1 vectors.
- Define deterministic vector source conventions for mapping payload parsing and
  DG-SEM lowering signatures.
- Tighten parse-time vector source and shape consistency checks.
- Keep scalar behavior backward compatible in payload strings and regression
  expectations.

**Non-Goals**

- Rank-2 tensor execution semantics.
- Full vector IGA assembly execution.
- NURBS or multipatch implementation.

## Decisions

1. Add optional `component` metadata to DG lowering entries.
   - Rationale: preserves existing scalar payload shape while making vector
     semantics explicit and deterministic.

2. Use a broadcast-by-default rule for vector source lowering.
   - Scalar source term on vector forms applies to each component unless a
     component tuple is explicitly provided.
   - Rationale: deterministic and minimally disruptive for existing scalar
     source payloads.

3. Support mapping payload vector source tuples for `source` terms.
   - Tuple/list source values are normalized to component tuples.
   - Length must match `value_shape[0]`.
   - Rationale: explicit component source values are needed for deterministic
     vector lowering tests.

4. Keep scalar payload string formats unchanged.
   - Rationale: avoid regressions in existing scalar DG tests and docs.

## Risks / Trade-offs

- [Risk] vector source tuple parsing could blur scalar-vs-vector semantics.
  - Mitigation: strict shape-length validation and explicit error messages.
- [Risk] component-aware lowering could alter ordering unexpectedly.
  - Mitigation: deterministic sort keys include component index.

## Migration Plan

1. Add parser validation for vector source tuple normalization and shape checks.
2. Add DG lowering component fields and vector expansion logic.
3. Add regression tests for component-aware lowering and vector source
   signatures.
4. Update docs and checklist tracking.
