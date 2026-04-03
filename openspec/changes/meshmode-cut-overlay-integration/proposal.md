## Why

CUTKIT already produces topology-validated trimmed-domain integration data, but there is no first-class bridge for applying those results as overlays on meshmode discretizations. Teams currently reimplement this glue logic ad hoc, which makes solver handoff brittle and inconsistent.

Adding an explicit meshmode cut-overlay integration capability now closes a major downstream gap between CUTKIT outputs and production solver assembly flows.

## What Changes

- Add a meshmode-oriented cut-overlay API that maps CUTKIT clipped/cut-cell outputs onto meshmode element groups and quadrature/evaluation points.
- Define stable contracts for overlay payloads (indices, weights, geometry metadata, and status/failure states) so solver code can consume them predictably.
- Add validation and diagnostics for common mismatch scenarios (element-id drift, orientation mismatch, invalid/empty overlay regions).
- Add tests and docs covering nominal workflows and key failure semantics for meshmode consumers.

## Roadmap Position

This change is the interoperability foundation for downstream solver assembly
work:

- It MUST land before DG-SEM backend assembly integration in
  `ufl-iga-and-grudge-dgsem-assembly`.
- It SHOULD define a stable, versioned payload contract so additional backends
  can consume the same overlay data without contract churn.

## Capabilities

### New Capabilities

- `meshmode-cut-overlay`: Provide a supported integration path from CUTKIT trimmed/cut-cell data to meshmode-ready overlay structures, including deterministic status reporting and diagnostics.

### Modified Capabilities

- None.

## Impact

- Affected code: likely new/expanded modules in `src/cutkit/io/` and/or `src/cutkit/quadrature/` for meshmode adapters and overlay assembly.
- APIs: new public overlay construction/translation API and related result/status objects.
- Dependencies/systems: runtime compatibility expectations with meshmode data layouts; updates to docs and integration tests.
