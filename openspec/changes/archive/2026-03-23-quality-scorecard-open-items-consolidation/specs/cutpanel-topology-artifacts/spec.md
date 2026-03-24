## ADDED Requirements

### Requirement: Failure artifacts include visual diff snapshots
Failed cut-panel evaluations SHALL export deterministic visual diff snapshots in
artifact payloads.

#### Scenario: Failure artifact includes visual diff metadata
- **WHEN** exporting a failed cut-panel evaluation artifact
- **THEN** the artifact includes a visual snapshot section with fixed grid
  dimensions, legend, summary counts, and raster lines

#### Scenario: Snapshot highlights orientation-sensitive mismatches
- **WHEN** a case fails due orientation-sensitive topology issues
- **THEN** the visual diff section includes mismatch markers where parity and
  signed occupancy disagree
