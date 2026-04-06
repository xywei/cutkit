## ADDED Requirements

### Requirement: Form IR accepts deterministic multipatch descriptors
The system SHALL parse and retain explicit multipatch identifiers and interface
descriptors in form IR metadata for supported scalar forms.

#### Scenario: Parse supported multipatch descriptor payload
- **WHEN** a caller submits a supported form payload containing multipatch
  metadata with patch identifiers and interface descriptors
- **THEN** parsing succeeds and returns deterministic IR metadata with stable
  descriptor ordering and required orientation fields

### Requirement: IGA backend lowers supported multipatch interface couplings
The system SHALL lower supported multipatch interface couplings on backend
`iga` using deterministic interface orientation handling.

#### Scenario: Assemble multipatch interface coupling on IGA backend
- **WHEN** a supported scalar form includes valid multipatch interface
  descriptors and backend `iga` is requested
- **THEN** assembly succeeds with deterministic interface contribution ordering
  and payload metadata records a multipatch execution path

### Requirement: Multipatch diagnostics are deterministic across modes
The system MUST report deterministic diagnostics for malformed multipatch
descriptors and unsupported backend combinations.

#### Scenario: Unsupported multipatch interface on DG-SEM backend
- **WHEN** a form includes multipatch interface descriptors and backend `dgsem`
  is requested
- **THEN** strict checks fail with `unsupported_multipatch_interface` and
  permissive mode records the same diagnostic in assembly results

#### Scenario: Malformed multipatch descriptor key
- **WHEN** a multipatch interface descriptor omits a required neighbor patch or
  orientation key
- **THEN** parse/lowering fails with deterministic payload-validation metadata
  naming the missing key
