# Antolin Section 6 Parity Fixtures

Naming convention:

- `<profile>-<geometry-mode>-<scope>.json`
- `profile`: `quick` or `antolin-paper`
- `geometry-mode`: `polygonized` or `cad-native`
- `scope`: `full` (2D+3D) or `2d-only`

Notes:

- CAD-native fixtures set `requires_cad: true`.
- In environments without OpenCascade, CAD fixtures should be reported as
  unavailable rather than hard-failed.

Current mode/profile coverage:

- `quick-polygonized-full.json`
- `quick-cad-native-full.json`
- `antolin-paper-polygonized-2d-only.json`
- `antolin-paper-cad-native-2d-only.json`
