## 1. OpenSpec and Planning

- [x] 1.1 Add proposal/design/tasks/spec artifacts for signed source-cloud export.
- [x] 1.2 Add/refresh execution plan in `docs/exec-plans/active/`.

## 2. Source-Cloud API

- [x] 2.1 Add typed signed source-cloud dataclasses for dimension-independent
  single and batch workflows (2D/3D).
- [x] 2.2 Add adapter API(s) that build source clouds from clipped 2D/3D regions
  and density functions.
- [x] 2.3 Expose backend-mode and deterministic ordering metadata.
- [x] 2.4 Implement one object-or-arrays normalization path for vectorized source-region inputs.

## 3. CAD/Quadrature Integration

- [x] 3.1 Wire source-cloud export through existing CAD box clipping pathways.
- [x] 3.2 Reuse folded 2D/3D quadrature rules without duplicating core kernels.
- [x] 3.3 Preserve per-box status semantics (`ok`, `empty`, `invalid_box`, `backend_error`).

## 4. Volumential Adapter Surface

- [x] 4.1 Add volumential-friendly materialization helpers (NumPy when available, pure-Python fallback).
- [x] 4.2 Add deterministic batching/flattening behavior documentation and examples.

## 5. Tests and Validation

- [x] 5.1 Add unit tests for sign preservation, ordering, and metadata.
- [x] 5.2 Add object-mode vs array-mode equivalence tests for matching source batches in 2D/3D.
- [x] 5.3 Add conservation/parity tests for constant and smooth density functions in 2D/3D.
- [x] 5.4 Run focused tests and `make dev`.
