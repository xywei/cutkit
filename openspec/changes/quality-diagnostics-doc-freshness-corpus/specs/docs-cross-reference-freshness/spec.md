## ADDED Requirements

### Requirement: Docs cross-reference paths must be fresh
Repository docs SHALL be checked for stale local cross-reference paths.

#### Scenario: Missing referenced path fails checker
- **WHEN** a markdown cross-reference points to a file or directory that does
  not exist
- **THEN** the docs freshness checker exits non-zero and reports the missing
  reference with source location

### Requirement: Docs freshness checker is enforced by quality gates
The repository quality workflow SHALL run docs freshness checks in local and CI
flows.

#### Scenario: Quality gate includes docs freshness
- **WHEN** running standard quality commands (`make check` or equivalent CI
  hooks)
- **THEN** docs freshness validation runs and can fail the workflow
