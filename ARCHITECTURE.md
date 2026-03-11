# ARCHITECTURE

This document defines the target architecture for CUTKIT.

Current code is intentionally small. The structure below is the direction we
will enforce as functionality grows.

## Purpose

CUTKIT provides a topology-aware geometry and integration layer for trimmed
domains, designed to work with `meshmode`, `modepy`, and boundary-integral
workflows.

## Design Goals

- Keep geometry handling explicit and testable.
- Separate topology, clipping, and quadrature concerns.
- Preserve predictable data flow from CAD trims to integration outputs.
- Make behavior legible to both human and agent contributors.

## Target Package Layout

```text
src/cutkit/
  geometry/      # patch maps, Jacobians, boundary curves, evaluators
  topology/      # loop orientation, nesting, seam and connectivity logic
  clipping/      # inside/outside/cut classification and cut-cell extraction
  quadrature/    # cut-cell moments, rule generation, integration drivers
  diagnostics/   # quality metrics, invariants, debug exports
  io/            # optional adapters for external formats/tooling
```

## Dependency Direction

Dependencies should move forward only:

`geometry -> topology -> clipping -> quadrature`

Additional rules:

- `diagnostics` may depend on any layer for read-only analysis.
- `io` may depend on any layer, but core layers must not depend on `io`.
- No reverse dependencies across core layers.

## Data Flow

1. Geometry adapters expose patch parameterizations and trim curves.
2. Topology normalizes loops (outer/hole orientation, nesting, seam handling).
3. Clipping computes active regions and cut cells in parameter space.
4. Quadrature evaluates integrals on resulting cut panels/cells.
5. Diagnostics reports quality and failure modes.

## Testing Expectations

- Unit tests for each layer with deterministic fixtures.
- Cross-layer integration tests for representative trimmed cases.
- Regression fixtures for slivers, holes, near-degenerate cuts, and seam cases.

## Mechanical Enforcement

- `scripts/check_architecture.py` validates layer dependency direction.
- `tests/test_architecture_contract.py` fails when architecture rules are broken.
- CI runs these checks via the standard quality gate.

## Notes

This file captures architecture intent. If code and architecture diverge,
update both code and this document in the same change.
