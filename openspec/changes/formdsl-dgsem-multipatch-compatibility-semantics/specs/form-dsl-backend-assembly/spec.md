## ADDED Requirements

### Requirement: DG-SEM multipatch strict mode remains fail-fast
The system SHALL continue to reject multipatch descriptors on backend `dgsem`
in strict mode.

#### Scenario: Strict DG-SEM multipatch request
- **WHEN** a form with multipatch descriptors is assembled on `dgsem` with
  `strict=True`
- **THEN** capability validation fails with
  `unsupported_multipatch_interface`

### Requirement: DG-SEM multipatch permissive diagnostics are compatibility-aware
The system SHALL emit deterministic compatibility diagnostics for DG-SEM
multipatch requests in permissive mode.

#### Scenario: Permissive DG-SEM multipatch request with orientation variants
- **WHEN** a multipatch descriptor on `dgsem` includes `reversed` orientation
  interfaces and `strict=False`
- **THEN** diagnostics include a DG-SEM compatibility code describing
  unsupported orientation semantics

#### Scenario: Permissive DG-SEM multipatch request with per-interface penalties
- **WHEN** a multipatch descriptor on `dgsem` includes per-interface `penalty`
  controls and `strict=False`
- **THEN** diagnostics include a DG-SEM compatibility code describing
  unsupported per-interface coupling controls
