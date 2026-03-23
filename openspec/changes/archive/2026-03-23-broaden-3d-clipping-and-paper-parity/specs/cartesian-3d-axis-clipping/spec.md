## ADDED Requirements

### Requirement: Cartesian 3D clipping supports axis-general classification
The clipping layer SHALL classify Cartesian 3D cells for x-, y-, and z-aligned
trim intervals through one axis-general API with axis-specific wrappers.

#### Scenario: Axis-general classification matches x-wrapper behavior
- **WHEN** an x-aligned interval classification is requested through both the
  axis-general API and the x-specific wrapper
- **THEN** both return the same `outside|inside|trimmed` state

#### Scenario: Y- and Z-aligned interval states are classified correctly
- **WHEN** y- and z-aligned interval bounds place a cell fully inside, fully
  outside, or partially covered
- **THEN** the y- and z-specific wrappers return the expected classification

### Requirement: Cartesian graph-surface integration supports x/y/z axes
The quadrature layer SHALL integrate Cartesian graph-surface trim domains for
x-, y-, and z-aligned surfaces with consistent semantics.

#### Scenario: Half-cube volume is consistent across x/y/z axis modes
- **WHEN** integrating a constant integrand over half-cube trims aligned to x,
  y, and z axes
- **THEN** each axis mode returns the same expected value
