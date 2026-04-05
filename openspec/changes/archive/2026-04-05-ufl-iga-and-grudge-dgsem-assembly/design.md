## Context

CUTKIT currently provides geometry-aware quadrature and solver-oriented assembly
paths, including local spline Galerkin operators and meshmode-oriented overlay
planning. However, weak form expression is backend-specific and duplicated
across workflows.

Adopting UFL as a form DSL can improve user ergonomics and consistency, but UFL
alone is not an assembler. CUTKIT therefore needs a lowering layer that
translates UFL forms into backend-ready integration kernels for both smooth IGA
assembly and DG-SEM assembly through meshmode+grudge.

## Goals / Non-Goals

**Goals**

- Enable UFL-authored forms for CUTKIT trimmed-domain assembly.
- Support one form description with backend selection: `iga` and `dgsem`.
- Preserve deterministic status/error reporting and strict/permissive behavior.
- Keep CAD-trimmed quadrature as the source of geometric integration truth.

**Non-Goals**

- Replacing grudge internal discretization/trace APIs.
- Full UFL language coverage in first iteration.
- Distributed-memory solver orchestration redesign.
- Broad multiphysics coupling in the first release.

## Decisions

1. Introduce a method-neutral weak-form IR between UFL parsing and backend
   assembly.
   - Rationale: isolates frontend syntax from backend-specific implementation
     constraints.

2. Implement additive optional dependency handling for `ufl`.
   - Rationale: avoid making UFL mandatory for users who rely on existing API
     entrypoints.

3. Treat IGA and DG-SEM as separate backends sharing form IR and diagnostics.
   - Rationale: smooth-space and discontinuous-space assembly needs diverge,
     especially around traces/fluxes and continuity assumptions.

4. Require explicit backend capability checks during lowering.
   - Rationale: some forms/terms may be valid in one backend and unsupported in
     another; diagnostics must be deterministic and actionable.

5. Make DG-SEM lowering explicitly dependent on meshmode overlay contracts.
   - Rationale: avoids ad hoc geometry/index translation logic in backend code.
   - Alternative considered: direct CUTKIT payload consumption in DG backend.
     Rejected to prevent layering violations and duplicated mapping logic.

## Risks / Trade-offs

- [Risk] UFL subset too narrow for user expectations.
  - Mitigation: define explicit supported-term matrix and clear diagnostics.
- [Risk] Backend parity drift over time.
  - Mitigation: add shared manufactured-solution parity tests and CI checks.
- [Risk] Complexity increase in lowering pipeline.
  - Mitigation: keep IR minimal and incremental; avoid premature generality.
- [Risk] DG-SEM backend mismatch with trimmed integration assumptions.
  - Mitigation: build on meshmode overlay contracts and validate orientation/
    mapping semantics in integration tests.

## Migration Plan

1. Land UFL adapter and IR as additive modules with no behavior changes to
   existing APIs.
2. Enable IGA backend for a small supported-form subset (Poisson/mass/reaction).
3. Enable DG-SEM backend lowering for the same subset using meshmode+grudge
   adapter contracts.
4. Add backend selection examples and parity benchmarks in docs.

## Phase Gates

### Phase 1 Gate: DSL + IR + IGA MVP

- Supported forms: scalar diffusion/mass/reaction only.
- Required outputs: deterministic IR diagnostics and IGA assembly payloads.
- Required validation: manufactured-solution correctness and `make dev` pass.

### Phase 2 Gate: DG-SEM backend MVP

- Prerequisite: `meshmode-cut-overlay` contract landed and validated.
- Supported forms: same subset as Phase 1.
- Required outputs: deterministic DG-SEM lowering diagnostics and backend
  payloads using overlay metadata.

### Phase 3 Gate: Expansion

- Candidate expansions: broader flux families, vector forms, NURBS mapping,
  multipatch terms.
- Expansion only after Phase 1/2 parity metrics stabilize.

Rollback strategy: keep legacy assembly entrypoints as default and gate new
form-driven path behind explicit backend/form APIs.

## Open Questions

- Should first release support only scalar forms, or include vector-valued forms
  from day one?
- Which flux families (central/upwind/SIPG variants) should be mandatory in the
  initial DG-SEM adapter?
- Should NURBS rational geometry mapping ship in the first slice, or follow
  B-spline-only parity validation?
