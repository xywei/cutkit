## ADDED Requirements

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
