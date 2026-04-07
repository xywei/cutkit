## ADDED Requirements

### Requirement: IGA multipatch descriptors affect assembled operators
The system SHALL assemble deterministic numerical interface coupling
contributions when valid multipatch descriptors are supplied on backend `iga`.

#### Scenario: Multipatch descriptor changes IGA operator entries
- **WHEN** the same supported scalar form is assembled on backend `iga` with and
  without valid multipatch interface descriptors
- **THEN** the multipatch run includes deterministic interface coupling
  contributions that change operator entries while preserving deterministic
  execution metadata

### Requirement: IGA multipatch orientation mapping is deterministic
The system SHALL apply multipatch interface orientation deterministically when
mapping plus/minus interface quadrature points.

#### Scenario: Reversing interface orientation changes coupling pattern
- **WHEN** a supported interface descriptor is assembled with `orientation`
  switched between `aligned` and `reversed`
- **THEN** interface-coupling matrix contributions differ deterministically and
  payload metadata preserves the normalized orientation sign

### Requirement: IGA multipatch segment pairing failures are explicit
The system MUST fail deterministically when plus/minus interface boundaries
cannot be paired into compatible segment sets.

#### Scenario: Interface segment pairing mismatch
- **WHEN** a multipatch descriptor references plus/minus boundaries with
  mismatched segment counts or incompatible segment lengths
- **THEN** assembly raises a deterministic validation error naming the pairing
  mismatch instead of silently assembling partial coupling
