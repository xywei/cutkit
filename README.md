# CUTKIT

**Cut-cell Utilities for Trimming, Kernel Integration, and Topology**

Topology-aware cut-cell utilities for trimmed-domain kernel integration.

## Scope

CUTKIT focuses on a geometry/cut layer that complements `meshmode` and `modepy`:

- trimmed patch loop handling (outer loops, holes, orientation)
- cut-cell classification and clipping in parametric space
- robust integration helpers for regular cut panels
- diagnostics for cut topology and quadrature quality

## Non-goals (for now)

- replacing singular/near-singular QBX evaluation in `pytential`
- being a full CAD kernel

## Development Status

Early bootstrap. APIs may change.

## Development Workflow

CUTKIT uses `uv` for dependency and environment management.

```bash
make dev
```

`make dev` will:

- sync the development environment with `uv`
- install local `prek` git hooks
- block direct pushes to `main` via a local pre-push hook
- run formatting, lint, typing, architecture, tests, and cut-panel eval checks

See `docs/entire-transcript-policy.md` for the policy on using Entire session transcripts.

For cut-panel harness checks:

```bash
uv run python scripts/run_cutpanel_eval.py
```

## OpenSpec Workflow

This repository is bootstrapped for OpenSpec-driven changes.

- Run `/opsx-propose <idea>` (OpenCode) or `/opsx:propose <idea>` to define a change.
- Run `/opsx-apply <change>` (OpenCode) or `/opsx:apply <change>` to implement tasks.
- Run `/opsx-archive <change>` (OpenCode) or `/opsx:archive <change>` after merge.

See `docs/openspec-setup.md` for setup and command details.

## Repository Knowledge

- Agent map: `AGENTS.md`
- Documentation index: `docs/index.md`
- Architecture map: `ARCHITECTURE.md`

## License

MIT. See `LICENSE`.
