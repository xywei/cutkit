## ADDED Requirements

### Requirement: 3D Boundary Orientation Normalization
The system SHALL build a closed, consistently outward-oriented boundary
triangulation for a curved trimmed volume before folded quadrature is assembled.

#### Scenario: Section 6.1.3 boundary builder supports side-face refinement
- **WHEN** Section 6.1.3 boundary triangles are generated with
  `side_resolution > 1`
- **THEN** the resulting triangulation remains orientation-consistent for signed
  volume reconstruction

#### Scenario: Refined side meshes preserve seed-invariant signed volume
- **WHEN** signed domain volume is reconstructed from two valid seeds on a
  side-refined Section 6.1.3 boundary triangulation
- **THEN** both reconstructions match within tolerance and remain positive
