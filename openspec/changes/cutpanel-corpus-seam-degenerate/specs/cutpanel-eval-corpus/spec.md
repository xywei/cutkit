## ADDED Requirements

### Requirement: Default corpus includes seam-adjacent and near-degenerate panels
The cut-panel evaluation harness SHALL include deterministic default cases that
exercise seam-adjacent holes and near-degenerate trimmed regions.

#### Scenario: Seam-adjacent and near-degenerate cases are part of default eval
- **WHEN** `run_default_eval()` executes
- **THEN** the result set includes named seam-adjacent and near-degenerate cases
- **AND** those cases produce passing validation results under default
  tolerances

### Requirement: Seam-touching topology remains invalid
The topology validator SHALL reject seam-touching hole geometry so seam
adjacency and seam contact are not conflated.

#### Scenario: Hole touching outer seam fails validation
- **WHEN** a panel hole touches the outer boundary seam
- **THEN** validation reports a topology error indicating the hole is not
  strictly inside and/or intersects the outer loop boundary
