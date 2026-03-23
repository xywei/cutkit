## ADDED Requirements

### Requirement: Anchor freshness checks cover renderer-style edge headings
Docs freshness validation SHALL support additional heading/anchor patterns used
by common markdown renderers.

#### Scenario: Setext heading anchors are recognized
- **WHEN** a markdown file defines a setext heading and another link targets its
  corresponding anchor fragment
- **THEN** docs freshness validation treats that anchor as valid

#### Scenario: Explicit HTML anchors are recognized
- **WHEN** a markdown file defines explicit HTML anchor tags with `id` or `name`
  attributes and a link targets those fragments
- **THEN** docs freshness validation treats those anchors as valid
