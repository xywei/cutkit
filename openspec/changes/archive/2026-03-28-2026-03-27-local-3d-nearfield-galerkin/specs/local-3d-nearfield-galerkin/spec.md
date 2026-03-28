## ADDED Requirements

### Requirement: Local boxed near-field correction system assembly
The system SHALL provide local boxed correction system assembly for near-field
potential workflows with an IGA-style Galerkin method in 2D and 3D.

#### Scenario: Assemble one local correction system from restricted source support
- **WHEN** a local box, restricted source set, and supported discretization
  settings are provided in 2D or 3D
- **THEN** the workflow SHALL emit a deterministic local operator representation
  for that box (`assembled` matrix/RHS + metadata, or `matrix_free` matvec/RHS
  + metadata)

### Requirement: Dual local-operator modes for near-field correction
The local correction workflow SHALL support both assembled and matrix-free
operator modes with equivalent algebraic action within tolerance in 2D/3D.

#### Scenario: Compare assembled and matrix-free local operators
- **WHEN** equivalent local correction inputs are assembled in both
  `assembled` and `matrix_free` modes
- **THEN** operator application and solved correction outputs SHALL agree within
  configured tolerances

### Requirement: Boundary trace injection from far-field quadrature
The local correction workflow SHALL consume boundary values sampled from
far-field quadrature evaluation in matching dimension.

#### Scenario: Apply far-field boundary trace to local solve
- **WHEN** boundary trace samples are supplied on the local box boundary
- **THEN** the local solve SHALL impose those values as Dirichlet boundary data
  and produce deterministic correction outputs

### Requirement: Near-target contribution evaluation
The system SHALL evaluate local correction contributions for target points in
near-field interaction groups.

#### Scenario: Evaluate correction for self/list1/list3/list4-style targets
- **WHEN** near-target batches are passed to the local correction workflow
- **THEN** the API SHALL return deterministic per-target correction values in the
  same ordering as the input target batch

### Requirement: Object-or-arrays vectorized local correction inputs
The local correction workflow SHALL support object-mode and array-mode inputs
for local boxes, restricted source sets, and target batches in 2D/3D.

#### Scenario: Object-mode and array-mode near-correction equivalence
- **WHEN** equivalent local-box/source/target inputs are provided once in
  object-mode and once in array-mode
- **THEN** local correction outputs SHALL match within tolerance with
  deterministic row-major flattening semantics

### Requirement: Compact-support forcing couples to box basis via folded load assembly
The local correction workflow SHALL assemble forcing terms by integrating
restricted compact-support source density against box test functions over the
source support region, not over the full box volume/area.

#### Scenario: Assemble local RHS from compact trimmed support inside box
- **WHEN** `rho_near` support is a trimmed region strictly inside the local box
- **THEN** local load terms SHALL be computed from folded support quadrature as
  `b_i ~= sum_q charge_q * phi_i(y_q)` where `charge_q = rho(y_q) * w_q`

### Requirement: Dimension-independent near-field operator contract
The near-field operator API SHALL expose one shared batch contract with explicit
dimension metadata (`dim in {2,3}`).

#### Scenario: Compare 2D and 3D local operator batches
- **WHEN** local operator batches are emitted for equivalent 2D and 3D workflows
- **THEN** both outputs SHALL share one container layout (`dim`, batch pointers,
  statuses/errors, operator payload) with runtime validation of point/bounds
  arity per dimension

### Requirement: Explicit far/near composition safety
The local correction result SHALL include metadata that supports safe
combination with far-field contributions without double-counting.

#### Scenario: Compose far-field and local near-field outputs
- **WHEN** callers combine far-field and local correction contributions
- **THEN** the workflow metadata SHALL identify composition semantics needed to
  avoid duplicate near-source contributions

### Requirement: Deterministic local solve diagnostics
The system SHALL provide deterministic local solve diagnostics when CUTKIT local
solve helpers are used on assembled local systems under fixed inputs.

#### Scenario: Solve emitted local systems with CUTKIT helper
- **WHEN** a batch of assembled local systems is solved through CUTKIT helper APIs
- **THEN** solver diagnostics SHALL include deterministic free-DOF, residual,
  and iteration metadata per local system
