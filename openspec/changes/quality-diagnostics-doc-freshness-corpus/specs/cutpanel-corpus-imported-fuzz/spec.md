## ADDED Requirements

### Requirement: Default cut-panel corpus includes imported-production fixtures
The default cut-panel corpus SHALL include deterministic imported-production
cases from fixture-backed definitions.

#### Scenario: Imported-production cases appear in default corpus
- **WHEN** requesting default cut-panel cases
- **THEN** at least one case tagged as imported-production is included

### Requirement: Default cut-panel corpus includes fuzz-derived edge cases
The default cut-panel corpus SHALL include deterministic fuzz-derived cases that
exercise topology-sensitive boundaries.

#### Scenario: Fuzz-derived cases appear in default corpus
- **WHEN** requesting default cut-panel cases
- **THEN** at least one case tagged as fuzz-derived is included
