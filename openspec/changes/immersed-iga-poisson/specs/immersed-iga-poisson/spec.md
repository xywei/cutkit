## ADDED Requirements

### Requirement: Trimmed Planar Poisson Benchmark
The system SHALL provide a benchmark workflow for Poisson problems on trimmed planar geometries using CUTKIT quadrature outputs.

#### Scenario: Run planar benchmark with manufactured solution
- **WHEN** the planar benchmark runner is executed with a supported profile
- **THEN** the system SHALL produce deterministic error metrics against the manufactured reference solution

### Requirement: Trimmed Volume Poisson Benchmark
The system SHALL provide a benchmark workflow for Poisson problems on trimmed volumes using CUTKIT quadrature outputs.

#### Scenario: Run volume benchmark with manufactured solution
- **WHEN** the volume benchmark runner is executed with a supported profile
- **THEN** the system SHALL produce deterministic volume-solver error metrics against the manufactured reference solution

### Requirement: Explicit Quadrature Backend Selection
The system SHALL allow benchmark runs to declare which quadrature backend mode is used for integration.

#### Scenario: Select folded backend for benchmark run
- **WHEN** a benchmark configuration requests folded quadrature mode
- **THEN** the benchmark SHALL run with folded integration paths and record the selected mode in output metadata

### Requirement: Convergence and Acceptance Reporting
The system SHALL report convergence-relevant metrics and benchmark pass/fail status against configured acceptance thresholds.

#### Scenario: Evaluate benchmark thresholds
- **WHEN** benchmark metrics are computed for a run
- **THEN** the system SHALL mark the run as pass only if all configured thresholds are satisfied

### Requirement: Profile-Aware Execution
The system SHALL support at least one CI-friendly quick profile and one denser profile for deeper validation.

#### Scenario: Execute quick profile in CI
- **WHEN** the benchmark runner is invoked with the quick profile
- **THEN** the system SHALL complete within configured CI limits while still producing valid pass/fail metrics
