## Context

Section 6.2 3D currently uses an x-surface-only Cartesian integration helper,
which limits reuse for other axis-aligned graph classes. The script output notes
non-monotonic rows but does not provide structured diagnostics, and paper-profile
parity fixtures are currently not full-scope.

## Goals / Non-Goals

**Goals:**
- Generalize 3D clipping/integration entry points across x/y/z aligned graph
  surfaces while preserving existing behavior for x-surface workflows.
- Add deterministic monotonicity diagnostics to Section 6.2 3D result objects
  and manifests.
- Promote antolin-paper fixtures to full scope and keep parity docs/tests in
  sync.
- Document singular quadrature status and defer QBFEM implementation.

**Non-Goals:**
- Implementing singular or near-singular kernel quadrature.
- Replacing the Section 6.2 3D protocol with a different benchmark definition.

## Decisions

1. Add axis-general wrappers rather than rewriting the x-surface core.
   - Rationale: reuses validated x-surface implementation and minimizes risk.
   - Alternatives considered: fully new per-axis loop implementations were
     rejected due duplication and divergence risk.

2. Add monotonicity diagnostics as explicit fields in Section 6.2 3D order
   results.
   - Rationale: provides machine-readable investigation signals in manifests and
     parity comparisons.
   - Alternatives considered: plain console warnings were rejected as
     insufficiently testable.

3. Keep CAD antolin-paper full fixture as placeholder when CAD is unavailable.
   - Rationale: preserves fixture matrix completeness without introducing
     environment-coupled failures.
   - Alternatives considered: omitting CAD paper fixture was rejected because it
     leaves mode/profile coverage ambiguous.

4. Record singular quadrature status in docs/follow-up notes rather than adding
   stubs in runtime code.
   - Rationale: avoids implying implemented support while still clarifying paper
     scope and roadmap.

## Risks / Trade-offs

- [Risk] Axis wrapper mistakes can silently permute coordinates. -> Mitigation:
  add analytic half-cube tests for y/z axes with known volumes.
- [Risk] Full paper-profile 3D fixture generation is expensive. -> Mitigation:
  generate once with explicit command and commit deterministic manifest outputs.
- [Risk] Monotonic diagnostics may expose existing instability but not fix it.
  -> Mitigation: treat diagnostics as first-class outputs and keep protocol
  notes explicit.
