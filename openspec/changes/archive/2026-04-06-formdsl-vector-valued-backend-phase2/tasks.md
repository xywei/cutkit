## 1. OpenSpec Artifacts

- [x] 1.1 Add proposal for vector backend phase 2.
- [x] 1.2 Add design and spec deltas for component-aware DG-SEM semantics.

## 2. Parser + Validation

- [x] 2.1 Support deterministic vector source tuple parsing in mapping payloads.
- [x] 2.2 Validate vector source tuple length against `value_shape`.

## 3. DG-SEM Lowering

- [x] 3.1 Add component metadata to DG lowering entries.
- [x] 3.2 Emit deterministic per-component lowering entries for rank-1 vectors.
- [x] 3.3 Add deterministic vector source lowering signatures.

## 4. Tests + Docs

- [x] 4.1 Add regression tests for vector source parsing/validation.
- [x] 4.2 Add regression tests for component-aware DG lowering behavior.
- [x] 4.3 Update backend support docs and active execution plan checklist.
