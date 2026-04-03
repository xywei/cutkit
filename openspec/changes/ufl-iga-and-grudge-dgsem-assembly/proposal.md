## Why

CUTKIT can already assemble trimmed-domain spline operators and export
solver-facing payloads, but weak forms are still expressed through
implementation-specific assembly calls. This limits reusability across solver
styles and raises the cost of comparing IGA and DG-SEM formulations on the same
geometry and PDE setup.

We need one high-level form description path that can target:

- CUTKIT's smooth spline IGA assembly backend, and
- meshmode+grudge DG-SEM operator assembly,

while preserving CAD-trimmed quadrature and deterministic diagnostics.

## What Changes

- Add a UFL-based form DSL entrypoint for trimmed-domain system assembly.
- Add a method-neutral weak-form IR/lowering layer for CUTKIT assembly backends.
- Add an IGA backend that assembles spline/NURBS-style operators from the DSL.
- Add a meshmode+grudge DG-SEM backend adapter that lowers the same forms into
  DG operators and flux terms.
- Add deterministic backend capability checks and unsupported-form diagnostics.
- Add convergence/parity tests and docs for IGA vs DG-SEM assembly workflows.

## Roadmap Position

- Phase 1 (required first): UFL adapter + method-neutral IR + IGA backend for a
  minimal scalar subset.
- Phase 2 (depends on `meshmode-cut-overlay`): DG-SEM backend lowering through
  meshmode+grudge using explicit overlay contracts.
- Phase 3: broader term coverage, flux families, and optional NURBS extensions.

This change MUST consume (not bypass) the meshmode overlay contract so backend
integration logic stays layered and testable.

## Capabilities

### New Capabilities

- `ufl-iga-form-dsl`: UFL-authorable weak forms for CUTKIT trimmed-domain
  assembly workflows.
- `grudge-dgsem-assembly-adapter`: lower method-neutral forms to
  meshmode+grudge DG-SEM operators with explicit flux and trace handling.

### Modified Capabilities

- `meshmode-cut-overlay`: extend overlay usage from payload translation to
  backend assembly consumption for DG-SEM workflows.
- `immersed-poisson-galerkin-solver`: allow form-driven assembly path in
  addition to solver-specific benchmark entrypoints.

## Impact

- Affected code:
  - new DSL/lowering modules under `src/cutkit/`
  - IGA assembly integration updates in local spline assembly modules
  - new meshmode+grudge adapter modules for DG-SEM lowering
  - tests under `tests/` for DSL coverage and backend parity
  - docs updates for UFL usage and backend selection
- Dependency impact:
  - `ufl` as optional dependency for DSL mode
  - runtime integration assumptions with `meshmode` and `grudge` for DG backend
