# Documentation Index

Repository-local documentation is the system of record for CUTKIT.

## Start Here

- `AGENTS.md`: short map for coding agents
- `ARCHITECTURE.md`: target package structure and boundaries
- `README.md`: project scope and local development commands
- `docs/openspec-setup.md`: OpenSpec workflow setup and usage

## Planning

- `docs/exec-plans/active/`: active execution plans
- `docs/exec-plans/completed/`: completed execution plans

## Quality And Operations

- `docs/quality/score.md`: quality scorecard and known gaps
- `docs/cutpanel-corpus.md`: default cut-panel regression corpus and intent
- `docs/folded-decomposition-followups.md`: tracked post-MVP folded-decomposition extensions
- `docs/antolin-parity-fixtures.md`: Section 6 parity fixture and update workflow
- `docs/cad-box-batch-interface.md`: consumer-facing CAD object-or-arrays clip/integrate interface
- `docs/volumential-handoff.md`: CUTKIT far/near primitive handoff contract for volumential workflows
- `docs/meshmode-cut-overlay.md`: meshmode cut-overlay contract and validation semantics
- `docs/nearfield-template-experiments.md`: folded fan near-field template derivation and prototype
- `docs/poisson-benchmarks.md`: Poisson-oriented benchmark usage and profiles
- `docs/poisson-galerkin-solver.md`: immersed Poisson Galerkin solve + validation workflow
- `docs/formdsl-parity-benchmarks.md`: shared IGA + DG-SEM formdsl parity benchmark usage
- `docs/formdsl-nurbs-multipatch-evaluation.md`: Phase 3 evaluation notes for NURBS mapping and multipatch rollout
- `docs/ufl-backend-support.md`: UFL form backend support matrix and diagnostics
- `scripts/check_docs_freshness.py`: stale docs path + markdown-anchor checker
- `scripts/minimize_cutpanel_fuzz_cases.py`: deterministic fuzz-candidate minimizer
- `scripts/run_formdsl_parity_benchmark.py`: run formdsl convergence + parity benchmark examples
- `docs/entire-transcript-policy.md`: Entire transcript handling policy
- `.github/workflows/weekly-janitor.yml`: scheduled repository cleanup automation

## Conventions

- Keep docs concise and cross-linked.
- Update docs in the same change when behavior or architecture changes.
- Prefer many focused docs over one large catch-all doc.
