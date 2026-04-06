# meshmode-cut-overlay Specification

## Purpose
Define requirements for deterministic CUTKIT-to-meshmode cut-overlay contracts
with strict/permissive validation and downstream DG-SEM adapter consumption.

## Requirements
### Requirement: Build meshmode overlay from CUTKIT integration outputs
The system SHALL provide an API that constructs meshmode-compatible cut-overlay data from CUTKIT trimmed-domain integration outputs using explicit mapping inputs.

#### Scenario: Overlay construction succeeds with valid mapping
- **WHEN** a caller provides valid CUTKIT integration payloads and a consistent element mapping contract
- **THEN** the system returns an overlay result containing per-element indices, integration weights, geometry metadata, and status entries without requiring caller-side reshaping logic

### Requirement: Overlay contract is versioned and deterministically ordered
The system SHALL expose an explicit overlay contract version and deterministic
ordering rules for payload arrays so repeated generation is reproducible across
platforms.

#### Scenario: Regenerating overlay payloads on different platforms
- **WHEN** equivalent inputs are processed on different supported runtime
  environments
- **THEN** emitted overlay ordering and status payloads are identical for a given
  contract version

### Requirement: Overlay results expose deterministic per-element statuses
The system SHALL report per-element status outcomes for overlay generation, including successful, empty, and error categories, without collapsing the batch into a single global status.

#### Scenario: Batch includes mixed valid and invalid elements
- **WHEN** overlay construction is requested for a batch where some elements map cleanly and others fail validation
- **THEN** the system returns a result object that preserves successful element overlays and records deterministic status/error details for each failed element

### Requirement: Overlay validation detects mapping and orientation mismatches
The system MUST validate index-space and orientation assumptions between CUTKIT payloads and meshmode target layout before finalizing overlay output.

#### Scenario: Element index map does not align
- **WHEN** provided mapping inputs reference element identifiers not present in CUTKIT payloads or meshmode targets
- **THEN** the system marks affected entries with a mapping mismatch status and includes actionable diagnostic metadata identifying missing or conflicting identifiers

#### Scenario: Orientation convention mismatch is detected
- **WHEN** geometric orientation checks indicate incompatible orientation conventions for mapped entities
- **THEN** the system emits an orientation mismatch status and diagnostic details for the affected overlay entries

### Requirement: Validation behavior supports strict and permissive execution modes
The system SHALL support strict and permissive validation modes for overlay assembly, with strict mode enforcing fail-fast behavior and permissive mode allowing partial-success outputs.

#### Scenario: Strict mode rejects mismatched input
- **WHEN** strict mode is enabled and validation encounters a mapping or orientation mismatch
- **THEN** the system fails the overlay build operation and returns error context describing the first blocking violation

#### Scenario: Permissive mode returns partial results
- **WHEN** permissive mode is enabled and validation encounters a subset of mismatched elements
- **THEN** the system returns overlays for valid elements and status diagnostics for invalid elements in one result payload

### Requirement: Overlay payloads are consumable by downstream backend adapters
The system SHALL provide payload fields sufficient for downstream assembly
adapters (including DG-SEM workflows) without requiring implicit positional
assumptions.

#### Scenario: Downstream adapter consumes overlay payload directly
- **WHEN** a backend adapter consumes the overlay result
- **THEN** it can construct backend-local assembly structures using explicit
  mapping/status metadata without custom reverse-engineered reshaping
