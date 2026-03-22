## Context

CUTKIT currently has architecture boundaries and a baseline cut-panel evaluation harness, but no implementation in the quadrature layer. This change introduces the first folded-decomposition implementation while keeping dependency direction explicit: `geometry -> topology -> clipping -> quadrature`.

The target is a small and testable MVP for 2D polygonized trimmed panels that can later be consumed by downstream solvers via adapters.

## Goals / Non-Goals

**Goals:**
- Implement robust folded decomposition for 2D polygonized trimmed panels.
- Generate reusable quadrature nodes and weights for smooth integrands.
- Preserve outer-loop and hole semantics via signed decomposition.
- Provide diagnostics for area consistency and low-order polynomial moments.
- Keep APIs deterministic and narrow for integration and testing.

**Non-Goals:**
- 3D curved-polyhedron folded decomposition.
- Direct NURBS/B-rep kernel integration.
- Singular or near-singular kernel-specialized quadrature.
- Direct `volumential` integration in this change.

## Decisions

1. Add explicit 2D panel data structures in `geometry`.
   - Rationale: Keep loop ownership and panel representation stable and type-checked.
   - Alternatives considered: Reusing eval-only structures in `cutkit.evals` was rejected because it mixes test harness types with core APIs.

2. Normalize loop orientation in `topology` before decomposition.
   - Rationale: Outer=ccw and holes=cw gives deterministic signs and simpler validation.
   - Alternatives considered: Deferring orientation handling to quadrature was rejected because it couples topology concerns to integration code.

3. Build folded decomposition from an interior anchor to signed fan triangles.
   - Rationale: Minimal algorithmic core for MVP, easy to verify by area reconstruction and moments.
   - Alternatives considered: General polygon triangulation was rejected for MVP because it does not directly expose folded signed contributions.

4. Use deterministic triangle quadrature mapping and aggregate at panel level.
   - Rationale: Keeps rule generation transparent and testable while supporting hole cancellation.
   - Alternatives considered: Black-box polygon cubature was rejected because diagnostics and decomposition semantics are less explicit.

5. Add moment diagnostics in a dedicated diagnostics module.
   - Rationale: Quality metrics should remain independent of rule generation internals.

## Risks / Trade-offs

- Anchor point selection may fail for near-degenerate loops -> add fallback search and explicit validity checks.
- Thin geometries can amplify floating-point cancellation -> expose tolerances and report diagnostics in eval output.
- Restricting v0 to smooth integrands accelerates delivery -> singular-kernel workflows are intentionally deferred to follow-up changes.

## Migration Plan

No runtime migration is required because this introduces new capabilities only. Existing APIs remain unchanged.

## Open Questions

- Should v1 prioritize 3D folded decomposition or singular-kernel-aware 2D extensions first?
- What rule export shape best matches the first downstream adapter (`volumential` or another consumer)?
