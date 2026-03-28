## Context

Current CUTKIT capabilities provide:

- robust folded quadrature for regular 2D/3D clipped domains
- deterministic source-region clipping and batch APIs
- a 2D immersed Galerkin solver benchmark path

But there is no dimension-independent local near-field correction assembly
workflow that can replace direct near-kernel evaluation in QBFEM-style
compositions.

## Goals / Non-Goals

**Goals**

- Provide a local boxed correction assembler using tensor-product B-spline
  (IGA-style) Galerkin discretization in 2D/3D.
- Support boundary-value injection from far-field quadrature traces sampled on
  local box boundaries.
- Return deterministic local linear systems/operators for requested target
  batches in 2D/3D.
- Support dual local-operator modes: assembled sparse systems and matrix-free
  matvec operators (with RHS and metadata).
- Make composition with far-field source-cloud evaluation explicit and safe
  against double-counting.
- Support object-or-arrays vectorized inputs for local boxes, restricted-source
  sets, and near-target batches.

**Non-Goals**

- General PDE framework with broad BC/stabilization policies.
- Full adaptive mesh refinement or multigrid in this change.
- Replacing external tree/list construction logic.

## Decisions

1. Use axis-aligned local correction boxes as the computational domain.
   - Rationale: aligns with existing clipped-box workflows and simplifies
     deterministic setup.

2. Use strong Dirichlet imposition on local box boundaries.
   - Rationale: boundary traces are supplied from far-field evaluation and map
     directly to local correction boundary conditions.

3. Use an assembler-first contract: CUTKIT emits local operators; solving can be
   performed by CUTKIT helpers or external callers.
   - Rationale: aligns with QBFEM orchestration and keeps interfaces flexible.

4. Add `operator_mode` selection (`assembled` or `matrix_free`) with algebraic
   equivalence guarantees.
   - Rationale: high-order local operators may be expensive to materialize,
     while matrix-free matvec can reduce memory pressure.

5. Separate source support selection from solver internals.
   - Rationale: list classification (`self/list1/list3/list4`) belongs to
     caller-side orchestration; solver consumes restricted source-cloud inputs.

6. Expose explicit composition metadata for far/near reconciliation.
   - Rationale: avoid accidental double-counting when combining far-field and
     local corrections.

7. Reuse one object-or-arrays normalization path across local box, source, and
   target inputs.
   - Rationale: vectorized workflows need deterministic broadcasting and
     ordering equivalent to object-mode behavior.

8. Use a dimension-dispatched core with one public contract (`dim in {2,3}`).
   - Rationale: callers need one interface shape across dimensions while kernels
     remain dimension-specific internally.

## API Sketch

- `build_local_box_boundary_trace(...) -> BoundaryTraceBatch`
- `assemble_local_nearfield_operators(..., operator_mode=...) -> LocalOperatorBatch`
- `solve_local_operator_batch(...) -> LocalNearfieldSolveBatch` (optional helper)
- input contract (tentative):
  - object-mode: `Box2D|Box3D` / `Sequence[Box2D|Box3D]`, point tuples for
    sources/targets
  - array-mode: coordinate arrays broadcast to shared shapes
- result metadata (tentative):
  - `dim` (`2` or `3`)
  - local box bounds and discretization info
  - operator encoding metadata:
    - assembled mode: sparse matrix encoding (for example CSR + per-system pointers)
    - matrix-free mode: deterministic matvec kernel metadata and per-system pointers
  - residual and iteration diagnostics
  - source/target counts and composition markers

### Concrete Signature Draft

