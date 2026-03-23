## Why

Section 6 reproductions currently verify mostly qualitative behavior and include known caveats in 3D, which makes regressions hard to detect early. We need a formal parity capability with mode-aware fixtures and tolerance policies so numerical drift is visible and actionable.

## What Changes

- Add machine-readable result manifests for Section 6 reproduction runs.
- Add baseline fixture management for polygonized and CAD-native 2D paths, plus 3D paths, across quick and paper parameter profiles.
- Add tolerance-based parity checks that compare current results to committed fixtures.
- Add CI-friendly diagnostics that pinpoint which rows/columns exceed tolerance and by how much.

## Capabilities

### New Capabilities
- `antolin-section6-parity`: Deterministic fixture generation and tolerance-based regression checks for Section 6 2D/3D reproduction outputs.

### Modified Capabilities
- None.

## Impact

- Affected code:
  - `scripts/reproduce_antolin_2022_examples.py`
  - `src/cutkit/evals/antolin_wei_buffa_2022_2d.py`
  - `src/cutkit/evals/antolin_wei_buffa_2022_3d.py`
  - `tests/evals/test_antolin_examples_2d.py`
  - `tests/evals/test_antolin_examples_3d.py`
  - new parity fixtures under `tests/fixtures/` or `docs/` as selected in design
- No mandatory new runtime dependencies; optional tooling for fixture diff output may be added.
- Improves reproducibility and review confidence for numerical changes.
