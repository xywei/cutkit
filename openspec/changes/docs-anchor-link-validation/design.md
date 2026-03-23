## Overview

This change extends docs freshness from path-level checks to anchor-level checks
for markdown links.

## Design Decisions

### Anchor reference scope

- Validate anchors only for markdown link targets (`[text](...)`), not generic
  inline code tokens.
- Support both in-file (`#anchor`) and cross-file (`file.md#anchor`) links.
- Skip anchors for external URLs and non-markdown targets.

### Anchor normalization

- Normalize link fragments and heading text with a shared slugification routine.
- Use deterministic duplicate-heading suffix behavior (`-1`, `-2`, ...).
- Decode percent-encoded fragments before normalization.

### Heading extraction

- Parse ATX-style headings (`#` through `######`) from markdown text.
- Ignore headings inside fenced code blocks.
- Cache per-file extracted anchors during a scan to avoid repeated reparsing.

### Error reporting

- Keep existing missing-path reports unchanged.
- Report missing anchors distinctly with source reference, missing anchor, and
  target markdown file.

## Risks and Mitigations

- **Anchor algorithm mismatch**: use a single normalization path for both link
  fragments and headings to keep behavior consistent.
- **False positives from vendored docs**: continue excluding non-source
  directories (including `node_modules`) from default scan scope.
- **Performance overhead**: cache extracted anchors for target files within each
  run.
