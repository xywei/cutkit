# Folded Decomposition Follow-ups

This note tracks follow-up work intentionally out of scope for the 2D MVP.

## Priority Follow-ups

1. Singular and near-singular kernel quadrature extensions.
2. Downstream adapter into `volumential` rule-consumption paths.

## Singular Quadrature Status

- CUTKIT currently focuses on regular-volume/regular-boundary folded integration.
- Singular and near-singular kernel quadrature (including QBX/QBFEM-style
  treatments) remains explicitly deferred follow-up work.
- The Antolin-Wei-Buffa (2022) Section 6 reproduction target in this repository
  is treated as a regular integration benchmark; the paper source we audited did
  not provide a dedicated singular/near-singular quadrature protocol to mirror.

## CAD Core

OpenCascade is now the designated CAD core for exact 2D Section 6 clipping
workflows and CAD-native 3D solid ingest/axis-aligned clipping adapters.

Recent 3D broadening now in-tree:

- axis-general Cartesian graph-surface integration includes bounded-slab support
  between lower/upper trim surfaces;
- Section 6.1.3 boundary builder supports side-face refinement beyond
  `side_resolution=1`;
- CAD-native 3D solid ingestion supports triangulated oriented boundary export
  and axis-aligned box clipping hooks.

## Rationale

The MVP establishes a deterministic and testable 2D folded core first.
The follow-ups above extend representation coverage and solver-facing accuracy
without blocking the initial architecture-aligned implementation.
