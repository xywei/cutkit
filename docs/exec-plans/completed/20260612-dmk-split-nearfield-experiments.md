# DMK Split Near-Field Experiments

## Objective

Run a first numerical check of the preferred near-field direction: split the 2D
log kernel into a smooth Ewald/heat-kernel part plus a localized singular
residual, evaluate the smooth part with folded fan quadrature, and measure when
the residual may require boundary-aware handling.

## Scope

- Extend the existing straight-fan near-field prototype with a 2D log Ewald split.
- Compare ordinary folded quadrature convergence for the full kernel versus the
  smoothed kernel.
- Compare current robust interior-style seeds against a simple node-barycenter
  seed on CAD-like fan fixtures.
- Run the numerical sweep on `ipa` and summarize results in
  `docs/nearfield-template-experiments.md` and
  `docs/nearfield-dmk-split-report.md`.

## Non-Goals

- Implement the final boundary-aware correction tables.
- Add a production near-field API.
- Replace existing folded decomposition seed policy.

## Acceptance Criteria

- [x] Experiment script emits machine-readable and Markdown summaries.
- [x] Results include interior, boundary-near, and exterior-near target cases.
- [x] Report states whether the smooth split improves quadrature convergence and
  whether seed choice materially changes fan quality in the fixtures.
- [x] `make dev` passes before handoff.

## Checklist

- [x] Add Ewald-split utilities and experiment dataclasses.
- [x] Add CLI options for the DMK-style sweep and report output.
- [x] Run the sweep on `ipa`.
- [x] Add a concise report to the near-field notes.
- [x] Validate with `make dev`.

## Outcomes

- The 2D log Ewald split made the smoothed folded-quadrature path much easier:
  at `order=24`, smooth-part errors were at least about `70x` smaller than direct
  full-log errors across the tested cases.
- Median improvement was `1.8e3`, `6.6e2`, and `1.4e3` for `sigma` values
  `0.08`, `0.16`, and `0.32`, respectively.
- Boundary-near targets also benefited strongly, so the smooth remainder is not
  the bottleneck in these fixtures.
- The node-barycenter seed is viable but not uniformly better than the current
  robust interior anchor; seed choice should remain a measured quality parameter.
- The next unresolved issue is the localized singular residual when its window
  intersects a rigid trim boundary.

## Validation

Ran `make dev` successfully after the implementation and report updates.

## Risks

- The straight-fan fixtures may understate CAD curvature effects.
- Boundary-aware residual behavior requires a later local-residual experiment with
  curved or trim-intersecting fixtures to be conclusive.
