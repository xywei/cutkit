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

1. Run the reproduction script and write a candidate fixture:

   ```bash
   uv run python scripts/reproduce_antolin_2022_examples.py \
     --parity-fixture tests/fixtures/antolin-section6/<name>.json \
     --write-parity-fixture
   ```

2. Re-run with parity enabled against that fixture:

   ```bash
   uv run python scripts/reproduce_antolin_2022_examples.py \
     --parity-fixture tests/fixtures/antolin-section6/<name>.json
   ```

3. In review, call out why fixture values changed (algorithmic change,
   dependency change, tolerance policy update, etc).

## CAD-Unavailable Behavior

For fixtures with `requires_cad: true`, parity checks are skipped with an
explicit status when OpenCascade is unavailable.

## Current Fixture Set

- `quick-polygonized-full.json`
- `quick-cad-native-full.json`
- `antolin-paper-polygonized-2d-only.json`
- `antolin-paper-cad-native-2d-only.json`
