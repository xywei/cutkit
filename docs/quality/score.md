# Quality Scorecard

This scorecard tracks current quality posture and where to invest next.

Scores are intentionally coarse:

- `A`: strong and enforced
- `B`: mostly solid, minor gaps
- `C`: usable but under-defined
- `D`: weak or missing

## Current Baseline

| Area | Score | Notes |
| --- | --- | --- |
| Repository map and docs index | B | `AGENTS.md` and doc index exist, coverage should grow with features |
| Architecture boundaries | B | target layering is documented and checked via `scripts/check_architecture.py` |
| Dev workflow and checks | B | `uv`, `prek`, CI, and local bootstrap are active |
| Execution planning hygiene | C | plan directories exist; usage habits still forming |
| Geometry/topology regression coverage | C | cut-panel harness now includes seam-adjacent and near-degenerate cases; broader production corpus still limited |
| Maintenance automation | B | weekly janitor workflow can auto-open maintenance PRs |

## Next Improvements

1. Add richer topology diagnostics and artifact exports for debugging failures.
2. Add docs freshness checks that fail CI on stale cross-references.
3. Expand corpus further with imported production fixtures and fuzz-derived edge cases.
