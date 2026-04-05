## 1. Phase 1: UFL Frontend + IR + IGA Backend

- [x] 1.1 Add UFL adapter entrypoint(s) for form parsing and backend selection.
- [x] 1.2 Add method-neutral weak-form IR types and deterministic diagnostics.
- [x] 1.3 Add supported-form capability matrix for initial scalar subset.
- [x] 1.4 Implement IR-to-IGA lowering for scalar diffusion/mass/reaction forms.
- [x] 1.5 Reuse CUTKIT trimmed quadrature in IGA backend assembly loops.
- [x] 1.6 Add boundary-condition lowering for essential/natural terms in the
      initial subset.

## 2. Phase 1 Exit Gate

- [x] 2.1 Add unit tests for UFL parsing, IR construction, and capability checks.
- [x] 2.2 Add manufactured-solution tests for IGA assembly correctness.
- [x] 2.3 Document backend support matrix and unsupported-form diagnostics.

## 3. Phase 2: meshmode+grudge DG-SEM Backend

- [x] 3.1 Confirm prerequisite: `meshmode-cut-overlay` contract is landed.
- [x] 3.2 Implement IR-to-DG-SEM lowering using meshmode+grudge building blocks.
- [x] 3.3 Integrate meshmode cut-overlay payloads into DG assembly path.
- [x] 3.4 Add initial flux/trace lowering for same scalar subset.
- [x] 3.5 Add deterministic mapping/orientation validation diagnostics.

## 4. Phase 2 Exit Gate

- [x] 4.1 Add backend parity tests (same form/problem on `iga` and `dgsem`).
- [x] 4.2 Add convergence/parity benchmark examples.
- [ ] 4.3 Verify strict/permissive diagnostics and run `make dev`.

## 5. Phase 3 Backlog (post-MVP)

- [ ] 5.1 Evaluate expansion to vector-valued forms.
- [ ] 5.2 Evaluate additional DG flux families.
- [ ] 5.3 Evaluate NURBS geometry mapping and multipatch support.
