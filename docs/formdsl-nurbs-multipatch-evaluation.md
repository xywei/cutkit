# Form DSL NURBS + Multipatch Evaluation

This note captures Phase 3 evaluation findings for extending formdsl assembly
beyond the current scalar B-spline single-patch slice.

## Current Coverage

- Form parsing and backend lowering are stable for scalar-space terms on the
  current IGA and DG-SEM paths.
- DG-SEM lowering consumes explicit meshmode overlay contracts and now includes
  deterministic flux-family behavior for SIPG, central, and upwind.
- Form parsing now rejects vector/tensor-valued spaces so unsupported geometry
  and shape combinations do not silently pass through.

## Gap Assessment

### NURBS geometry mapping

Main gaps:

- No IR-level representation for rational weights or geometry-map metadata.
- IGA backend currently assumes polynomial/B-spline-style basis and geometry
  evaluation in assembly loops.
- No deterministic diagnostics yet for unsupported rational mapping requests.

Implication:

- Enabling NURBS without explicit geometry-map metadata risks hidden quadrature
  mismatch and non-reproducible errors.

### Multipatch support

Main gaps:

- No patch-level identifiers in form IR or backend lowering payloads.
- No interface-term model for patch coupling (trace/interface continuity,
  orientation, and jump/average conventions across patch boundaries).
- No parity/benchmark fixtures that exercise patch interfaces.

Implication:

- Multipatch enablement requires explicit patch-interface semantics before it
  can be considered deterministic.

## Recommended Rollout

1. Add geometry-map metadata to IR with deterministic parse/lowering diagnostics
   for unsupported map types (start with `bspline`, then add `nurbs`).
2. Land single-patch NURBS IGA lowering first, with manufactured-solution
   regression coverage and parity thresholds.
3. Add multipatch identifiers and interface descriptors in IR, then introduce
   backend lowering for interface terms with orientation diagnostics.
4. Add shared parity fixtures for multipatch forms and keep strict/permissive
   behavior deterministic at each stage.

## Tracking

- OpenSpec change: `openspec/changes/ufl-iga-and-grudge-dgsem-assembly/`
- Active plan: `docs/exec-plans/active/20260402-ufl-iga-and-grudge-dgsem-assembly.md`
