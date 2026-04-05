# Form DSL Vector-Valued MVP

## Objective

Start the post-archive vector-form roadmap by enabling an initial vector-valued
form slice in the shared formdsl path without regressing deterministic behavior.

## Scope

- Extend method-neutral IR with explicit value-shape metadata.
- Allow parser ingestion of vector-valued form payloads and UFL-like arguments.
- Gate backend support by shape capability (`iga` scalar-only,
  `dgsem` scalar + rank-1 vector).
- Propagate shape metadata into DG-SEM lowering payloads.
- Add deterministic tests/docs for vector parsing and capability behavior.

## Non-Goals

- Full vector/tensor operator assembly in IGA backend.
- Rank-2 tensor-form execution in DG-SEM backend.
- NURBS or multipatch implementation work.

## Acceptance Criteria

- `WeakFormIR` carries explicit `value_shape` metadata.
- Vector-form payloads can parse deterministically when shape is explicit.
- UFL-like vector argument shapes are represented in parsed IR.
- `iga` rejects unsupported non-scalar shapes with deterministic capability
  diagnostics.
- `dgsem` accepts rank-1 vector shapes and forwards `value_shape` in lowering
  results.
- Tests/docs are updated and CI passes.

## Implementation Checklist

- [x] Add `value_shape` to formdsl IR and parser normalization.
- [x] Add backend value-shape capability diagnostics.
- [x] Thread value-shape into DG-SEM lowering payload.
- [x] Add regression tests for mapping, WeakFormIR, UFL-like vector parsing,
      and backend capability behavior.
- [x] Update support docs and OpenSpec artifacts.
- [ ] Merge PR with green CI.

## Risks / Open Questions

- Permissive-mode behavior for unsupported shapes must remain deterministic and
  avoid silent semantic drift.
- UFL shape extraction can vary across element wrappers; parser diagnostics
  should stay actionable when shape metadata is incomplete.
