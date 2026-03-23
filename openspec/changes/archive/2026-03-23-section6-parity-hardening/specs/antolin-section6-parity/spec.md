## ADDED Requirements

### Requirement: Structured Section 6 Result Manifest
The system SHALL emit a machine-readable result manifest for Section 6 reproduction runs that includes metadata, parameter profile, geometry mode, and numeric result tables.

#### Scenario: Emit manifest for default quick run
- **WHEN** the reproduction script is executed with default quick settings
- **THEN** the system SHALL produce a deterministic manifest object containing all reported Section 6 metrics

### Requirement: Mode-Aware Baseline Fixtures
The system SHALL maintain separate parity fixtures for each supported geometry mode and profile combination.

#### Scenario: Select fixture for CAD-native quick run
- **WHEN** a CAD-native quick-profile parity check is requested
- **THEN** the system SHALL load the CAD-native quick fixture rather than polygonized or paper fixtures

### Requirement: Tolerance-Based Parity Checks
The system SHALL compare current manifests against fixtures using configured absolute and relative tolerances for each metric group.

#### Scenario: Detect out-of-tolerance drift
- **WHEN** a metric differs from fixture values beyond configured tolerances
- **THEN** the parity check SHALL fail and mark the metric as a regression

### Requirement: CAD-Unavailable Behavior
The system SHALL provide deterministic parity behavior when CAD-native backends are unavailable.

#### Scenario: Run parity check without OpenCascade
- **WHEN** CAD-native parity is requested in an environment without OpenCascade
- **THEN** the system SHALL report a clear unavailable status and continue mode-appropriate checks for available paths

### Requirement: Actionable Diff Reporting
The system SHALL report parity failures with row-level and metric-level diagnostics.

#### Scenario: Print focused regression diagnostics
- **WHEN** one or more parity checks fail
- **THEN** the system SHALL report the failing section, metric key, current value, fixture value, and tolerance bounds
