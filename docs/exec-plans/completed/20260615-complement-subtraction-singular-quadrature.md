# Complement-Subtraction Singular Quadrature

## Objective

Record and validate the strategy

```text
int_{Omega cap B} K(x,y) p(y) dy = int_B K(x,y) p(y) dy - int_{B \ Omega} K(x,y) p(y) dy
```

for cut-box near-field moments, using existing full-box singular tables for the
first term and folded decomposition for the smooth complement term.

## Scope

- Document the mathematical route and validity conditions.
- Identify when the complement integral is smooth and when it still needs a
  singular/near-singular fallback.
- Connect the route to existing full-box moment tables and folded fan pieces.
- Keep this as a design note first; production implementation comes after the
  classifier/table API is settled.

## Acceptance Criteria

- `docs/nearfield-template-experiments.md` explains complement subtraction as a
  candidate cut-box singular quadrature route.
- `docs/nearfield-local-model-catalogue.md` records the smoothness conditions,
  endpoint-node caveats, and fallback cases.
- `docs/index.md` remains current if a new standalone document is added.
- `make dev` passes before handoff.

## Checklist

- [x] Add complement-subtraction derivation and algorithm sketch.
- [x] Record smooth-complement conditions and failure modes.
- [x] Validate documentation with `make dev`.
- [x] Move this plan to `docs/exec-plans/completed/` with outcomes.

## Outcomes

- Added the full-box-minus-complement identity to
  `docs/nearfield-template-experiments.md` as a candidate cut-box singular
  quadrature route.
- Recorded the key condition: the complement folded integral is smooth only when
  the target is separated from `B \ Omega`.
- Added routing rules and the open-quadrature caveat to
  `docs/nearfield-local-model-catalogue.md`, including when to fall back to
  boundary moments, wedge/cone models, refinement, or target-centered Duffy.
- Validation passed with `make dev`.
