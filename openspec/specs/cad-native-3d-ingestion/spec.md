# cad-native-3d-ingestion Specification

## Purpose
TBD - created by archiving change 2026-03-24-3d-bounded-surface-refinement. Update Purpose after archive.
## Requirements
### Requirement: CAD-native 3D solid ingestion exports folded-ready boundaries
The IO layer SHALL ingest optional OpenCascade 3D solids and export boundary
face quadrature descriptors that can be normalized for folded 3D signed-volume
workflows.

#### Scenario: Build oriented boundary face quadrature from a CAD solid
- **WHEN** a valid CAD solid is provided and sampled in face parameter space
- **THEN** the system SHALL return a deterministic boundary-face quadrature set
  suitable for orientation normalization and folded-volume reconstruction

### Requirement: CAD-native 3D axis-aligned clipping
The IO layer SHALL clip CAD solids against axis-aligned boxes and expose clipped
boundary face quadrature for downstream folded integration.

#### Scenario: Reconstruct clipped box volume from folded signed boundary sum
- **WHEN** a unit CAD box is clipped by an axis-aligned half-box region and
  boundary face quadrature is extracted
- **THEN** signed-volume reconstruction over the oriented clipped boundary SHALL
  match the expected clipped volume within tolerance

### Requirement: Graceful unavailable-mode behavior
The IO layer SHALL provide explicit unavailable-mode status and raise a clear
runtime error when CAD-native 3D APIs are called without OpenCascade bindings.

#### Scenario: CAD 3D API call without OpenCascade
- **WHEN** OpenCascade bindings are unavailable in the runtime environment
- **THEN** CAD-native 3D ingest/clip API calls SHALL fail with a clear,
  actionable unavailable-backend error
