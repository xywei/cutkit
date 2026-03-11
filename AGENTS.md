# AGENTS.md

This file is a map for coding agents working in this repository.
Keep it short and use it as a table of contents, not as a full manual.

## First-Minute Checklist

1. Read `docs/index.md` for the docs map.
2. Read `ARCHITECTURE.md` for package boundaries.
3. If the task is non-trivial, create or update an execution plan in
   `docs/exec-plans/active/`.
4. Run `make dev` before handing off changes.

## Working Principles

- Prefer repository-local knowledge over chat history.
- Keep changes small, reviewable, and easy to revert.
- Encode repeated guidance as docs or checks, not one-off instructions.
- Favor clear structure and predictable naming over cleverness.

## Source Of Record

- Product and architecture intent: `docs/` and `ARCHITECTURE.md`
- Code and API behavior: `src/`
- Quality baseline and known gaps: `docs/quality/score.md`
- Active and completed execution plans: `docs/exec-plans/`
- OpenSpec change artifacts: `openspec/changes/`

## Repository Map

- `src/cutkit/`: Python package source
- `tests/`: test suite
- `docs/`: documentation system of record
  - `docs/index.md`: doc index
  - `docs/exec-plans/active/`: plans in progress
  - `docs/exec-plans/completed/`: archived plans
  - `docs/quality/score.md`: architecture and quality scorecard
  - `docs/entire-transcript-policy.md`: transcript handling policy
- `.github/workflows/ci.yml`: CI checks
- `Makefile`: common local commands

## Plan Workflow

- Create one markdown file per meaningful task in `docs/exec-plans/active/`.
- Include: objective, scope, acceptance criteria, and checklist.
- Keep plan progress updated while implementing.
- Move completed plans to `docs/exec-plans/completed/` with outcomes.

## Spec Workflow

- Start change definition with `/opsx-propose` (OpenCode) or `/opsx:propose`.
- Implement with `/opsx-apply` (OpenCode) or `/opsx:apply`.
- Archive with `/opsx-archive` (OpenCode) or `/opsx:archive`.

## Validation Commands

Use `uv` and `prek` via:

```bash
make dev
```

Equivalent checks:

```bash
uv run prek run --all-files
```

## Guardrails

- Python requirement is `>=3.12`.
- Do not bypass hooks or CI requirements.
- Do not push directly to `main`.
- Keep docs and code in sync when behavior changes.
