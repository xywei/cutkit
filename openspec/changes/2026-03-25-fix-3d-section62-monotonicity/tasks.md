## 1. Surface Inversion Robustness

- [x] 1.1 Replace single-seed nearest projection inversion with deterministic multi-start Newton inversion.
- [x] 1.2 Select lower-envelope `x` branch from converged candidates for `x_s(y,z)`.
- [x] 1.3 Add tests for branch-selection behavior.

## 2. 3D Section 6.2 Protocol Stabilization

- [x] 2.1 Update paper-profile 3D Section 6.2 grid sweep to a stable monotone range.
- [x] 2.2 Add/adjust tests that validate monotonic diagnostics for the paper-profile settings.

## 3. Docs and Fixtures

- [x] 3.1 Remove stale non-monotonic caveat messaging from README/script output.
- [x] 3.2 Regenerate polygonized/cad-native parity fixtures for quick and paper profiles.

## 4. Validation

- [x] 4.1 Run focused 3D eval/parity tests.
- [x] 4.2 Run `make dev`.