```python
from dataclasses import dataclass
from typing import Any, Callable, Literal, Sequence

SpatialDim = Literal[2, 3]
PointND = tuple[float, ...]  # runtime-validated length == dim
BoundsND = tuple[float, ...]  # runtime-validated length == 2*dim
NearfieldOperatorMode = Literal["assembled", "matrix_free"]


@dataclass(frozen=True)
class BoundaryTraceBatch:
    dim: SpatialDim
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    trace_ptr: tuple[int, ...]  # len = n_boxes + 1
    trace_points: tuple[PointND, ...]
    trace_values: tuple[float, ...]

    def statuses_shaped(self) -> Any: ...


@dataclass(frozen=True)
class RestrictedSourceBatch:
    dim: SpatialDim
    shape: tuple[int, ...]
    source_ptr: tuple[int, ...]  # len = n_boxes + 1
    source_points: tuple[PointND, ...]
    source_charges: tuple[float, ...]


@dataclass(frozen=True)
class LocalOperatorBatch:
    dim: SpatialDim
    operator_mode: NearfieldOperatorMode
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    free_dof_ptr: tuple[int, ...]  # len = n_boxes + 1
    rhs: tuple[float, ...]
    # Assembled representation (present in assembled mode):
    csr_indptr: tuple[int, ...] | None
    csr_indices: tuple[int, ...] | None
    csr_data: tuple[float, ...] | None
    # Matrix-free representation (present in matrix_free mode):
    matvec_kernel_id: str | None

    def matvec(self, x_flat: Sequence[float]) -> tuple[float, ...]: ...
    def statuses_shaped(self) -> Any: ...


@dataclass(frozen=True)
class LocalNearfieldSolveBatch:
    dim: SpatialDim
    shape: tuple[int, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    free_dof_ptr: tuple[int, ...]
    solution: tuple[float | None, ...]
    residual_norms: tuple[float | None, ...]
    iterations: tuple[int | None, ...]


def build_local_box_boundary_trace(
    dim: SpatialDim,
    boxes: Box2D | Sequence[Box2D] | Box2DArray | Box3D | Sequence[Box3D] | Box3DArray | None = None,
    *,
    x0: Any = None,
    x1: Any = None,
    y0: Any = None,
    y1: Any = None,
    z0: Any = None,
    z1: Any = None,
    farfield_potential: Callable[..., Any],
    trace_order: int = 5,
    strict: bool = True,
) -> BoundaryTraceBatch: ...


def assemble_local_nearfield_operators(
    dim: SpatialDim,
    boxes: Box2D | Sequence[Box2D] | Box2DArray | Box3D | Sequence[Box3D] | Box3DArray | None = None,
    *,
    x0: Any = None,
    x1: Any = None,
    y0: Any = None,
    y1: Any = None,
    z0: Any = None,
    z1: Any = None,
    restricted_sources: RestrictedSourceBatch,
    boundary_trace: BoundaryTraceBatch,
    resolution: int,
    spline_degree: int = 2,
    quadrature_order: int,
    operator_mode: NearfieldOperatorMode = "assembled",
    strict: bool = True,
) -> LocalOperatorBatch: ...


def solve_local_operator_batch(
    operators: LocalOperatorBatch,
    *,
    tolerance: float = 1.0e-10,
    max_iterations: int | None = None,
) -> LocalNearfieldSolveBatch: ...
```

## Composition Model

- Let `rho_near` be the restricted source set for one local correction box.
- Assemble on box `B`:
  - `A_ij = int_B grad(phi_i)·grad(phi_j) dV`
  - `b_i = int_{Omega_s} rho_near phi_i dV`
  - Dirichlet trace on `partial B` lifted from `g_far` sampled on boundary points.
- Emit `(A, b, metadata)` in vectorized batch form; solving/evaluation can be
  done in CUTKIT or externally.
- In matrix-free mode, emit `(matvec, b, metadata)` where `matvec` applies the
  same local Galerkin operator without explicit sparse materialization.

## Source-to-Box Coupling (Compact-Support Handling)

`rho_near` is supported on a compact trimmed region `Omega_s` inside `B`, while
the solution space is defined on tensor-product box basis functions over all of
`B`. The coupling is handled in weak form by integrating the forcing only over
`Omega_s`:

- Find `u` in box spline space with Dirichlet trace `g_far` such that, for all
  test functions `v` with zero trace,
  - `int_B grad(u)·grad(v) dV = int_{Omega_s} rho_near v dV`.

Implementation consequence:

- Stiffness assembly remains box-native (`A_ij = int_B grad(phi_i)·grad(phi_j)`).
- Load assembly is support-native (`b_i = int_{Omega_s} rho_near phi_i`).
- `int_{Omega_s}` is evaluated by folded quadrature over clipped support,
  yielding signed points/weights and the discrete deposition
  `b_i ~= sum_q charge_q * phi_i(y_q)` with `charge_q = rho(y_q) * w_q`.

No explicit geometric projection of `Omega_s` into a box-aligned mesh is
required; mismatch is resolved by quadrature coupling between spaces.

## Risks / Trade-offs

- Without preconditioning, high-order 3D local solves may require many CG
  iterations.
- Boundary trace quality can dominate correction accuracy if box padding or
  quadrature order is insufficient.
- Solver setup may become expensive for many overlapping local boxes without
  caching/reuse.

## Validation Plan

- Unit tests for local assembly sanity and deterministic diagnostics.
- Assembled-vs-matrix-free equivalence tests for operator application and local
  solve outputs (within tolerance).
- Object-mode vs array-mode equivalence tests for local solve and target
  evaluation paths.
- Manufactured-solution tests on boxed domains with known forcing/trace data.
- Composition tests showing far + solved(local system) agreement against
  high-order reference for near targets.
- Regression tests for `self/list1/list3/list4`-style restricted source sets.
- Full repository gate via `make dev`.
