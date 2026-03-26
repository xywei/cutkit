# Antolin Section 6 Parity Fixtures

Naming convention:

- `<profile>-<geometry-mode>-<scope>.json`
- `profile`: `quick` or `antolin-paper`
- `geometry-mode`: `polygonized` or `cad-native`
- `scope`: `full` (2D+3D) or `2d-only`

Notes:

- CAD-native fixtures set `requires_cad: true`.
- CAD-native fixtures are numeric full-scope baselines generated in a
  CAD-capable environment.
- In environments without OpenCascade, CAD fixture comparisons are expected to
  report as skipped rather than hard-failed.

Current mode/profile coverage:

- `quick-polygonized-full.json`
- `quick-cad-native-full.json`
- `antolin-paper-polygonized-full.json`
- `antolin-paper-cad-native-full.json`
