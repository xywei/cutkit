## ADDED Requirements

### Requirement: Default imported/fuzz packs provide broader deterministic coverage
The default cut-panel corpus SHALL include larger deterministic imported and
fuzz-derived fixture packs.

#### Scenario: Expanded fixture packs are loaded by default corpus
- **WHEN** evaluating default cut-panel cases
- **THEN** imported-production and fuzz-derived fixture groups each contribute
  multiple deterministic entries beyond the prior baseline set

### Requirement: Deterministic fuzz minimization workflow is available
The repository SHALL provide a deterministic workflow to minimize fuzz candidate
fixtures into the checked-in fuzz-derived corpus.

#### Scenario: Minimization output is reproducible
- **WHEN** running the fuzz minimization workflow with the same input and options
- **THEN** emitted fixture payload ordering and selected cases are identical
