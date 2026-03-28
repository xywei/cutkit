## 1. OpenSpec and Planning

- [x] 1.1 Add proposal/design/tasks/spec artifacts for local near-field Galerkin correction.
- [x] 1.2 Add/refresh execution plan in `docs/exec-plans/active/`.

## 2. Local Box + Trace Interfaces

- [x] 2.1 Add typed local-box configuration/result dataclasses.
- [x] 2.2 Add boundary-trace sampling API for far-field values on local box boundaries.
- [x] 2.3 Add explicit composition metadata for far/near reconciliation.
- [x] 2.4 Implement object-or-arrays normalization for local boxes, source sets, and target batches.

## 3. Local Galerkin Solver Kernels (2D/3D)

- [x] 3.1 Add tensor-product B-spline local assembly on axis-aligned boxes in 2D/3D.
- [x] 3.2 Add strong Dirichlet boundary imposition from sampled boundary traces.
- [x] 3.3 Add vectorized sparse-system export (matrix/RHS + per-system pointers and metadata).
- [x] 3.4 Add vectorized matrix-free local-operator export (matvec + RHS + metadata).
- [x] 3.5 Ensure assembled and matrix-free modes are algebraically equivalent within tolerance.
- [x] 3.6 Add optional CUTKIT local solve helper with deterministic diagnostics (iterations, residual, free DOFs).
- [x] 3.7 Add compact-support load coupling: assemble RHS via folded support quadrature against box basis/test functions.

## 4. Near-Field Evaluation Workflow

- [x] 4.1 Add restricted-source workflow support for self/list1/list3/list4 style sets.
- [x] 4.2 Add optional target-evaluation API for solved local corrections.
- [x] 4.3 Add explicit anti-double-counting composition guidance in API docs.

## 5. Tests and Validation

- [x] 5.1 Add manufactured-solution and boxed-domain local-solve tests in 2D/3D.
- [x] 5.2 Add object-mode vs array-mode equivalence tests for local correction APIs in 2D/3D.
- [x] 5.3 Add assembled-vs-matrix-free equivalence tests for operator application and solved corrections in 2D/3D.
- [x] 5.4 Add far+near composition regression tests against high-order references.
- [x] 5.5 Add regression tests for compact-support-inside-box forcing assembly consistency.
- [x] 5.6 Run focused tests and `make dev`.
