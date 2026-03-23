## Why

Current cut-panel regression coverage is limited to simple rectangular cases and
does not include seam-adjacent or near-degenerate geometries where topology and
orientation regressions are more likely.

## What Changes

- Expand the default cut-panel corpus with seam-adjacent and near-degenerate
  production-style cases.
- Add targeted regression checks for seam-touching invalid topology behavior.
- Document corpus case intent and expected harness usage.

## Capabilities

### New Capabilities
- `cutpanel-eval-corpus`: Define and enforce a richer default cut-panel corpus,
  including seam-adjacent and near-degenerate coverage with explicit regression
  expectations.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/evals/cutpanel.py`
  - `tests/evals/test_cutpanel_eval.py`
  - `tests/topology/test_loops2d.py`
  - `scripts/run_cutpanel_eval.py` (output reflects expanded case set)
  - `docs/` corpus and quality tracking pages
- No new runtime dependencies.
- Improves failure localization for topology/orientation regressions.
