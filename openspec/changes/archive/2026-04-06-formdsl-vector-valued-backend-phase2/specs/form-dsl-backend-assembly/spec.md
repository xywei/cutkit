## ADDED Requirements

### Requirement: DG-SEM vector lowering emits component-aware plans
The system SHALL emit deterministic component-aware DG-SEM lowering entries for
rank-1 vector forms.

#### Scenario: Rank-1 vector form lowering
- **WHEN** a supported rank-1 vector form is lowered for backend `dgsem`
- **THEN** the lowering payload includes deterministic per-component lowering
  structure in a stable component order

### Requirement: Vector source lowering is deterministic
The system SHALL define deterministic lowering semantics for rank-1 vector
source terms.

#### Scenario: Vector source parse and lower
- **WHEN** a supported rank-1 vector source is parsed and lowered for
  backend `dgsem`
- **THEN** source metadata and lowering entries are reproducible across runs and
  strict/permissive diagnostics remain deterministic
