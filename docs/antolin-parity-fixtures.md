# Antolin Section 6 Parity Fixtures

This note describes how to generate and review Section 6 parity fixtures.

## Fixture Location

- `tests/fixtures/antolin-section6/`

## Naming Convention

- `<profile>-<geometry-mode>-<scope>.json`
- profiles: `quick`, `antolin-paper`
- geometry modes: `polygonized`, `cad-native`
- scope: `full` (2D+3D) or `2d-only`

## Update Workflow

1. Refresh a fixture with explicit geometry and scope flags.

   Example: quick polygonized full fixture

   ```bash
   uv run python scripts/reproduce_antolin_2022_examples.py \
     --geometry-mode polygonized \
     --parity-fixture tests/fixtures/antolin-section6/quick-polygonized-full.json \
     --write-parity-fixture
   ```

   Example: antolin-paper polygonized full fixture

   ```bash
   uv run --with numpy python scripts/reproduce_antolin_2022_examples.py \
     --antolin-paper \
     --geometry-mode polygonized \
      --parity-fixture tests/fixtures/antolin-section6/antolin-paper-polygonized-full.json \
      --write-parity-fixture
   ```

2. Re-run parity against the same fixture with matching flags.

   ```bash
   uv run python scripts/reproduce_antolin_2022_examples.py \
     --geometry-mode polygonized \
     --parity-fixture tests/fixtures/antolin-section6/quick-polygonized-full.json
   ```

3. In review, call out why fixture values changed (algorithmic change,
   dependency change, tolerance policy update, etc).

4. CAD fixtures require OpenCascade (`uv sync --extra cad`) and system GL.
   Current CAD fixtures are numeric full-scope baselines generated on a
   CAD-capable host. When CAD is unavailable, CAD fixture comparison is
   reported as skipped.

## CAD-Unavailable Behavior

For fixtures with `requires_cad: true`, parity checks are skipped with an
explicit status when OpenCascade is unavailable.

## Current Fixture Set

- `quick-polygonized-full.json`
- `quick-cad-native-full.json`
- `antolin-paper-polygonized-full.json`
- `antolin-paper-cad-native-full.json`
