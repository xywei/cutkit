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
| Execution planning hygiene | B | active/completed plan split is now enforced with merged plans moved out of `active/` |
| Docs freshness guardrails | B | markdown path and heading-anchor freshness is checked in quality gates |
| Geometry/topology regression coverage | B | cut-panel harness now includes seam-adjacent, near-degenerate, imported-production, and fuzz-derived cases |
| Maintenance automation | B | weekly janitor workflow can auto-open maintenance PRs |

## Next Improvements

Current focus: anchor-level docs link freshness (`docs/exec-plans/active/20260323-docs-anchor-link-validation.md`).

1. Add concise visual diff snapshots for cut-panel failure artifacts.
2. Expand anchor validation coverage for renderer-specific heading edge cases.
3. Add larger imported corpus packs and deterministic fuzz minimization workflow.
