# CUTKIT

**Cut-cell Utilities for Trimming, Kernel Integration, and Topology**

Topology-aware cut-cell utilities for trimmed-domain kernel integration.

## Scope

CUTKIT focuses on a geometry/cut layer that complements `meshmode` and `modepy`:

- trimmed patch loop handling (outer loops, holes, orientation)
- cut-cell classification and clipping in parametric space
- robust integration helpers for regular cut panels
- diagnostics for cut topology and quadrature quality

## Non-goals (for now)

- replacing singular/near-singular QBX evaluation in `pytential`
- being a full CAD kernel

## Development Status

Early bootstrap. APIs may change.

## License

MIT. See `LICENSE`.
