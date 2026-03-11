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
| Geometry/topology regression coverage | C | baseline cut-panel eval harness exists; corpus depth still limited |
| Maintenance automation | B | weekly janitor workflow can auto-open maintenance PRs |

## Next Improvements

1. Expand cut-panel corpus with seam and near-degenerate production cases.
2. Add richer topology diagnostics and artifact exports for debugging failures.
3. Add docs freshness checks that fail CI on stale cross-references.
