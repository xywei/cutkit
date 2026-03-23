## Context

The existing cut-panel harness validates only three baseline cases. These are
useful sanity checks but underrepresent problematic geometry classes found in
production, especially loops near outer seams and very thin panel regions.

## Goals / Non-Goals

**Goals:**
- Add deterministic default cases that exercise seam-adjacent and
  near-degenerate geometry behavior.
- Add explicit regression checks that distinguish valid seam-adjacent geometry
  from invalid seam-touching topology.
- Keep the existing harness script and CI behavior unchanged except for richer
  case coverage.

**Non-Goals:**
- Reworking folded triangulation internals.
- Expanding into non-polygonal curve benchmarks in this change.

## Decisions

1. Add new corpus entries to `default_cases()` rather than creating a separate
   optional suite.
   - Rationale: the default harness is already part of `make dev`, so this gives
     immediate regression coverage.
   - Alternatives considered: separate optional suites were rejected because
     they are easier to skip and provide weaker CI protection.

2. Use simple polygon loops with carefully chosen near-seam and thin dimensions.
   - Rationale: preserves deterministic diagnostics and avoids introducing new
     geometry dependencies.
   - Alternatives considered: CAD-derived fixtures were rejected as unnecessary
     complexity for this layer.

3. Capture seam-touching failure behavior in tests as a topology regression
   guard.
   - Rationale: keeps expected failure mode explicit and prevents accidental
     relaxation of strict-inside constraints.
   - Alternatives considered: relying on generic topology tests alone was
     rejected because they do not anchor behavior to the cut-panel corpus intent.

## Risks / Trade-offs

- [Risk] Near-degenerate dimensions can increase floating-point sensitivity. ->
  Mitigation: use conservative but still stress-inducing dimensions and keep
  tolerance assertions metric-based.
- [Risk] Future edits may accidentally place seam-adjacent holes on the seam. ->
  Mitigation: add explicit pass/fail tests for both seam-adjacent and
  seam-touching variants.
