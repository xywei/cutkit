# Cut-Panel Corpus Seam/Near-Degenerate Expansion

## Objective

Expand the default cut-panel evaluation corpus with seam-adjacent and
near-degenerate production-style geometries to improve regression signal for
topology and orientation-sensitive paths.

Related issue: `#8`

## Scope

- Add new default corpus cases in `src/cutkit/evals/cutpanel.py`.
- Add regression tests for new pass/fail seam/topology edge behavior.
- Keep `scripts/run_cutpanel_eval.py` output aligned with expanded corpus.
- Update docs and OpenSpec artifacts in the same change.

## Non-Goals

- Redesigning folded quadrature algorithms.
- Introducing external geometry dependencies.
- Re-scoring the entire quality scorecard beyond this targeted gap.

## Acceptance Criteria

- `run_default_eval()` returns additional seam/near-degenerate cases.
- New tests cover seam-adjacent valid and seam-touching invalid behavior.
- Cut-panel corpus usage and case intent are documented.
- `make dev` passes.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks for this change.
- [x] Add seam-adjacent and near-degenerate default corpus cases.
- [x] Add regression tests for new valid corpus cases.
- [x] Add regression tests for seam-touching invalid topology behavior.
- [x] Update docs for corpus case intent and running the harness.
- [x] Run `make dev`.
- [x] Prepare PR.

## Risks

- Very thin geometry may increase numerical sensitivity in diagnostics.
- Seam-adjacent coordinates may accidentally become seam-touching after edits.

## Final Outcome

- Status: merged.
- Delivered via: `https://github.com/xywei/cutkit/pull/9`
- Follow-ups: none open from this plan.
