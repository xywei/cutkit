## Context

CUTKIT currently exposes folded 2D/3D integration primitives and CAD-native
clipped box workflows:

- oriented 2D loop/3D boundary extraction and clipping
- deterministic folded quadrature rules over trimmed panels/volumes
- consumer-facing object-or-arrays batch clipping APIs

But the solver-facing handoff is incomplete: users still need custom glue to
build signed source charges for far-field volume potential evaluation.

## Goals / Non-Goals

**Goals**

- Provide one deterministic API that maps clipped source regions and source
  density to signed point sources.
- Preserve folded weight signs and expose them explicitly.
- Keep output order stable across runs and compatible with batch box semantics.
- Support CUTKIT object-or-arrays input style for vectorized box/source
  workflows.
- Offer volumential-ready materialization helpers (NumPy-friendly when
  available, pure-Python fallback otherwise).

**Non-Goals**

- Implementing FMM/tree/list construction in CUTKIT.
- Solving near-field singular/near-singular interactions in this change.
- Replacing existing low-level quadrature kernels.

## Decisions

1. Add typed source-cloud containers with one dimension-independent contract and
   2D/3D convenience wrappers.
   - Rationale: explicit fields (`points`, `weights`, `charges`, indexing
      metadata) reduce downstream adapter ambiguity.

2. Define charge as `charge_i = rho(point_i) * weight_i`.
   - Rationale: directly represents folded quadrature sum semantics; negative
     folded weights naturally become negative charges.

3. Reuse existing clipping and folded-rule generation paths in both 2D and 3D.
   - Rationale: avoids divergent quadrature implementations and preserves tested
      folded behavior.

4. Keep deterministic flattening order aligned with existing batch APIs
   (row-major/C-order).
   - Rationale: reproducibility and fixture stability.

5. Expose backend mode (`jplus` / `folded`) in output metadata.
   - Rationale: downstream validation and parity diagnostics depend on explicit
     mode visibility.

6. Reuse one object-or-arrays normalization path for single and batch source
   region inputs.
   - Rationale: consistent behavior between object-mode and array-mode avoids
     semantic drift and supports vectorized callers.

## API Sketch

- `build_signed_source_cloud_2d(...) -> SignedSourceCloud`
- `build_signed_source_cloud_3d(...) -> SignedSourceCloud`
- `CadFace2D.source_cloud_over_boxes(...) -> SignedSourceCloudBatch`
- `CadSolid3D.source_cloud_over_boxes(...) -> SignedSourceCloudBatch`
- unified container contract:
  - `dim: Literal[2, 3]`
  - flat points/weights/charges with deterministic `point_ptr`
  - per-box statuses/errors and row-major batch semantics

### Concrete Signature Draft

```python
from dataclasses import dataclass
from typing import Any, Callable, Literal, Sequence

SpatialDim = Literal[2, 3]
FarfieldBackendMode = Literal["jplus", "folded"]
PointND = tuple[float, ...]  # runtime-validated length == dim
BoundsND = tuple[float, ...]  # runtime-validated length == 2*dim


@dataclass(frozen=True)
class SignedSourceCloud:
    dim: SpatialDim
    points: tuple[PointND, ...]
    weights: tuple[float, ...]
    charges: tuple[float, ...]
    backend_mode: FarfieldBackendMode
    order: int


@dataclass(frozen=True)
class SignedSourceCloudBatch:
    dim: SpatialDim
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    point_ptr: tuple[int, ...]  # len = n_boxes + 1
    points: tuple[PointND, ...]
    weights: tuple[float, ...]
    charges: tuple[float, ...]
    source_box_index: tuple[int, ...]  # same length as points
    backend_mode: FarfieldBackendMode
    order: int

    def statuses_shaped(self) -> Any: ...


def build_signed_source_cloud_2d(
    panel: CurveTrimmedPanel2D,
    *,
    density: Callable[[Any, Any], Any],
    order: int,
    backend_mode: FarfieldBackendMode = "folded",
) -> SignedSourceCloud: ...


def build_signed_source_cloud_3d(
    boundary: tuple[tuple[Point3D, Point3D, Point3D], ...],
    *,
    density: Callable[[Any, Any, Any], Any],
    seed: SeedInput3D = "grid-best",
    order: int,
    backend_mode: FarfieldBackendMode = "folded",
) -> SignedSourceCloud: ...


def source_cloud_over_boxes_2d(
    self: CadFace2D,
    density: Callable[[Any, Any], Any],
    boxes: Box2D | Sequence[Box2D] | Box2DArray | None = None,
    *,
    x0: Any = None,
    x1: Any = None,
    y0: Any = None,
    y1: Any = None,
    order: int,
    backend_mode: FarfieldBackendMode = "folded",
    strict: bool = True,
) -> SignedSourceCloudBatch: ...


def source_cloud_over_boxes_3d(
    self: CadSolid3D,
    density: Callable[[Any, Any, Any], Any],
    boxes: Box3D | Sequence[Box3D] | Box3DArray | None = None,
    *,
    x0: Any = None,
    x1: Any = None,
    y0: Any = None,
    y1: Any = None,
    z0: Any = None,
    z1: Any = None,
    order: int,
    seed: SeedInput3D = "grid-best",
    backend_mode: FarfieldBackendMode = "folded",
    strict: bool = True,
) -> SignedSourceCloudBatch: ...
```

## Risks / Trade-offs

- Signed-weight cancellation can increase floating-point sensitivity in highly
  folded configurations.
- Large source clouds may require chunking/materialization controls to avoid
  excessive memory overhead.
- Backend parity checks need tolerance-aware validation (exact point-for-point
  equality is not guaranteed between `jplus` and folded).

## Validation Plan

- Unit tests for deterministic ordering and stable metadata.
- Object-mode vs array-mode equivalence tests for matching box sets.
- Tests that verify signed weights are preserved (including negative entries in
  folded mode where expected).
- Conservation-style tests: constant-density charge sum approximates clipped
  volume integral.
- Parity-style tests: far-target potential from source cloud matches direct
  folded integration reference within tolerance.
- Full repository gate via `make dev`.
