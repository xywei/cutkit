# folded-decomposition-2d Specification

## Purpose
TBD - created by archiving change folded-decomposition-2d-mvp. Update Purpose after archive.
## Requirements
### Requirement: Loop Orientation Normalization
The system SHALL normalize trimmed panel loops such that the outer loop is counter-clockwise and each hole loop is clockwise.

#### Scenario: Normalize mixed-orientation input
- **WHEN** a trimmed panel is provided with arbitrary loop orientations
- **THEN** the normalized panel SHALL preserve geometry while enforcing outer=ccw and holes=cw

### Requirement: Folded Signed-Triangle Decomposition
The system SHALL decompose a normalized trimmed panel into signed triangles suitable for quadrature aggregation.

#### Scenario: Decompose panel with one hole
- **WHEN** a panel with one outer loop and one hole is decomposed
- **THEN** the signed triangle set SHALL represent panel area as outer minus hole contribution

### Requirement: Panel Quadrature Rule Export
The system SHALL export panel quadrature as explicit nodes and weights in parametric coordinates.

#### Scenario: Build quadrature rule from decomposition
- **WHEN** folded decomposition is completed for a panel
- **THEN** a deterministic `QuadratureRule2D` SHALL be produced with finite nodes and weights

### Requirement: Area and Moment Verification
The system SHALL provide diagnostics for area consistency and low-order polynomial moment errors.

#### Scenario: Validate baseline cut-panel cases
- **WHEN** diagnostics are run on baseline cases
- **THEN** area consistency and configured moment-error tolerances SHALL be reported and enforceable in tests

