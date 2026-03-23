## Overview

This change bundles three scorecard follow-ups across the cut-panel eval and
docs-freshness quality gates.

## Design Decisions

### Failure artifact visual diff snapshots

- Add an ASCII raster snapshot payload to failure artifacts that compares two
  deterministic occupancy models:
  - parity occupancy (trimmed-panel interpretation),
  - signed occupancy (orientation-sensitive winding interpretation).
- Store a compact diff map plus summary counts so failures remain inspectable in
  plain JSON without external renderers.

### Docs anchor edge-case coverage

- Extend heading extraction beyond ATX headings to include setext headings.
- Recognize explicit HTML anchors (for example `<a id="..."></a>` and
  `<a name="..."></a>`) as valid anchor targets.
- Keep slug normalization shared between heading extraction and fragment
  normalization to preserve deterministic behavior.

### Larger corpus + deterministic fuzz minimization

- Expand imported-production and fuzz-derived fixture packs with additional
  deterministic cases.
- Add deterministic fuzz minimization helpers that:
  - canonicalize case geometry,
  - deduplicate by canonical signature,
  - rank complexity deterministically,
  - select a bounded minimized subset.
- Provide a repository script to regenerate minimized fuzz fixtures from a
  candidate pack.

## Risks and Mitigations

- **Snapshot readability**: keep legend and dimensions fixed, plus summary counts.
- **Anchor false positives**: restrict explicit-anchor parsing to clear `id`/`name`
  forms and reuse existing path filters.
- **Corpus drift**: encode minimization metadata and deterministic ordering in
  emitted fixtures.
