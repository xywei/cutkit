# Analytic Local Residual Moments

## Objective

Test the simplest analytic/asymptotic local-residual approximation for the 2D log
Ewald split: full-space Taylor moments of the compact residual. Use it for both
interior windows and trim-intersecting windows first, then measure where the
boundary error appears.

## Scope

- Add a full-space analytic local residual estimator to the near-field split
  sweep.
- Compare analytic local residual values against high-order folded local
  residual references.
- Report interior, boundary-near, exterior-near, and vertex-near target errors.
- Run the comparison on `ipa` and update the report.

## Non-Goals

- Implement boundary-aware moments.
- Implement curved CAD fixtures.
- Replace direct local residual references.

## Acceptance Criteria

- [x] Report identifies when full-space analytic moments are accurate enough and
  when trim boundaries dominate the error.
- [x] `make dev` passes before handoff.

## Checklist

- [x] Add analytic local estimator and report fields.
- [x] Run the comparison on `ipa`.
- [x] Update docs with conclusions.
- [x] Validate with `make dev`.

## Outcomes

- The leading full-space moment `sigma^2 rho(x)/4` works for interior windows
  when the target is well away from the trim. At `sigma=0.08`, interior analytic
  local relative errors ranged from `2.6e-6` to `6.4e-4`.
- The same full-space moment fails for trim-intersecting windows. Median
  trim-near analytic local relative errors were `0.31`, `0.79`, and `1.41` for
  `sigma=0.08`, `0.16`, and `0.32`, respectively.
- Exterior-near targets are especially bad because the full-space moment includes
  material outside the source region.
- The next step is a window/boundary classifier: interior windows use analytic
  moments; trim-intersecting windows need boundary-aware corrections.

## Validation

Ran `make dev` successfully after implementation and report updates.
