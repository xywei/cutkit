## ADDED Requirements

### Requirement: Form IR carries deterministic value-shape metadata
The system SHALL represent parsed form value shape explicitly in
`WeakFormIR.value_shape`.

#### Scenario: Parse vector mapping payload with explicit shape
- **WHEN** a caller submits a mapping payload with vector/tensor space labels
  and explicit `value_shape`
- **THEN** the parser returns `WeakFormIR` with deterministic `value_shape`
  metadata

#### Scenario: Vector labels omit explicit mapping shape
- **WHEN** a mapping payload includes vector/tensor space labels without
  `value_shape`
- **THEN** parsing fails with a deterministic payload-validation error

### Requirement: Backend capability checks include value-shape support
The system SHALL report deterministic backend capability diagnostics for
unsupported value shapes.

#### Scenario: Non-scalar shape requested on scalar-only backend
- **WHEN** assembly is requested on backend `iga` with `value_shape != ()`
- **THEN** strict capability checks fail with `unsupported_value_shape`
  diagnostic metadata

### Requirement: DG-SEM lowering preserves supported value-shape metadata
The system SHALL allow rank-1 vector value shapes for backend `dgsem` and
forward shape metadata in lowering payloads.

#### Scenario: Vector-valued DG lowering
- **WHEN** a supported form with `value_shape=(N,)` is lowered on backend
  `dgsem`
- **THEN** lowering succeeds and the DG payload includes matching
  `value_shape` metadata
