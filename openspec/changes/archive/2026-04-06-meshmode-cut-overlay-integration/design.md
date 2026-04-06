## Context

CUTKIT currently focuses on trimmed-domain clipping and integration workflows, with output contracts optimized for internal quadrature and solver handoff primitives. The repository architecture already expects interoperability with `meshmode`, but there is no explicit adapter contract that maps cut/cell integration outputs into meshmode element- and quadrature-oriented overlays.

Today, downstream users must manually align element indices, geometry metadata, and integration status handling. This creates repeated glue code and inconsistent failure semantics. The proposed change introduces a dedicated integration layer and public contract for meshmode overlays while preserving CUTKIT's topology-first validation and deterministic status reporting model.

## Goals / Non-Goals

**Goals:**
- Define a stable CUTKIT-to-meshmode overlay contract that downstream assembly code can consume without ad hoc translation.
- Provide deterministic mapping behavior for element identifiers, local quadrature payloads, and per-element statuses (`ok`, `empty`, `invalid_box`, `backend_error`, plus mapping-specific mismatch statuses).
- Ensure diagnostics make mismatches actionable (for example, orientation or index-space mismatch) without requiring deep inspection of raw geometry internals.
- Keep implementation aligned with existing layer direction and avoid reverse dependencies across core geometry/topology/clipping/quadrature layers.

**Non-Goals:**
- Introducing meshmode as a hard runtime dependency for all CUTKIT users.
- Replacing existing source-cloud or local-operator export APIs.
- Solving distributed/parallel overlay exchange formats in this change.
- Redesigning underlying clipping or quadrature algorithms.

## Decisions

1. Introduce a dedicated meshmode adapter surface under `io`-facing boundaries.
   - Rationale: adapter responsibilities are integration-facing and should not force core quadrature modules to depend on meshmode-specific data shapes.
   - Alternative considered: embedding translation directly in quadrature outputs. Rejected because it leaks consumer-specific concerns into core layers.

2. Use explicit overlay result objects with structured status fields instead of raising on first mismatch.
   - Rationale: this matches CUTKIT's batch-oriented status model and supports partial success workloads.
   - Alternative considered: exception-driven API for mismatch/error paths. Rejected because it obscures per-element outcomes and complicates reproducible diagnostics.

3. Require deterministic index mapping inputs (explicit element id map or canonical ordering contract).
   - Rationale: avoids hidden assumptions between CUTKIT-produced boxes/cells and meshmode discretization ordering.
   - Alternative considered: implicit positional matching. Rejected due to fragility across mesh generation and refinement workflows.

4. Provide validation hooks that can run in strict or permissive mode.
   - Rationale: strict mode is needed for production workflows that must fail fast; permissive mode supports exploratory runs and fixture generation.
   - Alternative considered: strict-only behavior. Rejected because it blocks legitimate partial-data analysis and parity workflows.

5. Version overlay payload contracts from first release.
   - Rationale: downstream backends (DG-SEM today, others later) need additive
     compatibility guarantees.
   - Alternative considered: unversioned schema with doc-only compatibility.
     Rejected due to high risk of silent consumer breakage.

## Risks / Trade-offs

- [Risk] Overlay contract drifts from meshmode expectations as upstream evolves. -> Mitigation: version and document contract fields; add compatibility tests against representative meshmode data layouts.
- [Risk] Added adapter layer may duplicate existing metadata paths. -> Mitigation: centralize canonical overlay dataclass/typed-structure definitions and reuse across exports.
- [Risk] Validation overhead increases runtime for large batches. -> Mitigation: separate cheap structural checks from optional deep validation; expose mode toggles.
- [Risk] Ambiguity around orientation conventions across 2D and 3D workflows. -> Mitigation: codify orientation requirements in specs and include explicit diagnostics for mismatch categories.

## Migration Plan

1. Land new overlay types and adapter entry points behind additive APIs.
2. Add docs and examples showing translation from existing CUTKIT integration outputs to meshmode overlays.
3. Add integration tests and fixtures that cover nominal, mismatch, and partial-success paths.
4. Keep existing exports intact; encourage migration through docs and optional helper wrappers.

Rollback strategy: if regressions appear, remove or gate new adapter entry points without changing existing export contracts.

## Phasing and Exit Criteria

### Phase A (contract + validation core)

- Deliver typed overlay payloads and deterministic mapping/validation semantics.
- Exit criteria:
  - strict/permissive behavior fully specified and tested,
  - deterministic serialization/materialization ordering,
  - contract version marker documented.

### Phase B (consumer-facing integration hardening)

- Deliver representative meshmode-style integration tests and usage docs.
- Exit criteria:
  - mixed-status batches validated,
  - orientation and mapping mismatch diagnostics are actionable,
  - downstream DG-SEM adapter can consume payloads without ad hoc reshaping.

## Open Questions

- Should the first release target both nodal and modal meshmode workflows, or start with one canonical path and provide extension hooks?
- Do we need a serialized interchange form for overlays in reproducibility pipelines, or is in-memory API support sufficient for this phase?
