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
