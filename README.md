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

## Folded Decomposition (2D)

Current 2D scope is CAD-native first, with a polygonized MVP fallback:

- loop orientation normalization (outer ccw, holes cw)
- interior anchor selection
- folded decomposition on line and curved CAD edges
- OpenCascade-backed exact cell clipping for Section 6 reproductions
- area and low-order moment diagnostics

Current limitations:

- 3D folded decomposition is currently centered on Section 6.1.3-style
  boundary-driven workflows; broader 3D clipping/geometry coverage remains follow-up work
- no singular-kernel-specialized quadrature yet

Reproduction script for Antolin-Wei-Buffa (2022) Section 6 examples:

```bash
uv run python scripts/reproduce_antolin_2022_examples.py
```

This runs 2D and 3D reproductions by default (including 3D Cartesian
cut-cell refinement for Section 6.2).

2D runs use `--geometry-mode auto` by default, which selects CAD-native
OpenCascade when available and otherwise falls back to polygonized mode.

The 3D Section 6.2 path is CUTKIT-adapted and currently may show non-monotonic
rows for some `(n, h)` combinations.

For faster runs, enable NumPy acceleration in your environment:

```bash
uv sync --extra perf
```

For CAD-native OpenCascade 2D reproduction support:

```bash
uv sync --extra cad
```

Note: OpenCascade wheels may require system OpenGL libraries (for example
`libGL.so.1`) to be present.

Source and credit for the reproduced Section 6 2D protocols:

- Pablo Antolin, Xiaodong Wei, Annalisa Buffa
- "Robust Numerical Integration on Curved Polyhedra Based on Folded Decompositions"
- Computer Methods in Applied Mechanics and Engineering (2022)
- DOI: `10.1016/j.cma.2022.114948`
- arXiv: `2109.03734` (`https://arxiv.org/abs/2109.03734`)

The default mode is a quick protocol check (fast enough for local iteration).

To run only the 2D parts:

```bash
uv run python scripts/reproduce_antolin_2022_examples.py --skip-3d
```

To force CAD-native OpenCascade mode for 2D:

```bash
uv run python scripts/reproduce_antolin_2022_examples.py --geometry-mode cad-native
```

To force polygonized fallback mode for 2D:

```bash
uv run python scripts/reproduce_antolin_2022_examples.py --geometry-mode polygonized
```

For denser settings closer to the Antolin-Wei-Buffa (2022) sweep:

```bash
uv run python scripts/reproduce_antolin_2022_examples.py --antolin-paper
```

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
