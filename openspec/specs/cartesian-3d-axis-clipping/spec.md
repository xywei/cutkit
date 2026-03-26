# cartesian-3d-axis-clipping Specification

## Purpose
TBD - created by archiving change 2026-03-24-3d-bounded-surface-refinement. Update Purpose after archive.
## Requirements
### Requirement: Cartesian graph-surface integration supports x/y/z axes
The quadrature layer SHALL integrate Cartesian graph-surface trim domains for
x-, y-, and z-aligned surfaces with consistent semantics.

#### Scenario: Half-cube volume is consistent across x/y/z axis modes
- **WHEN** integrating a constant integrand over half-cube trims aligned to x,
  y, and z axes
- **THEN** each axis mode returns the same expected value

#### Scenario: Bounded slab integration uses lower and upper trim surfaces
- **WHEN** lower and upper axis-aligned trim surfaces define a bounded interval
  inside each orthogonal column
- **THEN** integration is performed only over that bounded interval

#### Scenario: Unbounded side defaults to the unit-cube boundary
- **WHEN** either lower or upper bounded-surface callback returns `None`
- **THEN** that side defaults to `0` (lower) or `1` (upper) for bounded
  integration semantics

