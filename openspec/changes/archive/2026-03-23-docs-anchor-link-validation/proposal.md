## Why

The docs freshness gate currently verifies path existence but does not validate
markdown heading anchors. As a result, links like `[#section]` or
`guide.md#section` can silently drift after heading edits while local and CI
quality checks still pass.

## What Changes

- Extend docs freshness checks to validate in-file anchor fragments in markdown
  links.
- Extend docs freshness checks to validate cross-file markdown anchor fragments
  when the target is a local markdown file.
- Report missing anchors with source reference and target markdown file.

## Capabilities

### Modified Capabilities
- `docs-cross-reference-freshness`: now validates markdown heading anchors in
  addition to path existence.

### New Capabilities
- None.

## Impact

- Affected code:
  - `src/cutkit/docs_freshness.py`
  - `scripts/check_docs_freshness.py`
  - `tests/test_docs_freshness.py`
- No new third-party dependencies expected.
