## Why

Recent merged work closed major folded-decomposition parity gaps, but three
quality concerns remain tightly coupled in day-to-day debugging and regression
reliability:

1. cut-panel failures still expose mostly string-level topology diagnostics,
2. docs cross-references can drift without a dedicated freshness gate,
3. the cut-panel corpus still under-represents imported-production and
   fuzz-derived geometries.

Addressing them together improves signal, debuggability, and maintenance
discipline in one pass.

## What Changes

- Add structured topology diagnostics in panel validation results and make them
  available through cut-panel evaluation outputs.
- Add exportable JSON artifacts for failed cut-panel cases to accelerate local
  and CI debugging.
- Add a docs freshness checker for cross-reference paths and enforce it in
  quality gates.
- Expand cut-panel default corpus with imported-production and fuzz-derived
  fixtures.

## Capabilities

### New Capabilities
- `cutpanel-topology-artifacts`: structured topology diagnostics and failure
  artifact exports for cut-panel evaluations.
- `docs-cross-reference-freshness`: repository docs cross-reference validation
  that fails quality checks when paths go stale.
- `cutpanel-corpus-imported-fuzz`: default cut-panel corpus includes
  imported-production and fuzz-derived case groups.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/topology/loops2d.py`
  - `src/cutkit/evals/cutpanel.py`
  - `scripts/run_cutpanel_eval.py`
  - docs freshness checker script/module and quality config
  - cut-panel corpus fixtures/docs/tests
- No new third-party runtime dependencies expected.
