# Paper-Complete Implementation Sequence

## Objective

Implement the three OpenSpec follow-up changes in dependency order to close the
remaining gap between CUTKIT and the folded-decomposition paper workflow.

## Scope

- Implement `folded-decomposition-3d-core` first as the foundational change.
- Implement `section6-parity-hardening` second, after core 3D APIs are in place.
- Begin `immersed-iga-poisson` scaffolding with benchmark-oriented interfaces.

## Non-Goals

- Completing every dense benchmark profile in a single pass.
- Introducing singular or near-singular kernel quadrature in this sequence.

## Acceptance Criteria

- New core 3D modules exist under architecture-aligned package layers.
- 3D eval runners consume core 3D APIs.
- Section 6 parity outputs are machine-readable and testable.
- Poisson benchmark scaffolding exists with explicit profile modes.
- Repository checks for touched areas pass.

## Implementation Checklist

- [x] Implement `folded-decomposition-3d-core` modules and refactor eval usage.
- [x] Add tests for new 3D core APIs and migration parity.
- [x] Implement `section6-parity-hardening` manifest schema and checker path.
- [x] Add parity fixtures and tolerance-driven regression tests.
- [x] Implement `immersed-iga-poisson` benchmark interfaces and quick-profile runner.
- [x] Run focused and full validation checks for the combined change set.

## Risks

- 3D folded migration can accidentally drift numerics in existing reproductions.
- CAD availability differences can complicate parity checks.
- Poisson benchmark dependency footprint may be heavier than current CI defaults.

## Final Outcome

- Status: merged.
- Delivered via: `https://github.com/xywei/cutkit/pull/7`
- Follow-ups: seam/degenerate corpus and remaining 3D parity gaps completed in
  `https://github.com/xywei/cutkit/pull/9` and
  `https://github.com/xywei/cutkit/pull/11`.
