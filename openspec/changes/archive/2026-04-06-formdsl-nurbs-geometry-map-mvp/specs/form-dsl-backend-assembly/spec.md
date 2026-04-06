## ADDED Requirements

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
