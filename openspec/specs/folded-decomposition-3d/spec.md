# folded-decomposition-3d Specification

## Purpose
TBD - created by archiving change 2026-03-24-3d-bounded-surface-refinement. Update Purpose after archive.
## Requirements
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

### Requirement: 3D Section 6.2 grid rows are monotone under paper-profile settings
The 3D Section 6.2 reproduction protocol SHALL report monotone non-increasing
grid-refinement error rows for configured paper-profile orders.

#### Scenario: Run paper-profile 3D Section 6.2 sweep
- **WHEN** the paper-profile 3D Section 6.2 grid experiment is run
- **THEN** each order row SHALL be marked monotone non-increasing with no
  violation indices

### Requirement: Deterministic lower-envelope `x_s(y,z)` selection
The curved-surface projection inversion SHALL deterministically select the lower
`x` branch when multiple converged candidates are present for a sampled `(y,z)`.

#### Scenario: Multiple converged projection candidates
- **WHEN** inversion yields more than one valid `x` candidate for the same
  `(y,z)` sample
- **THEN** the selected `x_s(y,z)` SHALL be the minimum converged candidate

