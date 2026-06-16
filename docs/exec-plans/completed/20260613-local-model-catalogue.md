# Local Model Catalogue

## Objective

Record the local analytic/asymptotic model catalogue for compact near-field
residual corrections in 2D and 3D.

## Scope

- Catalog one-feature residual windows: interiors, smooth boundaries, corners,
  faces, edges, and vertices.
- Derive the common Taylor/modal moment expansion used by these models.
- Record the 2D log residual radial moments used by the current experiments.
- Link the catalogue from the near-field experiment documentation.

## Acceptance Criteria

- The catalogue states the routing rule that each residual support should see at
  most one geometric singular feature.
- 2D and 3D local models include moment formulas and leading terms where known.
- The main near-field docs point to the catalogue as the next design reference.
- Documentation validation passes.

## Checklist

- [x] Add local model catalogue.
- [x] Add common Taylor/modal expansion.
- [x] Add 2D log residual moment derivation.
- [x] Link from docs index and near-field reports.
- [x] Run validation.

## Outcome

Added `docs/nearfield-local-model-catalogue.md`, covering the one-feature local
models and their expansion structure. The next implementation step is a
window/feature classifier followed by the 2D straight-boundary half-plane moment
experiment.
