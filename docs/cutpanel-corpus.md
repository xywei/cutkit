# Cut-Panel Corpus

`scripts/run_cutpanel_eval.py` executes the default deterministic corpus from
`cutkit.evals.default_cases()`.

## Current Default Cases

- Baseline deterministic cases:
- `unit-square`: baseline convex panel without holes.
- `square-with-hole`: centered hole with clear orientation expectations.
- `rect-with-thin-hole`: rectangular panel with a thin interior notch.
- `square-with-seam-adjacent-slot`: hole placed close to the outer seam without
  touching it.
- `square-with-ultra-thin-frame`: near-degenerate frame with a very large inner
  hole and narrow retained region.
- Imported-production fixture cases (from
  `src/cutkit/evals/fixtures/cutpanel-production-imported.json`).
- Fuzz-derived deterministic edge cases (from
  `src/cutkit/evals/fixtures/cutpanel-fuzz-derived.json`).
- Fuzz candidate pack used for deterministic minimization workflow (from
  `src/cutkit/evals/fixtures/cutpanel-fuzz-candidates.json`).

## Why These Cases

- Baseline metrics: area, cut fraction, and folded moment consistency.
- Orientation checks: outer loop ccw and holes cw.
- Topology checks: strict-inside hole rules and boundary intersection guards.
- Stress geometry: seam-adjacent and near-degenerate dimensions that are prone
  to regression.
- Production-style shape mix: multi-hole and corridor-like fixtures.
- Fuzz-style edge behavior: slim slots, seam-adjacent holes, and expanded
  multi-pocket configurations.

## Deterministic Fuzz Minimization

Regenerate the checked-in fuzz-derived fixture from the candidate pack:

```bash
uv run python scripts/minimize_cutpanel_fuzz_cases.py
```

The minimizer deduplicates by canonical geometry signature, ranks complexity
deterministically, and emits a bounded selected subset.

## Run

```bash
uv run python scripts/run_cutpanel_eval.py
```

Use `make dev` to run this together with formatting, lint, typing, architecture,
and tests.

## Failure Artifacts

When debugging failures, write per-case JSON artifacts with topology diagnostics
and compact visual diff snapshots:

```bash
uv run python scripts/run_cutpanel_eval.py --artifact-dir .artifacts/cutpanel
```
