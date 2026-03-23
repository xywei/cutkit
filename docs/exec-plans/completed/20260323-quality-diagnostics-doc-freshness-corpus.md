# Quality Diagnostics + Docs Freshness + Corpus Expansion

## Objective

Implement three coupled quality upgrades in one change set:

1. richer cut-panel topology diagnostics and exportable failure artifacts,
2. docs cross-reference freshness checks that fail local/CI quality gates,
3. expanded cut-panel corpus with imported-production and fuzz-derived cases.

## Scope

- Extend topology validation reports with structured diagnostics.
- Extend cut-panel eval API/script to surface diagnostics and write JSON artifacts
  for failed cases.
- Add a docs-freshness checker and wire it into repository checks.
- Add corpus fixture ingestion for imported/fuzz case sets and include these in
  default cut-panel regression coverage.
- Update tests/docs/OpenSpec artifacts.

## Non-Goals

- New singular quadrature algorithms.
- Replacing the current cut-panel metric definitions.
- Full property-based fuzzing framework integration.

## Acceptance Criteria

- Failed cut-panel eval cases produce structured topology diagnostics and can be
  exported as artifact JSON files.
- A docs-freshness check fails when a tracked cross-reference points at a
  missing file/path and is enforced by `make dev` and CI.
- Default cut-panel corpus includes imported-production and fuzz-derived cases,
  with regression tests and docs updates.
- `make dev` passes.

## Implementation Checklist

- [x] Add OpenSpec change proposal/design/spec/tasks for this bundle.
- [x] Add structured topology diagnostics to `validate_panel()` results.
- [x] Add cut-panel failure artifact export helpers and CLI options.
- [x] Add docs freshness checker and integrate into quality gates.
- [x] Add imported/fuzz corpus fixtures and default corpus loader path.
- [x] Add/adjust tests for diagnostics, docs freshness, and corpus expansion.
- [x] Update docs for workflow and corpus/diagnostic behavior.
- [x] Run focused tests and `make dev`.

## Risks

- Overly broad docs-reference parsing could create false positives.
- Added corpus cases may expose numerical sensitivity requiring tolerance tuning.
- Failure artifact schema should stay stable enough for debugging reuse.

## Final Outcome

- Status: merged.
- Delivered via: `https://github.com/xywei/cutkit/pull/12`
- Follow-ups: none open from this plan.
