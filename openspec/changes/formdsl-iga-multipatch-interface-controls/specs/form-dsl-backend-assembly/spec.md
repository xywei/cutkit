## ADDED Requirements

### Requirement: Multipatch interface descriptors accept optional penalties
The system SHALL accept optional finite positive per-interface penalty values in
multipatch interface descriptors.

#### Scenario: Parse interface descriptor with penalty
- **WHEN** a multipatch interface descriptor includes a valid numeric positive
  `penalty`
- **THEN** parsing succeeds and IR retains the per-interface penalty value

### Requirement: IGA multipatch coupling applies deterministic penalty precedence
The system SHALL use per-interface `penalty` when present and otherwise fall
back to global `multipatch_penalty` metadata.

#### Scenario: Interface penalty overrides global penalty
- **WHEN** a form provides both global `multipatch_penalty` metadata and a
  specific interface `penalty`
- **THEN** that interface uses its own penalty value during coupling assembly
  and payload metadata reports the effective value

### Requirement: Invalid interface penalties fail deterministically
The system MUST reject malformed per-interface penalties with deterministic
validation errors.

#### Scenario: Non-finite or non-positive interface penalty
- **WHEN** a multipatch interface descriptor specifies `penalty` that is
  non-numeric, non-finite, or non-positive
- **THEN** parsing or IR validation fails with deterministic error metadata
  naming the invalid penalty field
