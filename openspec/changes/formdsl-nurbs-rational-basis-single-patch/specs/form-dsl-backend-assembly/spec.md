## ADDED Requirements

### Requirement: IGA NURBS lowering uses deterministic rational execution internals
When `geometry_map=nurbs` is requested on backend `iga`, lowering SHALL use a
deterministic single-patch rational execution path.

#### Scenario: Single-patch NURBS form lowers through rational path
- **WHEN** a supported scalar form is assembled on backend `iga` with
  `metadata.geometry_map=nurbs`
- **THEN** lowering succeeds through the rational execution path and payload
  metadata records deterministic NURBS execution semantics

### Requirement: B-spline path remains stable when NURBS is not requested
The system SHALL preserve existing scalar B-spline lowering behavior for IGA
when `geometry_map` is omitted or set to `bspline`.

#### Scenario: Default B-spline form is unaffected by NURBS internals
- **WHEN** a supported scalar form is assembled on backend `iga` without
  `metadata.geometry_map=nurbs`
- **THEN** lowering behavior and payload semantics remain consistent with the
  prior B-spline path
