## ADDED Requirements

### Requirement: 3D Boundary Orientation Normalization
The system SHALL build a closed, consistently outward-oriented boundary triangulation for a curved trimmed volume before folded quadrature is assembled.

#### Scenario: Normalize mixed-orientation boundary input
- **WHEN** boundary patches are provided with inconsistent local triangle orientation
- **THEN** the system SHALL return a deterministic outward-oriented triangle set suitable for signed volume integration

### Requirement: Seed-Based Folded Cell Construction
The system SHALL support seed-based folded decomposition in 3D where local integration cells MAY have negative Jacobians and are combined by signed contribution.

#### Scenario: Build folded cells from one seed and one boundary triangulation
- **WHEN** a valid seed and oriented boundary triangulation are provided
- **THEN** the system SHALL generate folded integration contributions that reconstruct the same domain integral as the reference orientation-aware formulation

### Requirement: 3D Quadrature Rule Export
The system SHALL export deterministic 3D quadrature nodes and weights for folded cells through a stable rule container API.

#### Scenario: Export rule for downstream use
- **WHEN** folded decomposition is completed for a volume at order `n`
- **THEN** the system SHALL provide finite node and weight arrays with repeatable ordering for the same inputs

### Requirement: Jplus and Folded Seed Policies
The system SHALL provide explicit policies for jplus and folded seed sets, including exclusion of the jplus seed from folded-best metrics.

#### Scenario: Compute best folded error without jplus contamination
- **WHEN** folded and jplus errors are evaluated over a seed grid
- **THEN** the folded-best metric SHALL be computed from non-jplus seeds only

### Requirement: 3D Folded Diagnostics
The system SHALL provide diagnostics for signed-volume reconstruction and seed-invariance checks for closed boundary triangulations.

#### Scenario: Verify seed-invariant volume
- **WHEN** signed-volume diagnostics are computed for two valid seeds on the same oriented boundary
- **THEN** the resulting domain volume SHALL match within configured tolerance
