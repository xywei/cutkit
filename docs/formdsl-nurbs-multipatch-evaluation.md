# Form DSL NURBS + Multipatch Evaluation

This note captures Phase 3 evaluation findings for extending formdsl assembly
beyond the current scalar B-spline single-patch slice.

## Current Coverage

- Form parsing and backend lowering are stable for scalar-space terms on the
  current IGA and DG-SEM paths.
- DG-SEM lowering consumes explicit meshmode overlay contracts and now includes
  deterministic flux-family behavior for SIPG, central, and upwind.
- Form parsing now carries explicit `value_shape` metadata and supports a
  constrained vector MVP (`dgsem`: rank-1 vectors; `iga`: scalar-only gated).
- Geometry-map capability semantics are explicit with `geometry_map` metadata:
  `iga` accepts `bspline` and single-patch `nurbs`, while `dgsem` remains
  `bspline`-only with deterministic `unsupported_geometry_map` diagnostics.

## Gap Assessment

### NURBS geometry mapping

Main gaps:

- No IR-level representation for rational weights beyond metadata selection.
- IGA backend still uses the existing numerical path for the NURBS MVP and does
  not yet add dedicated rational basis execution internals.
- DG-SEM NURBS geometry-map support is intentionally deferred.

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

1. Add dedicated rational basis execution internals for single-patch NURBS in
   IGA beyond metadata-level capability semantics.
2. Add multipatch identifiers and interface descriptors in IR, then introduce
   backend lowering for interface terms with orientation diagnostics.
3. Add shared parity fixtures for multipatch forms and keep strict/permissive
   behavior deterministic at each stage.

## Tracking

- Multipatch interface coupling archive:
  `openspec/changes/archive/2026-04-07-formdsl-nurbs-multipatch-interface-coupling/`
- Multipatch interface completed plan:
  `docs/exec-plans/completed/20260406-formdsl-nurbs-multipatch-interface-coupling.md`
- OpenSpec archive:
  `openspec/changes/archive/2026-04-05-ufl-iga-and-grudge-dgsem-assembly/`
- Completed plan:
  `docs/exec-plans/completed/20260402-ufl-iga-and-grudge-dgsem-assembly.md`
- NURBS geometry-map MVP archive:
  `openspec/changes/archive/2026-04-06-formdsl-nurbs-geometry-map-mvp/`
- NURBS geometry-map completed plan:
  `docs/exec-plans/completed/20260406-formdsl-nurbs-geometry-map-mvp.md`
