## Why

Single-patch `geometry_map=nurbs` lowering on backend `iga` now has explicit
rational execution internals, but multipatch workflows still lack deterministic
IR descriptors and interface-coupling semantics. Without explicit patch and
interface contracts, any multipatch rollout risks non-reproducible orientation
errors and ambiguous backend behavior.

We need a focused phase that introduces deterministic multipatch descriptor
semantics and capability-gated interface lowering for IGA, while keeping
existing single-patch behavior stable.

## What Changes

- Add deterministic multipatch descriptor schema support (patch identifiers and
  interface descriptors) in formdsl parsing/IR metadata.
- Add capability-gated multipatch interface lowering for backend `iga` with
  deterministic orientation and selector diagnostics.
- Preserve current single-patch `bspline` and `nurbs` behavior when multipatch
  metadata is omitted.
- Add regression coverage for valid multipatch interfaces and strict/permissive
  diagnostics for malformed descriptors or unsupported backend requests.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: expands from single-patch NURBS execution to
  deterministic multipatch interface descriptor and coupling support.

### Unchanged Capabilities

- `ufl-dgsem-form-dsl`: remains multipatch-interface unsupported and continues
  to emit deterministic capability diagnostics.

## Impact

- Affected code:
  - `src/cutkit/formdsl/ir.py`
  - `src/cutkit/formdsl/adapter.py`
  - `src/cutkit/formdsl/capabilities.py`
  - `src/cutkit/formdsl/iga_backend.py`
  - regression tests under `tests/formdsl/`
  - support docs under `docs/`
- This phase does not add DG-SEM multipatch execution.
