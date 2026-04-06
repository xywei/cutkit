# form-dsl-backend-assembly Specification

## Purpose
Define requirements for UFL-authored scalar form assembly across IGA and
meshmode+grudge DG-SEM backends with deterministic diagnostics and parity
validation.
## Requirements
### Requirement: UFL-authored forms are accepted for trimmed-domain assembly
The system SHALL provide an API that accepts UFL-authored weak forms and
builds a method-neutral intermediate representation for CUTKIT assembly
backends.

#### Scenario: Parse supported scalar form
- **WHEN** a caller submits a supported scalar UFL form with declared trial/test
  spaces and coefficients
- **THEN** the system returns a deterministic IR payload with no backend-specific
  terms embedded

### Requirement: Backend support is explicitly phased and capability-gated
The system SHALL expose a backend capability matrix and deterministic diagnostics
for terms unsupported by the selected backend or release phase.

#### Scenario: Request term outside current release subset
- **WHEN** a caller submits a valid UFL form containing terms outside the
  current supported subset
- **THEN** lowering fails with an explicit capability diagnostic naming backend,
  term class, and supported alternatives

### Requirement: IGA backend assembles from shared form IR
The system SHALL lower supported IR forms to CUTKIT IGA assembly using trimmed
quadrature and spline basis evaluation.

#### Scenario: Assemble Poisson-like bilinear form
- **WHEN** a supported diffusion form is lowered with backend `iga`
- **THEN** the system emits deterministic operator payloads and RHS consistent
  with trimmed-domain quadrature semantics

### Requirement: DG-SEM backend assembles from shared form IR through meshmode+grudge
The system SHALL lower supported IR forms to meshmode+grudge DG-SEM operator
construction with explicit trace/flux handling.

#### Scenario: Assemble shared form on DG backend
- **WHEN** the same supported form is lowered with backend `dgsem`
- **THEN** the system emits DG-SEM-ready assembly payloads and diagnostics using
  meshmode+grudge integration contracts

#### Scenario: DG-SEM backend requested before overlay prerequisite is available
- **WHEN** backend `dgsem` is requested without required meshmode overlay
  contract availability
- **THEN** lowering fails with an explicit prerequisite diagnostic instead of
  attempting implicit payload translation

### Requirement: Backend capability mismatches are explicit and deterministic
The system MUST detect unsupported terms for each backend and return actionable
diagnostics instead of silent fallback behavior.

#### Scenario: Unsupported term in DG backend
- **WHEN** a form includes a term outside DG-SEM support in the current release
- **THEN** lowering fails with a deterministic unsupported-term diagnostic
  identifying term category and backend

### Requirement: Shared-form backend parity is testable
The system SHALL provide validation coverage demonstrating that supported forms
run on both backends with expected convergence behavior.

#### Scenario: Manufactured solution backend comparison
- **WHEN** the same manufactured problem is assembled and solved using both
  `iga` and `dgsem` backend paths
- **THEN** each backend satisfies its expected convergence/order threshold and
  emits reproducible diagnostics for comparison

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

### Requirement: Geometry-map capability checks are deterministic
The system SHALL validate requested geometry maps against backend capabilities
and emit deterministic diagnostics for unsupported combinations.

#### Scenario: Unsupported geometry map on backend
- **WHEN** a form requests `geometry_map=nurbs` on backend `dgsem`
- **THEN** strict capability checks fail with `unsupported_geometry_map` and
  permissive mode surfaces the same diagnostic in assembly results

### Requirement: IGA accepts single-patch NURBS geometry-map metadata
The system SHALL accept `geometry_map=nurbs` for backend `iga` in the current
single-patch MVP.

#### Scenario: IGA lowering with NURBS geometry map
- **WHEN** a supported scalar form is assembled on backend `iga` with
  `metadata.geometry_map=nurbs`
- **THEN** lowering succeeds and payload metadata records geometry map `nurbs`

