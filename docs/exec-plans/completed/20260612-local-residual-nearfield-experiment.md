# Local Residual Near-Field Experiment

## Objective

Measure the compact singular residual from the DMK-style 2D log split directly,
to decide whether ordinary folded quadrature is adequate or whether analytic or
boundary-aware precomputed handling is needed.

## Scope

- Extend the near-field split sweep with local-residual folded quadrature values.
- Report full, smooth, local, and reconstructed errors against high-order
  references.
- Run the residual-inclusive sweep on `ipa`.
- Update the near-field DMK report with conclusions.

## Non-Goals

- Implement analytic residual moments.
- Implement boundary-aware precomputed correction tables.
- Add curved CAD fan fixtures.

## Acceptance Criteria

- [x] Residual-inclusive report identifies whether direct local folded quadrature
  is the new bottleneck.
- [x] Results include the same target and seed cases as the smooth split sweep.
- [x] `make dev` passes before handoff.

## Checklist

- [x] Add local residual measurements to experiment dataclasses and CLI tables.
- [x] Run the sweep on `ipa`.
- [x] Update reports and notes.
- [x] Validate with `make dev`.

## Outcomes

- Direct ordinary folded quadrature of the compact residual is not competitive as
  the primary method.
- At `order=24`, smooth-part median relative errors are near `1e-7`, while local
  residual median relative errors range from `4.2e-4` to `8.9e-3` depending on
  `sigma`.
- Reconstructing `smooth + local` with direct local quadrature reproduces the
  direct full-log error, confirming that the residual is the remaining hard part.
- The next implementation choice should be a special local residual method:
  analytic/asymptotic moments for interior windows or boundary-aware precomputed
  folded-fan corrections for trim-intersecting windows.

## Validation

Ran `make dev` successfully after the implementation and report updates.
