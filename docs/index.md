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
- `docs/poisson-benchmarks.md`: Poisson-oriented benchmark usage and profiles
- `docs/poisson-galerkin-solver.md`: immersed Poisson Galerkin solve + validation workflow
- `scripts/check_docs_freshness.py`: stale docs path + markdown-anchor checker
- `scripts/minimize_cutpanel_fuzz_cases.py`: deterministic fuzz-candidate minimizer
- `docs/entire-transcript-policy.md`: Entire transcript handling policy
- `.github/workflows/weekly-janitor.yml`: scheduled repository cleanup automation

## Conventions

- Keep docs concise and cross-linked.
- Update docs in the same change when behavior or architecture changes.
- Prefer many focused docs over one large catch-all doc.
