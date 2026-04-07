## Context

`multipatch_penalty` currently configures one scalar value for all IGA
multipatch interfaces. Recent multipatch stress fixtures showed a practical need
for heterogeneous interface weights while keeping deterministic behavior.

## Goals / Non-Goals

**Goals**

- Add optional per-interface penalty control in multipatch descriptors.
- Preserve deterministic fallback to global `multipatch_penalty` when interface
  penalty is omitted.
- Keep parsing and assembly validation deterministic for malformed penalties.
- Expose effective interface penalties in IGA payload metadata.

**Non-Goals**

- DG-SEM multipatch execution.
- Interface-family expansion beyond current penalty-style coupling model.
- Runtime adaptive penalty heuristics.

## Decisions

1. Add optional `penalty` field on each interface descriptor.
   - Rationale: keeps controls colocated with interface topology/orientation.

2. Keep metadata-level `multipatch_penalty` as fallback.
   - Rationale: backward-compatible behavior for existing payloads.

3. Validate penalties at parse and IR-validation stages.
   - Rationale: fail early with deterministic diagnostics before assembly.

4. Record effective coupling penalty in `interface_lowering` metadata.
   - Rationale: improves observability and testability of control precedence.

## Risks / Trade-offs

- [Risk] Duplicate interfaces with differing penalties may still be ambiguous.
  - Mitigation: keep canonical duplicate rejection independent of penalty.
- [Risk] Very large penalties can worsen conditioning.
  - Mitigation: enforce finite positive values and leave numerical tuning to the
    caller.

## Migration Plan

1. Extend OpenSpec requirements for per-interface coupling controls.
2. Implement IR/parser support and deterministic penalty validation.
3. Apply per-interface penalty precedence in IGA coupling assembly.
4. Add regression tests/docs and update execution tracking.
