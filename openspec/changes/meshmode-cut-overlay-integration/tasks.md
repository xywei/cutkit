## 1. Phase A: Contract Core

- [ ] 1.1 Define public overlay result types (indices, weights, geometry metadata,
      per-element status, diagnostics) in a stable module boundary.
- [ ] 1.2 Add explicit contract version field(s) and compatibility policy notes.
- [ ] 1.3 Add meshmode cut-overlay entry-point API accepting CUTKIT payloads with
      explicit mapping inputs.
- [ ] 1.4 Add strict/permissive mode controls with documented defaults.

## 2. Phase A: Deterministic Mapping and Validation

- [ ] 2.1 Implement deterministic element-id mapping logic for CUTKIT payload to
      meshmode target alignment.
- [ ] 2.2 Implement mapping and orientation validation checks.
- [ ] 2.3 Implement mismatch classification and per-element status population for
      mixed batches.
- [ ] 2.4 Implement strict fail-fast and permissive partial-success behavior.

## 3. Phase A Exit Gate

- [ ] 3.1 Add unit tests for contract shape, deterministic ordering, and
      strict/permissive behavior.
- [ ] 3.2 Add diagnostics payload fields/messages for mapping/orientation/invalid
      element classes.
- [ ] 3.3 Verify this change can be consumed by the planned DG-SEM adapter
      without ad hoc data reshaping.

## 4. Phase B: Consumer Hardening and Docs

- [ ] 4.1 Add integration tests with representative meshmode-style layouts for
      nominal and mixed-status batches.
- [ ] 4.2 Document meshmode cut-overlay usage and failure semantics with minimal
      end-to-end examples.
