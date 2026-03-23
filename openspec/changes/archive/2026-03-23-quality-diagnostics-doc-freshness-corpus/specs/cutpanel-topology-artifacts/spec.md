## ADDED Requirements

### Requirement: Cut-panel evaluations expose structured topology diagnostics
The cut-panel evaluation path SHALL provide machine-readable topology
diagnostics in addition to human-readable error strings.

#### Scenario: Topology diagnostics include loop and intersection state
- **WHEN** validating a panel case
- **THEN** the result includes structured diagnostics for outer/hole orientation,
  signed-area magnitude, self-intersection status, containment/intersection, and
  hole-overlap relationships

### Requirement: Failed cut-panel cases can be exported as JSON artifacts
The cut-panel evaluation script SHALL support writing failure artifacts that
contain case geometry, computed metrics, topology diagnostics, and errors.

#### Scenario: Failure artifacts are written for failing cases
- **WHEN** one or more cases fail validation and an artifact output directory is
  provided
- **THEN** one JSON artifact per failing case is written with deterministic
  filenames and the required diagnostic fields
