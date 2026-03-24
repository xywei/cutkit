## Why

`docs/quality/score.md` still tracks three open quality improvements that are
coupled in day-to-day evaluation and maintenance workflows:

1. failure artifacts lack compact visual diff snapshots,
2. docs anchor validation still misses renderer-specific heading edge patterns,
3. cut-panel corpus packs and fuzz minimization workflow need expansion.

Addressing these together improves debugging signal, docs reliability, and corpus
maintenance consistency in one pass.

## What Changes

- Add deterministic visual diff snapshots to cut-panel failure artifact payloads.
- Expand markdown anchor validation for additional heading and explicit-anchor
  edge cases.
- Expand imported/fuzz fixture packs and add a deterministic fuzz minimization
  workflow script.

## Capabilities

### Modified Capabilities
- `cutpanel-topology-artifacts`: failure artifacts now include concise visual
  diff snapshots.
- `docs-cross-reference-freshness`: anchor checks cover additional renderer-style
  heading edge cases.
- `cutpanel-corpus-imported-fuzz`: larger fixture packs and deterministic fuzz
  minimization workflow.

### New Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/evals/cutpanel.py`
  - `scripts/run_cutpanel_eval.py`
  - `src/cutkit/docs_freshness.py`
  - `scripts/check_docs_freshness.py`
  - `scripts/minimize_cutpanel_fuzz_cases.py`
  - `src/cutkit/evals/fixtures/`
  - tests/docs/OpenSpec artifacts
- No new runtime dependencies expected.
