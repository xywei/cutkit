# volumential-signed-source-cloud Specification

## Purpose
TBD - created by archiving change 2026-03-27-volumential-signed-source-cloud. Update Purpose after archive.
## Requirements
### Requirement: Signed folded source-cloud export for trimmed clipped regions
The system SHALL export deterministic signed point-source clouds from trimmed
clipped regions using folded quadrature rules in both 2D and 3D.

#### Scenario: Build folded source cloud from one clipped source region
- **WHEN** a clipped 2D or 3D source region and source-density function are provided
- **THEN** the API SHALL return point locations, signed quadrature weights, and
  per-point charges where each charge equals density times signed weight

### Requirement: Deterministic object-or-arrays batching semantics
The system SHALL support object-mode and array-mode source-region workflows with
deterministic ordering and shape metadata.

#### Scenario: Build source cloud over a broadcasted box batch
- **WHEN** users request source-cloud generation for a valid box batch
- **THEN** outputs SHALL preserve deterministic row-major ordering and include
  source-to-box index metadata for every generated point

#### Scenario: Object-mode and array-mode source-cloud equivalence
- **WHEN** the same source-region set is provided once as `Sequence[Box2D]` or
  `Sequence[Box3D]` and once via array-mode coordinates
- **THEN** generated source-cloud outputs SHALL match within tolerance after
  deterministic flattening

### Requirement: Dimension-independent source-cloud contract
Source-cloud containers SHALL carry explicit dimension metadata and present one
consistent flat-batch contract for 2D and 3D workflows.

#### Scenario: Compare 2D and 3D source-cloud container layout
- **WHEN** source clouds are built for 2D and 3D clipped inputs
- **THEN** both outputs SHALL expose a shared contract shape (`dim`, `point_ptr`,
  flat points/weights/charges, statuses/errors) with dimension-specific point
  arity validated by runtime checks

### Requirement: Explicit backend-mode visibility in source-cloud metadata
Source-cloud outputs SHALL expose which folded backend mode generated the cloud.

#### Scenario: Generate source clouds in jplus and folded modes
- **WHEN** source-cloud generation is run in either backend mode
- **THEN** result metadata SHALL include the selected mode and remain
  deterministic for repeated runs under that mode

### Requirement: Volumential-ready source-cloud materialization
The system SHALL provide an adapter surface that materializes source clouds into
volumential-friendly point/charge arrays.

#### Scenario: Materialize source cloud for external point-potential evaluation
- **WHEN** a signed source cloud is exported through the adapter
- **THEN** the resulting arrays SHALL preserve signed charges and be consumable
  without additional geometric reconstruction steps

