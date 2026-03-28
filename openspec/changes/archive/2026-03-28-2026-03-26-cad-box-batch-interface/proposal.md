## Why

CUTKIT now has the core pieces for CAD-native ingestion, axis-aligned box
clipping, folded decomposition, and parity validation. However, consumers still
need to stitch low-level APIs together across multiple modules and manually
manage loops for many boxes.

We need one consumer-facing interface that supports both object-style inputs and
array-style batch inputs so users can process many clip boxes in one call and
run folded quadrature workflows deterministically.

## What Changes

- Add a new consumer-facing CAD workflow facade with typed geometry handles and
  axis-aligned box value objects for 2D and 3D.
- Add an "object or arrays" batch box interface with deterministic broadcasting
  and output shape semantics.
- Add batch clipping and folded quadrature convenience APIs that operate on one
  or many boxes with identical behavior.
- Add explicit per-box status reporting (`ok`, `empty`, `invalid_box`,
  `backend_error`) and `strict` mode behavior.
- Add tests and docs for single-box and batch workflows.

## Capabilities

### New Capabilities

- `cad-box-batch-interface`: unified CAD ingest/clip/integrate interface with
  object-or-arrays batch input semantics.

### Modified Capabilities

- `cad-native-3d-ingestion`: expands from low-level solid ingest/clip helpers to
  consumer-facing batch clipping workflows.
- `folded-decomposition-2d`: adds consumer-facing folded quadrature convenience
  over boxed clipping results.
- `folded-decomposition-3d`: adds consumer-facing folded quadrature convenience
  over clipped boundary triangulations.

## Impact

- Affected code:
  - new consumer facade module(s) under `src/cutkit/`
  - `src/cutkit/io/__init__.py` (exports/wiring)
  - folded quadrature integration plumbing in `src/cutkit/quadrature/`
  - tests for new API semantics under `tests/`
  - README/docs usage examples
- No mandatory dependency changes expected.
