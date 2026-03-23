## Context

Section 6 scripts currently print tables for human inspection and tests primarily check trends such as monotonicity or order improvements. This is useful but insufficient for catching subtle numerical drift caused by algorithm changes, dependency updates, or environment differences.

## Goals / Non-Goals

**Goals:**
- Define a canonical machine-readable schema for Section 6 run outputs.
- Add mode-aware parity fixtures for polygonized 2D, CAD-native 2D, and 3D runs.
- Enforce tolerance-based comparisons in tests and CI output.
- Provide actionable diff diagnostics when parity checks fail.

**Non-Goals:**
- Re-derive the numerical methods themselves in this change.
- Eliminate all floating-point variability across every hardware platform.
- Replace fast qualitative smoke tests that remain useful for local iteration.

## Decisions

1. Add a structured result manifest emitted by reproduction runners.
   - Rationale: Stable machine-readable output is required before robust parity checks.
   - Alternatives considered: Parsing console tables was rejected because it is brittle.

2. Keep separate fixtures by geometry mode and parameter profile.
   - Rationale: Polygonized and CAD-native paths are intentionally different and should not share one numeric baseline.
   - Alternatives considered: A single global fixture was rejected because it conflates mode-specific behavior.

3. Use combined absolute/relative tolerances per metric family.
   - Rationale: Mixed tolerance policies better handle values across several orders of magnitude.
   - Alternatives considered: Relative-only thresholds were rejected because near-zero entries become unstable.

4. Add explicit handling for unavailable CAD environments.
   - Rationale: CI and developer machines differ in OpenCascade availability.
   - Alternatives considered: Hard-failing parity when CAD is unavailable was rejected for portability.

5. Surface row-level and metric-level diffs in failure output.
   - Rationale: Engineers need direct localization of drift to debug quickly.
   - Alternatives considered: Single aggregate pass/fail status was rejected as low-signal.

## Risks / Trade-offs

- [Risk] Fixture updates may hide unintended regressions if overused. -> Mitigation: require explicit fixture update notes and review sign-off.
- [Risk] Tolerance bands can be set too loose or too strict. -> Mitigation: calibrate against historical runs and document rationale.
- [Risk] CAD and non-CAD environments can diverge in surprising ways. -> Mitigation: tag fixtures with environment metadata and mode identifiers.

## Migration Plan

1. Add structured result output alongside existing table output.
2. Generate initial fixtures for quick and paper profiles per mode.
3. Add parity checks in tests and script wrappers.
4. Gate CI on parity checks where environment prerequisites are met.
5. Document fixture update workflow.

## Open Questions

- Should fixtures be stored as JSON, CSV, or both?
- Should paper-profile parity run in default CI, or only in scheduled jobs?
