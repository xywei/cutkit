## 1. OpenSpec and Planning

- [x] 1.1 Add proposal/design/tasks/spec artifacts for CAD object-or-arrays interface.
- [x] 1.2 Add execution plan in `docs/exec-plans/active/`.

## 2. Public CAD Facade

- [x] 2.1 Add consumer-facing CAD facade module with `CadSession`, `CadFace2D`, and `CadSolid3D` handles.
- [x] 2.2 Add typed box value objects (`Box2D`, `Box3D`) and batch containers (`Box2DArray`, `Box3DArray`).
- [x] 2.3 Export new facade APIs through stable package entry points.

## 3. Object-Or-Arrays Batch Semantics

- [x] 3.1 Implement one normalization path for object-mode and array-mode box inputs.
- [x] 3.2 Implement deterministic broadcasting + flatten/reshape ordering.
- [x] 3.3 Add strict/non-strict validation behavior and per-box status reporting.

## 4. Clipping and Folded Integration Workflows

- [x] 4.1 Add 2D clip helpers for one/many boxes that return panel-compatible outputs.
- [x] 4.2 Add 3D clip helpers for one/many boxes that return triangulation-compatible outputs.
- [x] 4.3 Add folded quadrature convenience APIs for one/many boxes in 2D and 3D.

## 5. Tests and Documentation

- [x] 5.1 Add unit tests for batch input normalization, broadcasting, and statuses.
- [x] 5.2 Add object-vs-array equivalence tests for clipping and integration outputs.
- [x] 5.3 Add docs/README usage examples for single-box and batch workflows.

## 6. Validation

- [x] 6.1 Run focused tests for new CAD facade and batch APIs.
- [x] 6.2 Run `make dev`.
