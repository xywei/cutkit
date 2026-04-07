## Why

IGA multipatch coupling now supports deterministic metadata and numerical
interface contributions, but coupling strength is controlled only by one global
metadata value (`multipatch_penalty`). This makes heterogeneous interface
stabilization awkward because users cannot tune individual interfaces without
changing all interface penalties.

We need deterministic per-interface coupling controls so interface-specific
penalties can be expressed directly in multipatch descriptors while preserving
current global-default behavior.

## What Changes

- Extend multipatch interface descriptors with optional per-interface penalty
  configuration.
- Keep `multipatch_penalty` metadata as the global fallback when interface
  penalty is omitted.
- Validate per-interface penalties deterministically (finite, positive).
- Surface effective interface penalties in IGA lowering payload metadata.
- Add regression coverage for override precedence and malformed controls.

## Capabilities

### Modified Capabilities

- `ufl-iga-form-dsl`: multipatch coupling control expands from global penalty
  only to per-interface override controls with deterministic fallback semantics.

### Unchanged Capabilities

- `ufl-dgsem-form-dsl`: remains multipatch execution unsupported.

## Impact

- Affected code:
  - `src/cutkit/formdsl/ir.py`
  - `src/cutkit/formdsl/adapter.py`
  - `src/cutkit/formdsl/iga_backend.py`
  - `tests/formdsl/test_formdsl_assembly.py`
  - docs updates under `docs/`
