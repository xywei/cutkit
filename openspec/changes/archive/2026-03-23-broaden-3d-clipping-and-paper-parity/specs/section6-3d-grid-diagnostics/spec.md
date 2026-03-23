## ADDED Requirements

### Requirement: Section 6.2 3D grid runs expose monotonicity diagnostics
Section 6.2 3D Cartesian refinement results SHALL include monotonicity metadata
for each order row.

#### Scenario: Monotone row reports no violations
- **WHEN** an order row has non-increasing absolute error as grid resolution
  increases
- **THEN** diagnostics mark the row monotone and report zero violation indices

#### Scenario: Non-monotone row reports explicit violation indices
- **WHEN** an order row has a refinement step where absolute error increases
- **THEN** diagnostics mark the row non-monotone and list the violating
  pair-index positions
