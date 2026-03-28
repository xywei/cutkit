# immersed-poisson-galerkin-solver Specification

## Purpose
TBD - created by archiving change 2026-03-25-immersed-poisson-galerkin-solver. Update Purpose after archive.
## Requirements
### Requirement: Trimmed-domain immersed Poisson Galerkin solve
The system SHALL assemble and solve a trimmed-domain immersed tensor-product
B-spline (IGA-style) Poisson Galerkin system using CUTKIT clipping and
quadrature workflows.

#### Scenario: Solve Poisson system on Section 6.1.1 trimmed geometry
- **WHEN** the immersed solver is run with a supported resolution and backend
  mode
- **THEN** it SHALL return deterministic solver diagnostics including free-DOF
  count, residual norm, and iteration count

### Requirement: Explicit backend selection for solver assembly
The system SHALL support explicit jplus and folded quadrature modes for immersed
solver assembly.

#### Scenario: Run solver benchmark in folded mode
- **WHEN** folded backend mode is requested
- **THEN** assembly SHALL use folded trimmed-cell integration and report folded
  benchmark rows in output metadata

### Requirement: Solver-level reference validation
The system SHALL provide profile-driven solver validation against a fine-grid
reference solve with deterministic error reporting.

#### Scenario: Evaluate solver benchmark profile
- **WHEN** a solver benchmark profile is executed
- **THEN** output SHALL include per-resolution absolute/relative error rows and
  profile-threshold pass/fail status

### Requirement: Paper-style figure-pack generation
The system SHALL generate deterministic paper-style figure packs from immersed
Poisson Galerkin workflows, including geometry, cell classification, solution,
and convergence plots.

#### Scenario: Generate SVG figure pack for jplus and folded runs
- **WHEN** Poisson Galerkin figure-pack generation is invoked for a benchmark
  profile
- **THEN** geometry, cell classification, solution-field, and
  absolute/relative-error SVG artifacts SHALL be produced using reusable
  visualization helpers in `src/`

