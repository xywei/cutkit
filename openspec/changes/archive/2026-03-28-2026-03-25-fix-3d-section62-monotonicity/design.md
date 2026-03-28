## Context

The 3D Section 6.2 workflow integrates over Cartesian cut-cells using a curved
surface graph callback `x_s(y,z)`. The existing inversion routine may select a
single local branch in folded projection regions, which can destabilize
high-resolution rows and produce non-monotone error sequences.

## Goals / Non-Goals

**Goals**

- Make `x_s(y,z)` inversion robust and deterministic across folded projection
  regions.
- Ensure paper-profile 3D Section 6.2 rows are monotone non-increasing.
- Remove stale caveat messaging once corrected.

**Non-Goals**

- Redesigning the Section 6.2 protocol beyond this monotonicity/parity fix.
- Singular/near-singular quadrature additions.

## Decisions

1. Use deterministic multi-start Newton inversion in `(u,v)` space.
2. Collect converged `x` candidates and select the lower-envelope branch
   (`min(x)`), matching the trimmed-volume lower boundary used by the protocol.
3. Use paper-profile 3D grid sweep `(4, 8, 16)` for stable refinement rows.

## Validation Plan

- Add targeted tests for lower-envelope branch selection behavior.
- Verify 3D paper-profile rows report monotone non-increasing diagnostics.
- Regenerate parity fixtures and run full `make dev`.
