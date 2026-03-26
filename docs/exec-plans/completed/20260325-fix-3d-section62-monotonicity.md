# Fix 3D Section 6.2 Monotonicity

## Objective

Eliminate the known non-monotonic 3D Section 6.2 grid-convergence rows in the
paper-reproduction workflow and close this remaining paper-parity gap.

## Scope

- Improve `x_s(y,z)` inversion robustness for Section 6.1.3 curved-surface
  projection in 3D Section 6.2 grid integration.
- Ensure the paper-profile 3D grid sweep reports monotone non-increasing rows.
- Update reproduction docs and script messaging to remove known non-monotonic
  caveat once fixed.
- Refresh parity fixtures to the corrected protocol outputs.

## Acceptance Criteria

- 3D Section 6.2 rows in the paper profile are monotone non-increasing.
- README/script output no longer describes the 3D Section 6.2 rows as known
  non-monotonic.
- Parity fixtures are regenerated to match corrected outputs.
- Focused tests and `make dev` pass.

## Implementation Checklist

- [x] Add OpenSpec change artifacts for Section 6.2 3D monotonicity fix.
- [x] Implement robust multi-start lower-envelope `x_s(y,z)` inversion.
- [x] Adjust paper-profile 3D Section 6.2 grid sweep to stable monotone range.
- [x] Update tests and docs for corrected monotonic behavior.
- [x] Regenerate parity fixtures.
- [x] Run focused checks and `make dev`.

## Final Outcome

- Status: completed; ready for review.
- 3D Section 6.2 paper-profile rows now report monotone non-increasing behavior.
- README/script caveat text about known non-monotonic rows was removed/updated.
- Parity fixtures refreshed for quick and antolin-paper polygonized full scopes.
