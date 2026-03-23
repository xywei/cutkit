## Context

The current repository has strong 2D folded-decomposition coverage, while 3D behavior is implemented in `cutkit.evals` as reproduction-specific helpers. This leaves a gap between architecture intent (`geometry -> topology -> clipping -> quadrature`) and 3D implementation placement, and it limits reuse of 3D folded quadrature outside Section 6 runners.

## Goals / Non-Goals

**Goals:**
- Move 3D folded decomposition primitives into core package layers.
- Define deterministic 3D seed and orientation handling semantics.
- Expose reusable 3D quadrature rule outputs and diagnostics.
- Keep Section 6.1.3 and 6.2 reproduction entry points working while migrating to core APIs.

**Non-Goals:**
- Implement singular or near-singular kernel quadrature in this change.
- Build a full production PDE solver stack.
- Replace the existing 2D folded APIs.

## Decisions

1. Introduce explicit 3D boundary and cell primitives in core modules.
   - Rationale: Shared types prevent eval-only drift and support testing at layer boundaries.
   - Alternatives considered: Keeping 3D structures private in `cutkit.evals` was rejected because it blocks reuse and architecture enforcement.

2. Use a boundary-first folded construction with seed-based signed cell contributions.
   - Rationale: Matches the current successful 3D reproduction path and keeps folded negative-Jacobian behavior explicit.
   - Alternatives considered: Full tetrahedralization-only workflows were rejected because they hide folded semantics needed for parity studies.

3. Add a dedicated `QuadratureRule3D` container and deterministic 3D rule assembly utilities.
   - Rationale: A stable output contract is needed for diagnostics, regression tests, and downstream adapters.
   - Alternatives considered: Reusing ad-hoc tuples in eval code was rejected because it is error-prone and hard to validate.

4. Move 3D clipping/classification logic into `cutkit.clipping` before eval integration.
   - Rationale: Keeps architecture direction consistent and avoids embedding mesh/cell logic directly in eval code.
   - Alternatives considered: Deferring clipping migration was rejected because it would keep the same layering gap.

5. Preserve existing reproduction entry points as thin adapters over new core APIs.
   - Rationale: Minimizes user disruption and allows incremental parity verification.
   - Alternatives considered: Breaking API replacement in one step was rejected to reduce migration risk.

## Risks / Trade-offs

- [Risk] Orientation handling across stitched boundary patches can produce sign mistakes. -> Mitigation: add orientation invariance tests and explicit outward-normal checks.
- [Risk] Folded-cell cancellation can increase floating-point sensitivity on thin regions. -> Mitigation: expose tolerances and add high-resolution regression fixtures.
- [Risk] 3D core migration may temporarily diverge from current eval outputs. -> Mitigation: run side-by-side parity checks during migration and gate cutover on bounded error deltas.

## Migration Plan

1. Add core 3D types and quadrature builders behind new APIs.
2. Implement adapter wrappers in existing 3D eval runners.
3. Compare new/core and current/eval outputs on Section 6 settings.
4. Switch eval runners to core paths once parity thresholds pass.
5. Remove superseded eval-private 3D implementation blocks.

## Open Questions

- Should the first solver-facing export target be `volumential` or a neutral interchange format?
- Do we need a separate seed-selection strategy for highly non-convex trimmed volumes in v1?
