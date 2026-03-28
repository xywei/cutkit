# cad-box-batch-interface Specification

## Purpose
TBD - created by archiving change 2026-03-26-cad-box-batch-interface. Update Purpose after archive.
## Requirements
### Requirement: Unified CAD object handles and clipping workflow
The system SHALL provide consumer-facing CAD object handles for 2D faces and 3D
solids that expose consistent axis-aligned clipping workflows.

#### Scenario: Clip one loaded CAD solid with one box
- **WHEN** a CAD solid is loaded from BREP and clipped with one axis-aligned box
- **THEN** the API SHALL return a deterministic clipped solid result usable by
  downstream boundary triangulation and folded integration helpers

### Requirement: Object-or-arrays batch box input pattern
The system SHALL support both object-style and array-style box inputs for batch
operations, with deterministic broadcasting semantics.

#### Scenario: Broadcast array-mode 3D box coordinates
- **WHEN** users provide array-mode `x0/x1/y0/y1/z0/z1` inputs that broadcast to
  a shared shape
- **THEN** the API SHALL process all broadcasted boxes and return outputs with a
  matching deterministic shape/order

#### Scenario: Object-mode and array-mode equivalence
- **WHEN** the same box set is provided once as `Sequence[Box3D]` and once as
  array-mode coordinates
- **THEN** clipping and integration outputs SHALL match within tolerance

### Requirement: Batch status reporting and strict mode
Batch workflows SHALL report explicit per-box statuses and support strict
failure behavior.

#### Scenario: Non-strict batch with invalid boxes
- **WHEN** a batch includes invalid boxes and strict mode is disabled
- **THEN** valid boxes SHALL still be processed and invalid entries SHALL return
  deterministic non-`ok` status markers

#### Scenario: Strict batch with invalid boxes
- **WHEN** a batch includes an invalid box and strict mode is enabled
- **THEN** the API SHALL raise a clear validation error instead of partial
  completion

### Requirement: Folded quadrature convenience over clipped boxes
The system SHALL provide convenience integration APIs that run folded quadrature
over one or many clipped boxes in both 2D and 3D workflows.

#### Scenario: Integrate over many clipped boxes
- **WHEN** users invoke folded integration over a box batch
- **THEN** each box result SHALL be computed deterministically using the same
  core folded quadrature kernels as single-box workflows

