## Overview

This change introduces three coordinated quality upgrades:

1. structured topology diagnostics and artifact exports for cut-panel failures,
2. deterministic docs cross-reference validation in quality gates,
3. broader default corpus coverage via imported and fuzz-derived fixtures.

## Design Decisions

### Topology diagnostics model

- Extend `PanelValidationResult` to include machine-readable diagnostics
  (orientation, signed-area, self-intersection, containment/intersection, and
  overlap relationships).
- Keep existing string error messages for compatibility, but derive them from
  the same computed diagnostics.

### Failure artifact exports

- Extend cut-panel evaluation outputs to carry topology diagnostics.
- Add JSON artifact export helpers that serialize case geometry, metrics,
  topology diagnostics, and errors for failed cases.
- Expose artifact writing through `scripts/run_cutpanel_eval.py` with an output
  directory option.

### Docs freshness checker

- Add a repository-local checker that scans markdown docs for path-like
  cross-references and verifies the referenced files/directories exist.
- Integrate checker into local/CI quality gates (`make check` / pre-commit via
  `prek`) so stale links fail fast.

### Corpus expansion strategy

- Add fixture-backed case groups for:
  - imported-production style geometries,
  - fuzz-derived edge cases.
- Load these fixtures into the default corpus path and keep deterministic case
  ordering to preserve stable output.

## Risks and Mitigations

- **False-positive docs checks**: scope parser to path-like references and skip
  URLs/anchors.
- **Numerical sensitivity in new corpus cases**: keep deterministic, validated
  geometries and assert bounded tolerances in tests.
- **Artifact schema drift**: keep schema simple, explicit, and covered by tests.
