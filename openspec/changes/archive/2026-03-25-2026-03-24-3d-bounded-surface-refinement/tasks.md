## 1. Bounded Cartesian 3D Integration

- [x] 1.1 Add axis-general bounded graph-surface integration API in `src/cutkit/quadrature/folded3d.py`.
- [x] 1.2 Add x/y/z bounded wrapper APIs and export them via `src/cutkit/quadrature/__init__.py`.
- [x] 1.3 Add quadrature tests for bounded slab fractions, axis consistency, and invalid axis rejection.

## 2. Section 6.1.3 Side-Face Refinement

- [x] 2.1 Remove the `side_resolution == 1` restriction from `build_section_6_1_3_boundary_triangles`.
- [x] 2.2 Add eval regression tests for positive, seed-invariant signed volume with `side_resolution > 1`.

## 3. Docs and Validation

- [x] 3.1 Update docs to reflect new bounded 3D integration support and narrowed remaining 3D follow-ups.
- [x] 3.2 Run focused tests and `make dev`.

## 4. CAD-Native 3D Ingestion and Clipping

- [x] 4.1 Add OpenCascade 3D adapter module for solid ingestion and triangulated boundary extraction.
- [x] 4.2 Add axis-aligned box clipping helper for CAD solids and oriented boundary export.
- [x] 4.3 Add IO-level regression tests for unavailable-mode behavior and available-mode clipped volume reconstruction.

## 5. Follow-up Closure

- [x] 5.1 Update follow-up docs to remove unresolved 3D coverage gap language after CAD-native ingest/clip support lands.
- [x] 5.2 Re-run `make dev` after the CAD-native 3D adapter changes.
