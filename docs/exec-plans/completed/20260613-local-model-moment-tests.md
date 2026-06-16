# Local Model Moment Tests

## Objective

Turn the 2D straight-feature local model catalogue into executable checks for the
log Ewald residual moments.

## Scope

- Add a radial moment helper for the 2D local log residual.
- Add a sector monomial moment helper for full-plane, half-plane, and wedge
  models at the local feature point.
- Test the helpers against known full-plane values and independent polar
  quadrature references.
- Add a practical curved cut-cell check using an exact rational quadratic trim
  and folded curve quadrature.
- Add an exact target-centered curved-boundary model with ray clipping and finite
  radial Ewald moments.
- Add a high-order Taylor graph boundary model and compare it with the exact
  circular boundary model.
- Add a precomputation-style interpolation check for high-order smooth-boundary
  moments.

## Acceptance Criteria

- Full-plane leading and second moments match closed-form values.
- Half-plane and wedge sector moments match direct numerical quadrature within
  the reference quadrature tolerance.
- On a curved cut-cell sample, the half-plane model beats the full-plane model
  for a target on the smooth trim.
- The exact curved-boundary model agrees under refinement to better than
  `1e-10` relative error.
- The Taylor boundary model reaches below `1e-10` relative error at sufficiently
  high geometry order for tested local windows.
- The precomputed table interpolation reaches below `1e-10` relative error on
  intermediate local-window samples.
- The near-field targeted tests and full validation pass.

## Checklist

- [x] Implement radial moment helper.
- [x] Implement sector monomial moment helper.
- [x] Add full-plane moment tests.
- [x] Add half-plane and wedge reference tests.
- [x] Add curved cut-cell practical test.
- [x] Add machine-precision curved-boundary model refinement test.
- [x] Add high-order Taylor boundary model convergence test.
- [x] Add precomputed boundary-table interpolation test.
- [x] Run full validation.

## Outcome

Added 2D log-residual moment helpers for straight local models and tests covering
full-plane, half-plane, and wedge sectors. The numerical reference uses a
log-radius polar quadrature to avoid direct endpoint integration of the
logarithmic singularity. Added a curved rational cut-cell experiment showing that
the half-plane model is only a leading diagnostic for a target on a smooth curved
trim; the full-plane moment incorrectly includes outside-domain mass, while
machine precision requires exact or high-order curved boundary ray clipping with
finite radial moments. The high-order Taylor graph model reaches the `1e-10`
relative target on the rational quarter-circle trim at order 8 for `sigma=0.02`
and at order 6 for `sigma=0.005, 0.01`. A first interpolation-table check over
the normalized boundary scale also reaches the `1e-10` target, while direct
online graph-strip quadrature is not accurate enough near the target endpoint.
