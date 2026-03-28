## Why

Current 3D Section 6.2 reproduction output includes known non-monotonic rows in
the grid-refinement table, and repository docs call this out as a caveat. This
is now the main remaining paper-parity quality gap in regular-integration
workflow outputs.

## What Changes

- Improve Section 6.1.3 curved-surface projection inversion (`x = x_s(y,z)`) to
  robustly handle folded/multi-branch projections by selecting a deterministic
  lower-envelope branch.
- Tighten 3D Section 6.2 paper-profile grid sweep settings to a stable,
  monotone range.
- Update 3D Section 6.2 script/docs messaging to remove known non-monotonic
  caveat.
- Regenerate parity fixtures to reflect corrected 3D Section 6.2 outputs.

## Capabilities

### Modified Capabilities

- `folded-decomposition-3d`

## Impact

- Affected code:
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py`
  - `scripts/reproduce_antolin_2022_examples.py`
  - `README.md`
  - `tests/evals/test_antolin_examples_3d.py`
  - `tests/fixtures/antolin-section6/*.json`
