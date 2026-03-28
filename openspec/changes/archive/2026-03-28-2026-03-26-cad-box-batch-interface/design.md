## Context

The current API surface provides robust low-level primitives:

- OpenCascade 2D/3D BREP ingestion and box clipping adapters
- folded 2D and 3D quadrature kernels
- deterministic parity and regression checks

But there is no unified consumer API that expresses:

1. CAD object representation,
2. many-box clipping in object-or-array form, and
3. folded integration over those clipped results.

## Goals / Non-Goals

**Goals**

- Provide one public CAD workflow facade for load/clip/integrate.
- Support both object-mode and array-mode box inputs with broadcasting.
- Provide deterministic output ordering/shape and per-box status reporting.
- Keep existing low-level APIs available for advanced users.

**Non-Goals**

- Replacing the existing low-level `io` and `quadrature` modules.
- Supporting non-axis-aligned clipping boxes in this change.
- Introducing GPU/distributed execution semantics.

## Decisions

1. Add a new consumer facade module (`cutkit.cad`) that depends on existing
   `io`, `geometry`, and `quadrature` layers.
   - Rationale: keep low-level internals stable while offering a cleaner public
     interface for common workflows.

2. Define explicit 2D/3D box types and array containers.
   - Rationale: typed value objects improve API discoverability and reduce
     ambiguity for single-box usage.

3. Use a single normalization path for object and array inputs.
   - Rationale: guarantees object-vs-array behavioral equivalence and avoids
     drift between code paths.

4. Standardize batch result semantics with statuses and strict mode.
   - Rationale: consumers need predictable behavior for partial failures in large
     box batches.

5. Keep deterministic flatten/reshape ordering (row-major/C-order).
   - Rationale: stable output ordering is required for reproducible workflows and
     fixture-based tests.

## API Sketch

- `Box2D`, `Box3D` for scalar object mode.
- `Box2DArray`, `Box3DArray` for explicit array mode containers.
- `CadSession.opencascade()` as backend entry point.
- `CadFace2D` and `CadSolid3D` handles:
  - `clip_box(...)`
  - `clip_boxes(...)`
  - conversion helpers into panel/triangulation forms
  - folded integration convenience over one or many boxes

## Batch Input Contract

- Accept exactly one style per call:
  - object mode (`boxes=Box*` or `Sequence[Box*]`), or
  - array mode (`Box*Array` or explicit coordinate arrays).
- Broadcast all array inputs to a shared shape.
- Validate `x1>x0`, `y1>y0`, and `z1>z0` per box.
- Return `BatchResult` with:
  - values array/list
  - statuses array/list
  - optional diagnostic messages

## Risks / Trade-offs

- Wrapper layer adds API surface area that must remain coherent.
- Batch semantics can become confusing without strict validation/docs.
- CAD-enabled test coverage may be environment-dependent.

## Validation Plan

- Unit tests for box normalization and broadcasting semantics.
- Unit tests for strict vs non-strict status handling.
- Equivalence tests: object-mode and array-mode produce matching outputs.
- 2D and 3D end-to-end tests for load/clip/integrate workflows.
- Full repository gate via `make dev`.
