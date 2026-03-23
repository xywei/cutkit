# Scorecard Open Items Consolidation

## Objective

Resolve the three currently listed quality follow-ups in one integrated change:

1. concise visual diff snapshots for cut-panel failure artifacts,
2. expanded markdown anchor validation for renderer-specific heading edge cases,
3. larger imported/fuzz cut-panel corpus packs with deterministic fuzz
   minimization workflow.

## Scope

- Extend failure artifact payloads in `src/cutkit/evals/cutpanel.py` with
  deterministic visual diff snapshot data.
- Expand docs anchor parsing in `src/cutkit/docs_freshness.py` to cover additional
  heading and anchor patterns.
- Add deterministic fuzz minimization helper(s) and a workflow script under
  `scripts/`.
- Expand imported-production and fuzz-derived fixture packs in
  `src/cutkit/evals/fixtures/`.
- Update tests and docs (`docs/cutpanel-corpus.md`, `README.md`,
  `docs/quality/score.md`, `docs/index.md`) to reflect behavior.

## Non-Goals

- Full graphical rendering pipeline for artifact visualization.
- Property-based fuzzing framework integration.
- Replacing folded quadrature algorithms or topology policy.

## Acceptance Criteria

- Failure artifact JSON includes compact deterministic visual diff snapshots.
- Docs freshness checker validates additional anchor edge cases and remains
  stable on repository docs.
- Default cut-panel corpus contains larger imported/fuzz fixture packs.
- Deterministic fuzz minimization workflow is documented and executable.
- `make dev` passes.

## Implementation Checklist

- [x] Add OpenSpec change artifacts for this bundled update.
- [x] Add visual diff snapshot generation to cut-panel failure artifacts.
- [x] Expand docs anchor extraction/normalization edge coverage.
- [x] Add deterministic fuzz minimization helpers and script workflow.
- [x] Expand imported-production and fuzz-derived fixture packs.
- [x] Add/adjust tests for artifacts, docs anchor edge cases, and minimization.
- [x] Update docs and scorecard follow-up list.
- [x] Run focused checks and `make dev`.

## Risks

- Snapshot rendering may introduce brittle expectations if the grid definition is
  not strictly deterministic.
- Anchor normalization expansions may cause false positives in unusual markdown
  formatting.
- Larger corpus packs may increase eval runtime if not kept compact.

## Final Outcome

- Status: implemented; pending merge.
- Delivered via: `https://github.com/xywei/cutkit/pull/14`
- Follow-ups: none currently planned.
