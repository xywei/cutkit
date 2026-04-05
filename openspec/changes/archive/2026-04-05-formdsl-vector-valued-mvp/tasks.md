## 1. Vector IR + Parsing

- [x] 1.1 Add `value_shape` metadata to `WeakFormIR`.
- [x] 1.2 Update mapping/UFL parser paths to normalize and validate
      value-shape metadata.
- [x] 1.3 Add deterministic parse errors for missing/invalid vector shape input.

## 2. Backend Capability + Lowering

- [x] 2.1 Add backend capability checks for unsupported value shapes.
- [x] 2.2 Keep IGA scalar-only for this slice with deterministic capability
      diagnostics.
- [x] 2.3 Thread supported value-shape metadata into DG-SEM lowering payloads.

## 3. Validation + Docs

- [x] 3.1 Add regression tests for mapping/WeakFormIR/UFL vector-shape parsing.
- [x] 3.2 Add backend behavior tests for IGA gating and DG-SEM vector acceptance.
- [x] 3.3 Update support docs and execution-plan tracking.
