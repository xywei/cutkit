# CAD Box Batch Interface

## Objective

Design and implement a consumer-facing CAD workflow interface that supports both
single-box and many-box operations through an object-or-arrays input pattern,
while reusing existing CUTKIT clipping and folded quadrature kernels.

## Scope

- Add a public CAD facade API for 2D and 3D load/clip/integrate workflows.
- Add typed scalar box objects and array-mode batch box containers.
- Define deterministic batch broadcasting, ordering, and result semantics.
- Add folded quadrature convenience APIs over clipped box batches.
- Add tests and docs for object-mode and array-mode usage.

## Non-Goals

- Replacing existing low-level `io`/`quadrature` APIs.
- Supporting non-axis-aligned clipping boxes.
- Introducing GPU or distributed batch execution.

## Acceptance Criteria

- Consumers can load CAD faces/solids and clip one or many axis-aligned boxes
  through one coherent public API.
- Batch APIs accept object-mode and array-mode inputs with deterministic
  broadcasting and output shape behavior.
- Strict and non-strict modes provide predictable validation/status handling.
- Object-mode and array-mode produce equivalent clipping/integration outputs for
  matching box sets.
- Focused tests and full `make dev` pass.

## Implementation Checklist

- [x] Add consumer-facing CAD facade (`CadSession`, `CadFace2D`, `CadSolid3D`).
- [x] Add `Box2D`/`Box3D` and `Box2DArray`/`Box3DArray` input types.
- [x] Implement shared input normalization + broadcasting utilities.
- [x] Implement strict/non-strict per-box status behavior.
- [x] Add 2D and 3D batch clipping workflows.
- [x] Add 2D and 3D folded integration convenience workflows.
- [x] Add tests for normalization, statuses, and mode equivalence.
- [x] Add README/docs usage examples.
- [x] Run focused tests and full `make dev`.

## Risks / Open Questions

- Exact shape/typing of batch result containers should balance ergonomics and
  minimal dependencies.
- CAD-enabled test coverage remains environment-dependent; fallback test strategy
  should avoid brittle environment assumptions.
