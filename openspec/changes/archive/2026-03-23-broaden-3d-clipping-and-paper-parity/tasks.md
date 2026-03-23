## 1. Axis-General 3D Clipping and Integration

- [x] 1.1 Add axis-general cell classification API and y/z wrapper functions in `src/cutkit/clipping/cartesian3d.py`.
- [x] 1.2 Add axis-general Cartesian graph-surface integration wrapper in `src/cutkit/quadrature/folded3d.py` and export it.
- [x] 1.3 Add clipping and quadrature regression tests for x/y/z behavior.

## 2. Section 6.2 3D Diagnostics

- [x] 2.1 Add monotonicity diagnostics fields to 3D grid experiment result rows.
- [x] 2.2 Update serialization and script printing to surface diagnostics.
- [x] 2.3 Add tests for monotone/non-monotone detection behavior.

## 3. Full Antolin-Paper Fixture Coverage

- [x] 3.1 Generate and commit `antolin-paper-polygonized-full.json`.
- [x] 3.2 Replace CAD paper fixture with full-scope placeholder semantics (`antolin-paper-cad-native-full.json`).
- [x] 3.3 Update fixture docs and parity tests to the full-scope matrix.

## 4. Documentation and Validation

- [x] 4.1 Document singular-quadrature status (paper scope vs QBFEM deferral) in follow-up docs.
- [x] 4.2 Run focused test suites for clipping/quadrature/evals/parity.
- [x] 4.3 Run `make dev`.
