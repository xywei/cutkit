## ADDED Requirements

### Requirement: Docs markdown anchor references must be fresh
Repository docs SHALL be checked for stale markdown heading anchor references.

#### Scenario: Missing in-file anchor fails checker
- **WHEN** a markdown link references `#anchor` in the same file and no matching
  heading anchor exists
- **THEN** the docs freshness checker exits non-zero and reports the missing
  anchor and source reference

#### Scenario: Missing cross-file anchor fails checker
- **WHEN** a markdown link references `target.md#anchor` and `target.md` exists
  but has no matching heading anchor
- **THEN** the docs freshness checker exits non-zero and reports the missing
  anchor and target markdown file
