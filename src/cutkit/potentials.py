"""Vectorized interfaces for far/near potential workflows.

This module defines dimension-aware dataclasses and API signatures for
far-field signed source clouds and near-field local operator batches,
including assembled and matrix-free local solve workflows.
"""

from __future__ import annotations

import importlib.util
import weakref
from itertools import product as iter_product
from dataclasses import dataclass
from math import prod
from typing import Any, Callable, Literal, Sequence, cast

import cutkit.cad as _cad
from cutkit.cad import BatchStatus, Box2D, Box2DArray, Box3D, Box3DArray, SeedInput3D
from cutkit.geometry import CurveTrimmedPanel2D, Point3D
from cutkit.io import solid_to_oriented_boundary_triangles
from cutkit.quadrature import (
    boundary_quadrature_rule_3d,
    folded_curve_quadrature_rule,
    gauss_legendre_01,
    seed_grid_3d,
)

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

SpatialDim = Literal[2, 3]
FarfieldBackendMode = Literal["jplus", "folded"]
NearfieldOperatorMode = Literal["assembled", "matrix_free"]
InteractionListName = Literal["self", "list1", "list3", "list4"]

PointND = tuple[float, ...]
BoundsND = tuple[float, ...]

_VALID_BACKENDS = {"jplus", "folded"}
_VALID_OPERATOR_MODES = {"assembled", "matrix_free"}
_VALID_STATUSES = {"ok", "empty", "invalid_box", "backend_error"}
_VALID_INTERACTION_LISTS = {"self", "list1", "list3", "list4"}


def _validate_dim(dim: SpatialDim) -> int:
    dim_value = int(dim)
    if dim_value not in {2, 3}:
        raise ValueError(f"dim must be 2 or 3; got {dim!r}")
    return dim_value


def _validate_order(order: int, *, name: str) -> None:
    if order < 1:
        raise ValueError(f"{name} must be positive")


def _validate_backend(backend_mode: FarfieldBackendMode) -> None:
    if backend_mode not in _VALID_BACKENDS:
        raise ValueError(f"unsupported backend_mode: {backend_mode!r}")


def _validate_shape(shape: tuple[int, ...]) -> int:
    if shape == ():
        return 1
    if not shape:
        return 0
    for axis_size in shape:
        if axis_size < 1:
            raise ValueError("shape dimensions must be positive")
    return prod(shape)


def _validate_points(points: tuple[PointND, ...], *, dim: int) -> None:
    for point in points:
        if len(point) != dim:
            raise ValueError(f"point arity mismatch: expected {dim}, got {len(point)}")


def _validate_bounds(bounds: tuple[BoundsND, ...], *, dim: int) -> None:
    expected = 2 * dim
    for item in bounds:
        if len(item) != expected:
            raise ValueError(
                f"bounds arity mismatch: expected {expected}, got {len(item)}"
            )


def _bounds_match(
    lhs: tuple[BoundsND, ...],
    rhs: tuple[BoundsND, ...],
    *,
    atol: float = 1.0e-12,
) -> bool:
    if len(lhs) != len(rhs):
        return False
    for left, right in zip(lhs, rhs, strict=True):
        if len(left) != len(right):
            return False
        for left_value, right_value in zip(left, right, strict=True):
            if abs(float(left_value) - float(right_value)) > atol:
                return False
    return True


def _validate_statuses(statuses: tuple[BatchStatus, ...]) -> None:
    for status in statuses:
        if status not in _VALID_STATUSES:
            raise ValueError(f"unsupported batch status: {status!r}")


def _validate_ptr(
    ptr: tuple[int, ...],
    *,
    count: int,
    total: int,
    name: str,
) -> None:
    if len(ptr) != count + 1:
        raise ValueError(
            f"{name} length mismatch: expected {count + 1}, got {len(ptr)}"
        )
    if not ptr:
        raise ValueError(f"{name} must not be empty")
    if ptr[0] != 0:
        raise ValueError(f"{name} must start at zero")

    previous = ptr[0]
    for value in ptr[1:]:
        if value < previous:
            raise ValueError(f"{name} must be nondecreasing")
        previous = value
    if ptr[-1] != total:
        raise ValueError(f"{name} terminal value mismatch: expected {total}")


def _reshape_flat(values: Sequence[Any], shape: tuple[int, ...]) -> Any:
    if shape == ():
        if not values:
            raise ValueError("cannot reshape empty sequence to scalar shape")
        return values[0]
    if not shape:
        return tuple(values)
    if len(shape) == 1:
        return tuple(values)

    chunk = prod(shape[1:])
    return tuple(
        _reshape_flat(values[index * chunk : (index + 1) * chunk], shape[1:])
        for index in range(shape[0])
    )


def _coerce_int(value: Any, *, name: str) -> int:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be an integer")
    coerced = int(value)
    if float(coerced) != float(value):
        raise ValueError(f"{name} must be an integer")
    return coerced


def _flatten_numeric_values(value: Any, *, name: str) -> tuple[float, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be numeric scalar or sequence")
    if isinstance(value, Sequence):
        flattened: list[float] = []
        for idx, item in enumerate(value):
            flattened.extend(_flatten_numeric_values(item, name=f"{name}[{idx}]"))
        return tuple(flattened)
    return (float(value),)


def _materialize_array(
    values: Sequence[Any],
    *,
    use_numpy: bool | None,
    dtype: Any,
    name: str,
) -> Any:
    if use_numpy is True:
        if _np is None:
            raise RuntimeError(f"NumPy is required for {name} with use_numpy=True")
        return _np.asarray(values, dtype=dtype)
    if use_numpy is False:
        return tuple(values)

    if _np is not None:
        return _np.asarray(values, dtype=dtype)
    return tuple(values)


def _materialize_point_coords(
    points: tuple[PointND, ...],
    *,
    dim: int,
    use_numpy: bool | None,
    name: str,
) -> tuple[Any, ...]:
    coords = []
    for axis in range(dim):
        axis_values = tuple(float(point[axis]) for point in points)
        coords.append(
            _materialize_array(
                axis_values,
                use_numpy=use_numpy,
                dtype=float,
                name=f"{name}.coords[{axis}]",
            )
        )
    return tuple(coords)


def _normalize_point_input(
    dim: int,
    points: Any,
) -> tuple[tuple[int, ...], tuple[PointND, ...], tuple[int, ...]]:
    if points is None:
        raise ValueError("points input is required")
    if isinstance(points, (str, bytes)):
        raise TypeError("points must be point tuple or sequence of point tuples")
    if not isinstance(points, Sequence):
        raise TypeError("points must be point tuple or sequence of point tuples")
    if not points:
        raise ValueError("points sequence must not be empty")

    first = points[0]
    if isinstance(first, Sequence) and not isinstance(first, (str, bytes)):
        normalized: list[PointND] = []
        for idx, item in enumerate(points):
            if not isinstance(item, Sequence) or isinstance(item, (str, bytes)):
                raise TypeError("points sequence must contain only point tuples")
            if len(item) != dim:
                raise ValueError(
                    f"point at index {idx} has arity {len(item)} but expected {dim}"
                )
            normalized.append(tuple(float(coord) for coord in item))
        return (len(normalized),), tuple(normalized), tuple(range(len(normalized)))

    if len(points) != dim:
        raise ValueError(f"point has arity {len(points)} but expected {dim}")
    point = tuple(float(coord) for coord in points)
    return (), (point,), (0,)


def _coerce_relation_entries(
    value: Any,
    *,
    box_count: int,
    name: str,
) -> tuple[tuple[int, ...], ...]:
    if value is None:
        return tuple(() for _ in range(box_count))
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be sequence data")
    if not isinstance(value, Sequence):
        raise TypeError(f"{name} must be sequence data")

    if box_count == 1:
        if not value:
            return ((),)
        first = value[0]
        if isinstance(first, Sequence) and not isinstance(first, (str, bytes)):
            if len(value) != 1:
                raise ValueError(f"{name} must have length 1 for scalar box shape")
            entry_seq = value[0]
            return (tuple(_coerce_int(item, name=f"{name}[0]") for item in entry_seq),)
        return (tuple(_coerce_int(item, name=f"{name}[0]") for item in value),)

    if len(value) != box_count:
        raise ValueError(f"{name} length must match box count {box_count}")

    entries: list[tuple[int, ...]] = []
    for idx, item in enumerate(value):
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            entries.append(
                tuple(_coerce_int(part, name=f"{name}[{idx}]") for part in item)
            )
        else:
            entries.append((_coerce_int(item, name=f"{name}[{idx}]"),))
    return tuple(entries)


def _unimplemented(name: str) -> NotImplementedError:
    return NotImplementedError(f"{name} is scaffolded but not implemented yet")


def _is_empty_boundary_error(exc: ValueError) -> bool:
    message = str(exc).lower()
    return (
        "no boundary triangles" in message
        or "no non-degenerate triangles" in message
        or "empty boundary" in message
    )


def _evaluate_density_2d(
    density: Callable[[Any, Any], Any],
    points: tuple[PointND, ...],
) -> tuple[float, ...]:
    if not points:
        return ()

    if _np is not None:
        xs = _np.asarray(tuple(point[0] for point in points), dtype=float)
        ys = _np.asarray(tuple(point[1] for point in points), dtype=float)
        try:
            values = _np.asarray(density(xs, ys), dtype=float)
            if values.shape == xs.shape:
                return tuple(float(value) for value in values.tolist())
        except Exception:
            pass

    return tuple(float(density(point[0], point[1])) for point in points)


def _evaluate_density_3d(
    density: Callable[[Any, Any, Any], Any],
    points: tuple[PointND, ...],
) -> tuple[float, ...]:
    if not points:
        return ()

    if _np is not None:
        xs = _np.asarray(tuple(point[0] for point in points), dtype=float)
        ys = _np.asarray(tuple(point[1] for point in points), dtype=float)
        zs = _np.asarray(tuple(point[2] for point in points), dtype=float)
        try:
            values = _np.asarray(density(xs, ys, zs), dtype=float)
            if values.shape == xs.shape:
                return tuple(float(value) for value in values.tolist())
        except Exception:
            pass

    return tuple(float(density(point[0], point[1], point[2])) for point in points)


def _panel_anchor_for_backend(
    panel: CurveTrimmedPanel2D,
    *,
    backend_mode: FarfieldBackendMode,
) -> tuple[tuple[float, float] | None, bool]:
    _ = panel
    if backend_mode == "jplus":
        return None, True
    return None, False


def _resolve_seed_3d(
    boundary: tuple[tuple[Point3D, Point3D, Point3D], ...],
    *,
    seed: SeedInput3D,
) -> Point3D:
    if isinstance(seed, str):
        if seed == "jplus":
            return (1.0, 1.0, 1.0)
        if seed == "centroid":
            vertices = tuple(vertex for tri in boundary for vertex in tri)
            if not vertices:
                return (0.0, 0.0, 0.0)
            scale = 1.0 / len(vertices)
            return (
                scale * sum(vertex[0] for vertex in vertices),
                scale * sum(vertex[1] for vertex in vertices),
                scale * sum(vertex[2] for vertex in vertices),
            )
        if seed == "grid-best":
            return _grid_best_seed_3d(boundary)
        raise ValueError(f"unsupported seed mode: {seed!r}")

    return (float(seed[0]), float(seed[1]), float(seed[2]))


def _grid_best_seed_3d(
    boundary: tuple[tuple[Point3D, Point3D, Point3D], ...],
) -> Point3D:
    vertices = tuple(vertex for tri in boundary for vertex in tri)
    if not vertices:
        return (0.0, 0.0, 0.0)

    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)

    if xmax <= xmin:
        xmax = xmin + 1.0
    if ymax <= ymin:
        ymax = ymin + 1.0
    if zmax <= zmin:
        zmax = zmin + 1.0

    candidates: tuple[Point3D, ...] = tuple(
        (
            xmin + (xmax - xmin) * sx,
            ymin + (ymax - ymin) * sy,
            zmin + (zmax - zmin) * sz,
        )
        for sx, sy, sz in seed_grid_3d(3)
    )

    def _closest_vertex_distance_sq(candidate: Point3D) -> float:
        return min(
            (candidate[0] - vx) ** 2
            + (candidate[1] - vy) ** 2
            + (candidate[2] - vz) ** 2
            for vx, vy, vz in vertices
        )

    return max(candidates, key=_closest_vertex_distance_sq)


def _box_measure(bounds: BoundsND, *, dim: int) -> float:
    if dim == 2:
        x0, x1, y0, y1 = bounds
        return max(0.0, float(x1) - float(x0)) * max(0.0, float(y1) - float(y0))
    x0, x1, y0, y1, z0, z1 = bounds
    return (
        max(0.0, float(x1) - float(x0))
        * max(0.0, float(y1) - float(y0))
        * max(0.0, float(z1) - float(z0))
    )


def _operator_coefficients(bounds: BoundsND, *, dim: int) -> tuple[float, float]:
    measure = _box_measure(bounds, dim=dim)
    diag = 1.0 + measure
    offdiag = -0.25 * measure / (1.0 + measure)
    if 2.0 * abs(offdiag) >= diag:
        offdiag = -0.49 * diag
    return diag, offdiag


def _linspace_inclusive(start: float, stop: float, count: int) -> tuple[float, ...]:
    if count <= 1:
        return (float(start),)
    step = (float(stop) - float(start)) / float(count - 1)
    return tuple(float(start) + step * idx for idx in range(count))


def _sample_boundary_points_2d(
    bounds: tuple[float, float, float, float],
    *,
    trace_order: int,
) -> tuple[PointND, ...]:
    x0, x1, y0, y1 = bounds
    count = max(2, trace_order)
    xs = _linspace_inclusive(x0, x1, count)
    ys = _linspace_inclusive(y0, y1, count)

    points: list[PointND] = []
    points.extend((x, y0) for x in xs)
    points.extend((x1, y) for y in ys[1:-1])
    points.extend((x, y1) for x in reversed(xs))
    points.extend((x0, y) for y in reversed(ys[1:-1]))
    return tuple(points)


def _sample_boundary_points_3d(
    bounds: tuple[float, float, float, float, float, float],
    *,
    trace_order: int,
) -> tuple[PointND, ...]:
    x0, x1, y0, y1, z0, z1 = bounds
    count = max(2, trace_order)
    xs = _linspace_inclusive(x0, x1, count)
    ys = _linspace_inclusive(y0, y1, count)
    zs = _linspace_inclusive(z0, z1, count)

    points: list[PointND] = []
    for y in ys:
        for z in zs:
            points.append((x0, y, z))
            points.append((x1, y, z))
    for x in xs:
        for z in zs:
            points.append((x, y0, z))
            points.append((x, y1, z))
    for x in xs:
        for y in ys:
            points.append((x, y, z0))
            points.append((x, y, z1))
    return tuple(points)


def _evaluate_field_2d(
    field: Callable[..., Any],
    points: tuple[PointND, ...],
) -> tuple[float, ...]:
    if not points:
        return ()
    if _np is not None:
        xs = _np.asarray(tuple(point[0] for point in points), dtype=float)
        ys = _np.asarray(tuple(point[1] for point in points), dtype=float)
        try:
            values = _np.asarray(field(xs, ys), dtype=float)
            if values.shape == xs.shape:
                return tuple(float(value) for value in values.tolist())
        except Exception:
            pass

    return tuple(float(field(point[0], point[1])) for point in points)


def _evaluate_field_3d(
    field: Callable[..., Any],
    points: tuple[PointND, ...],
) -> tuple[float, ...]:
    if not points:
        return ()
    if _np is not None:
        xs = _np.asarray(tuple(point[0] for point in points), dtype=float)
        ys = _np.asarray(tuple(point[1] for point in points), dtype=float)
        zs = _np.asarray(tuple(point[2] for point in points), dtype=float)
        try:
            values = _np.asarray(field(xs, ys, zs), dtype=float)
            if values.shape == xs.shape:
                return tuple(float(value) for value in values.tolist())
        except Exception:
            pass

    return tuple(float(field(point[0], point[1], point[2])) for point in points)


def _normalize_box_bounds(
    dim: int,
    boxes: (
        Box2D
        | Sequence[Box2D]
        | Box2DArray
        | Box3D
        | Sequence[Box3D]
        | Box3DArray
        | None
    ),
    *,
    x0: Any,
    x1: Any,
    y0: Any,
    y1: Any,
    z0: Any,
    z1: Any,
) -> tuple[tuple[int, ...], tuple[BoundsND, ...]]:
    if dim == 2:
        if z0 is not None or z1 is not None:
            raise ValueError("z0/z1 are unsupported when dim=2")
        if isinstance(boxes, (Box3D, Box3DArray)):
            raise TypeError("dim=2 requires Box2D inputs")
        boxes2d: Box2D | Sequence[Box2D] | Box2DArray | None = cast(
            Box2D | Sequence[Box2D] | Box2DArray | None,
            boxes,
        )
        normalized = _cad._normalize_boxes2d_inputs(
            boxes2d,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
        )
        return normalized.shape, tuple(normalized.box_bounds)

    if isinstance(boxes, (Box2D, Box2DArray)):
        raise TypeError("dim=3 requires Box3D inputs")
    boxes3d: Box3D | Sequence[Box3D] | Box3DArray | None = cast(
        Box3D | Sequence[Box3D] | Box3DArray | None,
        boxes,
    )
    normalized3d = _cad._normalize_boxes3d_inputs(
        boxes3d,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        z0=z0,
        z1=z1,
    )
    return normalized3d.shape, tuple(normalized3d.box_bounds)


def _build_rhs_segment(
    dof_count: int,
    *,
    source_charges: tuple[float, ...],
    trace_values: tuple[float, ...],
) -> tuple[float, ...]:
    if dof_count <= 0:
        return ()
    source_total = sum(source_charges)
    trace_average = 0.0 if not trace_values else sum(trace_values) / len(trace_values)
    base = source_total / float(dof_count)
    slope = 0.5 * trace_average
    return tuple(base + slope * ((idx + 1) / dof_count) for idx in range(dof_count))


def _build_tridiagonal_csr_segment(
    *,
    start: int,
    count: int,
    diag: float,
    offdiag: float,
    indptr: list[int],
    indices: list[int],
    data: list[float],
) -> None:
    for local_idx in range(count):
        row = start + local_idx
        if local_idx > 0:
            indices.append(row - 1)
            data.append(offdiag)
        indices.append(row)
        data.append(diag)
        if local_idx + 1 < count:
            indices.append(row + 1)
            data.append(offdiag)
        indptr.append(len(indices))


def _apply_tridiagonal_segment(
    vector: Sequence[float],
    *,
    start: int,
    end: int,
    diag: float,
    offdiag: float,
    out: list[float],
) -> None:
    for index in range(start, end):
        value = diag * float(vector[index])
        if index > start:
            value += offdiag * float(vector[index - 1])
        if index + 1 < end:
            value += offdiag * float(vector[index + 1])
        out[index] = value


def _cg_solve(
    matvec: Callable[[tuple[float, ...]], tuple[float, ...]],
    rhs: tuple[float, ...],
    *,
    tolerance: float,
    max_iterations: int,
) -> tuple[tuple[float, ...], int, float]:
    size = len(rhs)
    if size == 0:
        return (), 0, 0.0

    solution = [0.0] * size
    residual = list(rhs)
    direction = list(residual)
    residual_norm_sq = sum(value * value for value in residual)
    if residual_norm_sq <= tolerance * tolerance:
        return tuple(solution), 0, residual_norm_sq**0.5

    for iteration in range(1, max_iterations + 1):
        direction_tuple = tuple(direction)
        apply_direction = matvec(direction_tuple)
        denominator = sum(direction[idx] * apply_direction[idx] for idx in range(size))
        if abs(denominator) <= 1.0e-30:
            raise RuntimeError("local operator is singular or ill-conditioned")

        alpha = residual_norm_sq / denominator
        for idx in range(size):
            solution[idx] += alpha * direction[idx]
            residual[idx] -= alpha * apply_direction[idx]

        new_norm_sq = sum(value * value for value in residual)
        if new_norm_sq <= tolerance * tolerance:
            return tuple(solution), iteration, new_norm_sq**0.5

        beta = new_norm_sq / residual_norm_sq
        for idx in range(size):
            direction[idx] = residual[idx] + beta * direction[idx]
        residual_norm_sq = new_norm_sq

    raise RuntimeError("local conjugate-gradient did not converge")


def _normalize_to_unit(value: float, *, vmin: float, vmax: float) -> float:
    if vmax <= vmin:
        raise ValueError("invalid bounds for normalization")
    normalized = (value - vmin) / (vmax - vmin)
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return normalized


def _open_uniform_knots(*, num_elements: int, degree: int) -> tuple[float, ...]:
    if num_elements < 1:
        raise ValueError("num_elements must be positive")
    if degree < 1:
        raise ValueError("degree must be positive")

    knots = [0.0] * (degree + 1)
    for interior in range(1, num_elements):
        knots.append(interior / num_elements)
    knots.extend([1.0] * (degree + 1))
    return tuple(knots)


def _span_from_param(t: float, *, resolution: int, degree: int) -> int:
    element = int(t * resolution)
    if element < 0:
        element = 0
    elif element >= resolution:
        element = resolution - 1
    return degree + element


def _basis_funs(
    *,
    span: int,
    t: float,
    degree: int,
    knots: tuple[float, ...],
) -> tuple[float, ...]:
    basis = [0.0 for _ in range(degree + 1)]
    left = [0.0 for _ in range(degree + 1)]
    right = [0.0 for _ in range(degree + 1)]
    basis[0] = 1.0

    for j in range(1, degree + 1):
        left[j] = t - knots[span + 1 - j]
        right[j] = knots[span + j] - t
        saved = 0.0
        for r in range(j):
            denom = right[r + 1] + left[j - r]
            temp = 0.0 if abs(denom) <= 1.0e-15 else basis[r] / denom
            basis[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp
        basis[j] = saved

    return tuple(basis)


def _basis_and_derivatives(
    *,
    span: int,
    t: float,
    degree: int,
    knots: tuple[float, ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    values = _basis_funs(span=span, t=t, degree=degree, knots=knots)
    if degree == 0:
        return values, (0.0,)

    lower = _basis_funs(span=span, t=t, degree=degree - 1, knots=knots)
    derivatives = [0.0 for _ in range(degree + 1)]
    for local in range(degree + 1):
        global_index = span - degree + local

        term_left = 0.0
        if local > 0:
            denom_left = knots[global_index + degree] - knots[global_index]
            if abs(denom_left) > 1.0e-15:
                term_left = degree * lower[local - 1] / denom_left

        term_right = 0.0
        if local < degree:
            denom_right = knots[global_index + degree + 1] - knots[global_index + 1]
            if abs(denom_right) > 1.0e-15:
                term_right = degree * lower[local] / denom_right

        derivatives[local] = term_left - term_right

    return values, tuple(derivatives)


def _axis_bounds(
    bounds: BoundsND, *, dim: int
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if dim == 2:
        x0, x1, y0, y1 = cast(tuple[float, float, float, float], bounds)
        return (x0, y0), (x1, y1)
    x0, x1, y0, y1, z0, z1 = cast(
        tuple[float, float, float, float, float, float],
        bounds,
    )
    return (x0, y0, z0), (x1, y1, z1)


def _point_inside_bounds(
    point: PointND,
    bounds: BoundsND,
    *,
    dim: int,
    tol: float = 1.0e-12,
) -> bool:
    mins, maxs = _axis_bounds(bounds, dim=dim)
    return all(
        mins[axis] - tol <= point[axis] <= maxs[axis] + tol for axis in range(dim)
    )


def _flatten_multi_index(indices: tuple[int, ...], *, n_axis: int) -> int:
    value = 0
    stride = 1
    for component in indices:
        value += component * stride
        stride *= n_axis
    return value


def _basis_terms_at_point_nd(
    point: tuple[float, ...],
    *,
    bounds: BoundsND,
    dim: int,
    resolution: int,
    spline_degree: int,
    n_axis: int,
    knots_by_axis: tuple[tuple[float, ...], ...],
) -> tuple[tuple[int, float, tuple[float, ...]], ...]:
    mins, maxs = _axis_bounds(bounds, dim=dim)
    t_values = tuple(
        _normalize_to_unit(point[axis], vmin=mins[axis], vmax=maxs[axis])
        for axis in range(dim)
    )
    inv_lengths = tuple(1.0 / (maxs[axis] - mins[axis]) for axis in range(dim))

    spans = tuple(
        _span_from_param(t_values[axis], resolution=resolution, degree=spline_degree)
        for axis in range(dim)
    )
    basis_by_axis = []
    deriv_by_axis = []
    starts = []
    for axis in range(dim):
        basis_values, deriv_values = _basis_and_derivatives(
            span=spans[axis],
            t=t_values[axis],
            degree=spline_degree,
            knots=knots_by_axis[axis],
        )
        basis_by_axis.append(basis_values)
        deriv_by_axis.append(deriv_values)
        starts.append(spans[axis] - spline_degree)

    terms: list[tuple[int, float, tuple[float, ...]]] = []
    local_ranges = [range(spline_degree + 1) for _ in range(dim)]
    for locals_tuple in iter_product(*local_ranges):
        globals_tuple = tuple(starts[axis] + locals_tuple[axis] for axis in range(dim))
        if any(component < 0 or component >= n_axis for component in globals_tuple):
            continue

        basis_components = [
            basis_by_axis[axis][locals_tuple[axis]] for axis in range(dim)
        ]
        value = 1.0
        for component in basis_components:
            value *= component

        grads = []
        for axis in range(dim):
            grad_component = deriv_by_axis[axis][locals_tuple[axis]] * inv_lengths[axis]
            for other in range(dim):
                if other == axis:
                    continue
                grad_component *= basis_components[other]
            grads.append(grad_component)

        terms.append(
            (
                _flatten_multi_index(globals_tuple, n_axis=n_axis),
                value,
                tuple(grads),
            )
        )

    return tuple(terms)


def _add_to_sparse_row(row: dict[int, float], col: int, value: float) -> None:
    existing = row.get(col)
    if existing is None:
        row[col] = value
    else:
        row[col] = existing + value


def _assemble_stiffness_rows(
    *,
    bounds: BoundsND,
    dim: int,
    resolution: int,
    spline_degree: int,
    quadrature_order: int,
) -> list[dict[int, float]]:
    n_axis = resolution + spline_degree
    dof_count = n_axis**dim
    rows: list[dict[int, float]] = [dict() for _ in range(dof_count)]

    mins, maxs = _axis_bounds(bounds, dim=dim)
    lengths = tuple(maxs[axis] - mins[axis] for axis in range(dim))
    cell_sizes = tuple(length / resolution for length in lengths)
    knots_by_axis = tuple(
        _open_uniform_knots(num_elements=resolution, degree=spline_degree)
        for _ in range(dim)
    )

    quad_nodes, quad_weights = gauss_legendre_01(quadrature_order)
    element_ranges = [range(resolution) for _ in range(dim)]
    quad_ranges = [range(len(quad_nodes)) for _ in range(dim)]

    for element_indices in iter_product(*element_ranges):
        for quad_indices in iter_product(*quad_ranges):
            t_values = tuple(
                (element_indices[axis] + quad_nodes[quad_indices[axis]]) / resolution
                for axis in range(dim)
            )
            point = tuple(
                mins[axis] + lengths[axis] * t_values[axis] for axis in range(dim)
            )

            weight = 1.0
            for axis in range(dim):
                weight *= quad_weights[quad_indices[axis]] * cell_sizes[axis]

            terms = _basis_terms_at_point_nd(
                point,
                bounds=bounds,
                dim=dim,
                resolution=resolution,
                spline_degree=spline_degree,
                n_axis=n_axis,
                knots_by_axis=knots_by_axis,
            )

            for global_a, _value_a, grad_a in terms:
                row = rows[global_a]
                for global_b, _value_b, grad_b in terms:
                    stiffness = weight * sum(
                        grad_a[axis] * grad_b[axis] for axis in range(dim)
                    )
                    if abs(stiffness) <= 1.0e-20:
                        continue
                    _add_to_sparse_row(row, global_b, stiffness)

    return rows


def _boundary_planes_for_indices(
    axis_indices: tuple[int, ...],
    *,
    mins: tuple[float, ...],
    maxs: tuple[float, ...],
    n_axis: int,
) -> tuple[tuple[int, float], ...]:
    planes: list[tuple[int, float]] = []
    for axis, component in enumerate(axis_indices):
        if component == 0:
            planes.append((axis, mins[axis]))
        elif component == n_axis - 1:
            planes.append((axis, maxs[axis]))
    return tuple(planes)


def _solve_dense_system(
    matrix: list[list[float]],
    rhs: list[float],
) -> tuple[float, ...]:
    size = len(rhs)
    augmented = [row[:] + [rhs[idx]] for idx, row in enumerate(matrix)]

    for col in range(size):
        pivot = max(range(col, size), key=lambda row: abs(augmented[row][col]))
        if abs(augmented[pivot][col]) <= 1.0e-15:
            raise ValueError("singular local system")
        if pivot != col:
            augmented[col], augmented[pivot] = augmented[pivot], augmented[col]

        pivot_value = augmented[col][col]
        for j in range(col, size + 1):
            augmented[col][j] /= pivot_value

        for row in range(col + 1, size):
            factor = augmented[row][col]
            if factor == 0.0:
                continue
            for j in range(col, size + 1):
                augmented[row][j] -= factor * augmented[col][j]

    solution = [0.0] * size
    for row in range(size - 1, -1, -1):
        value = augmented[row][size]
        for col in range(row + 1, size):
            value -= augmented[row][col] * solution[col]
        solution[row] = value

    return tuple(solution)


def _fit_trace_value(
    *,
    position: tuple[float, ...],
    boundary_planes: tuple[tuple[int, float], ...],
    trace_points: tuple[PointND, ...],
    trace_values: tuple[float, ...],
    dim: int,
) -> float:
    if not trace_points:
        return 0.0

    boundary_axes = tuple(axis for axis, _value in boundary_planes)
    tangent_axes = tuple(axis for axis in range(dim) if axis not in boundary_axes)

    candidates: list[int] = []
    if boundary_planes:
        for idx, point in enumerate(trace_points):
            if all(
                abs(point[axis] - value) <= 1.0e-10 for axis, value in boundary_planes
            ):
                candidates.append(idx)

    if not candidates:
        candidates = list(range(len(trace_points)))

    if not tangent_axes:
        return sum(float(trace_values[idx]) for idx in candidates) / len(candidates)

    def tangent_distance_sq(index: int) -> float:
        point = trace_points[index]
        return sum((position[axis] - point[axis]) ** 2 for axis in tangent_axes)

    sorted_candidates = sorted(candidates, key=tangent_distance_sq)
    max_neighbors = max(4, 2 * (len(tangent_axes) + 1))
    selected = sorted_candidates[:max_neighbors]

    min_dist_sq = tangent_distance_sq(selected[0])
    if min_dist_sq <= 1.0e-24:
        coincident = [idx for idx in selected if tangent_distance_sq(idx) <= 1.0e-24]
        return sum(float(trace_values[idx]) for idx in coincident) / len(coincident)

    basis_size = len(tangent_axes) + 1
    normal = [[0.0 for _ in range(basis_size)] for _ in range(basis_size)]
    rhs = [0.0 for _ in range(basis_size)]

    for idx in selected:
        distance_sq = tangent_distance_sq(idx)
        weight = 1.0 / max(distance_sq, 1.0e-24)
        features = [1.0] + [trace_points[idx][axis] for axis in tangent_axes]
        value = float(trace_values[idx])
        for i in range(basis_size):
            rhs[i] += weight * features[i] * value
            for j in range(basis_size):
                normal[i][j] += weight * features[i] * features[j]

    ridge = 1.0e-12
    for i in range(basis_size):
        normal[i][i] += ridge

    try:
        coeffs = _solve_dense_system(normal, rhs)
        prediction = coeffs[0]
        for local_axis, axis in enumerate(tangent_axes, start=1):
            prediction += coeffs[local_axis] * position[axis]
        return float(prediction)
    except Exception:
        total_weight = 0.0
        total_value = 0.0
        for idx in selected:
            weight = 1.0 / max(tangent_distance_sq(idx), 1.0e-24)
            total_weight += weight
            total_value += weight * float(trace_values[idx])
        if total_weight <= 0.0:
            return 0.0
        return total_value / total_weight


def _fixed_dof_values_from_trace(
    *,
    bounds: BoundsND,
    dim: int,
    n_axis: int,
    trace_points: tuple[PointND, ...],
    trace_values: tuple[float, ...],
) -> dict[int, float]:
    mins, maxs = _axis_bounds(bounds, dim=dim)
    fixed: dict[int, float] = {}

    index_ranges = [range(n_axis) for _ in range(dim)]
    for axis_indices in iter_product(*index_ranges):
        if not any(component in {0, n_axis - 1} for component in axis_indices):
            continue

        position = tuple(
            mins[axis] + (maxs[axis] - mins[axis]) * axis_indices[axis] / (n_axis - 1)
            for axis in range(dim)
        )
        boundary_planes = _boundary_planes_for_indices(
            axis_indices,
            mins=mins,
            maxs=maxs,
            n_axis=n_axis,
        )
        if trace_points:
            value = _fit_trace_value(
                position=position,
                boundary_planes=boundary_planes,
                trace_points=trace_points,
                trace_values=trace_values,
                dim=dim,
            )
        else:
            value = 0.0

        fixed[_flatten_multi_index(axis_indices, n_axis=n_axis)] = value

    return fixed


def _apply_dirichlet_and_reduce(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    fixed_values: dict[int, float],
) -> tuple[list[dict[int, float]], tuple[float, ...], tuple[int, ...]]:
    if not fixed_values:
        return matrix_rows, tuple(rhs), tuple(range(len(rhs)))

    fixed_indices = tuple(sorted(fixed_values))
    fixed_set = set(fixed_indices)

    for index in fixed_indices:
        matrix_rows[index] = {index: 1.0}
        rhs[index] = fixed_values[index]

    for row_index, row in enumerate(matrix_rows):
        if row_index in fixed_set:
            continue
        for fixed_index in fixed_indices:
            coeff = row.pop(fixed_index, None)
            if coeff is not None:
                rhs[row_index] -= coeff * fixed_values[fixed_index]

    free_indices = [index for index in range(len(rhs)) if index not in fixed_set]
    if not free_indices:
        return [], (), ()

    index_map = {orig: local for local, orig in enumerate(free_indices)}
    local_rows: list[dict[int, float]] = [dict() for _ in free_indices]
    local_rhs = [0.0 for _ in free_indices]

    for local_index, original_index in enumerate(free_indices):
        local_rhs[local_index] = rhs[original_index]
        row = matrix_rows[original_index]
        for col, value in row.items():
            mapped = index_map.get(col)
            if mapped is None:
                continue
            local_rows[local_index][mapped] = value

    return local_rows, tuple(local_rhs), tuple(free_indices)


def _rows_to_csr(
    rows: Sequence[dict[int, float]],
) -> tuple[tuple[int, ...], tuple[int, ...], tuple[float, ...]]:
    indptr = [0]
    indices: list[int] = []
    data: list[float] = []
    for row in rows:
        for col in sorted(row):
            indices.append(col)
            data.append(row[col])
        indptr.append(len(indices))
    return tuple(indptr), tuple(indices), tuple(data)


@dataclass(frozen=True)
class _MatrixFreePayload:
    indptr_by_box: tuple[tuple[int, ...], ...]
    indices_by_box: tuple[tuple[int, ...], ...]
    data_by_box: tuple[tuple[float, ...], ...]


_MATRIX_FREE_PAYLOADS: weakref.WeakValueDictionary[str, _MatrixFreePayload] = (
    weakref.WeakValueDictionary()
)
_MATRIX_FREE_KERNEL_COUNTER = 0


def _register_matrix_free_payload(payload: _MatrixFreePayload) -> str:
    global _MATRIX_FREE_KERNEL_COUNTER
    _MATRIX_FREE_KERNEL_COUNTER += 1
    kernel_id = f"iga-mf-v1-{_MATRIX_FREE_KERNEL_COUNTER}"
    _MATRIX_FREE_PAYLOADS[kernel_id] = payload
    return kernel_id


def _get_matrix_free_payload(kernel_id: str | None) -> _MatrixFreePayload:
    if kernel_id is None:
        raise ValueError("matrix_free mode requires a kernel id")
    payload = _MATRIX_FREE_PAYLOADS.get(kernel_id)
    if payload is None:
        raise ValueError(f"unknown matrix_free kernel id: {kernel_id}")
    return payload


@dataclass(frozen=True)
class SignedSourceCloud:
    """Flat signed source cloud for one clipped source region."""

    dim: SpatialDim
    points: tuple[PointND, ...]
    weights: tuple[float, ...]
    charges: tuple[float, ...]
    backend_mode: FarfieldBackendMode
    order: int

    def __post_init__(self) -> None:
        dim = _validate_dim(self.dim)
        _validate_order(self.order, name="order")
        _validate_backend(self.backend_mode)
        _validate_points(self.points, dim=dim)

        count = len(self.points)
        if len(self.weights) != count:
            raise ValueError("weights length must match points length")
        if len(self.charges) != count:
            raise ValueError("charges length must match points length")

    def as_volumential_arrays(self, *, use_numpy: bool | None = None) -> dict[str, Any]:
        dim_value = _validate_dim(self.dim)
        return {
            "dim": dim_value,
            "coords": _materialize_point_coords(
                self.points,
                dim=dim_value,
                use_numpy=use_numpy,
                name="SignedSourceCloud",
            ),
            "weights": _materialize_array(
                self.weights,
                use_numpy=use_numpy,
                dtype=float,
                name="SignedSourceCloud.weights",
            ),
            "charges": _materialize_array(
                self.charges,
                use_numpy=use_numpy,
                dtype=float,
                name="SignedSourceCloud.charges",
            ),
            "backend_mode": self.backend_mode,
            "order": self.order,
        }


@dataclass(frozen=True)
class SignedSourceCloudBatch:
    """Flat signed source clouds over a deterministic box batch."""

    dim: SpatialDim
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    point_ptr: tuple[int, ...]
    points: tuple[PointND, ...]
    weights: tuple[float, ...]
    charges: tuple[float, ...]
    source_box_index: tuple[int, ...]
    backend_mode: FarfieldBackendMode
    order: int

    def __post_init__(self) -> None:
        dim = _validate_dim(self.dim)
        _validate_order(self.order, name="order")
        _validate_backend(self.backend_mode)

        box_count = _validate_shape(self.shape)
        if len(self.box_bounds) != box_count:
            raise ValueError("box_bounds length must match flattened shape")
        _validate_bounds(self.box_bounds, dim=dim)

        _validate_statuses(self.statuses)
        if len(self.statuses) != box_count:
            raise ValueError("statuses length must match flattened shape")
        if len(self.errors) != box_count:
            raise ValueError("errors length must match flattened shape")

        point_count = len(self.points)
        _validate_points(self.points, dim=dim)
        if len(self.weights) != point_count:
            raise ValueError("weights length must match points length")
        if len(self.charges) != point_count:
            raise ValueError("charges length must match points length")
        if len(self.source_box_index) != point_count:
            raise ValueError("source_box_index length must match points length")

        _validate_ptr(
            self.point_ptr,
            count=box_count,
            total=point_count,
            name="point_ptr",
        )

        for box_index in self.source_box_index:
            if box_index < 0 or box_index >= box_count:
                raise ValueError("source_box_index entries must reference valid boxes")

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def as_volumential_arrays(self, *, use_numpy: bool | None = None) -> dict[str, Any]:
        dim_value = _validate_dim(self.dim)
        return {
            "dim": dim_value,
            "shape": self.shape,
            "coords": _materialize_point_coords(
                self.points,
                dim=dim_value,
                use_numpy=use_numpy,
                name="SignedSourceCloudBatch",
            ),
            "weights": _materialize_array(
                self.weights,
                use_numpy=use_numpy,
                dtype=float,
                name="SignedSourceCloudBatch.weights",
            ),
            "charges": _materialize_array(
                self.charges,
                use_numpy=use_numpy,
                dtype=float,
                name="SignedSourceCloudBatch.charges",
            ),
            "point_ptr": _materialize_array(
                self.point_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="SignedSourceCloudBatch.point_ptr",
            ),
            "source_box_index": _materialize_array(
                self.source_box_index,
                use_numpy=use_numpy,
                dtype=int,
                name="SignedSourceCloudBatch.source_box_index",
            ),
            "statuses": self.statuses,
            "errors": self.errors,
            "backend_mode": self.backend_mode,
            "order": self.order,
        }


@dataclass(frozen=True)
class BoundaryTraceBatch:
    """Boundary trace values sampled over one or many local boxes."""

    dim: SpatialDim
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    trace_ptr: tuple[int, ...]
    trace_points: tuple[PointND, ...]
    trace_values: tuple[float, ...]

    def __post_init__(self) -> None:
        dim = _validate_dim(self.dim)
        box_count = _validate_shape(self.shape)

        if len(self.box_bounds) != box_count:
            raise ValueError("box_bounds length must match flattened shape")
        _validate_bounds(self.box_bounds, dim=dim)

        _validate_statuses(self.statuses)
        if len(self.statuses) != box_count:
            raise ValueError("statuses length must match flattened shape")
        if len(self.errors) != box_count:
            raise ValueError("errors length must match flattened shape")

        trace_count = len(self.trace_points)
        _validate_points(self.trace_points, dim=dim)
        if len(self.trace_values) != trace_count:
            raise ValueError("trace_values length must match trace_points length")

        _validate_ptr(
            self.trace_ptr,
            count=box_count,
            total=trace_count,
            name="trace_ptr",
        )

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)


@dataclass(frozen=True)
class RestrictedSourceBatch:
    """Restricted near-source charges grouped by local correction box."""

    dim: SpatialDim
    shape: tuple[int, ...]
    source_ptr: tuple[int, ...]
    source_points: tuple[PointND, ...]
    source_charges: tuple[float, ...]

    def __post_init__(self) -> None:
        dim = _validate_dim(self.dim)
        box_count = _validate_shape(self.shape)
        point_count = len(self.source_points)

        _validate_points(self.source_points, dim=dim)
        if len(self.source_charges) != point_count:
            raise ValueError("source_charges length must match source_points length")

        _validate_ptr(
            self.source_ptr,
            count=box_count,
            total=point_count,
            name="source_ptr",
        )


@dataclass(frozen=True)
class SourceBoxSelectionBatch:
    """Per-local-box source-box selections (for self/list1/list3/list4 plumbing)."""

    shape: tuple[int, ...]
    source_box_ptr: tuple[int, ...]
    source_box_index: tuple[int, ...]

    def __post_init__(self) -> None:
        box_count = _validate_shape(self.shape)
        _validate_ptr(
            self.source_box_ptr,
            count=box_count,
            total=len(self.source_box_index),
            name="source_box_ptr",
        )


@dataclass(frozen=True)
class NearfieldTargetBatch:
    """Target points mapped into one-or-many local correction boxes."""

    dim: SpatialDim
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    target_ptr: tuple[int, ...]
    target_points: tuple[PointND, ...]
    target_input_index: tuple[int, ...]
    input_shape: tuple[int, ...]

    def __post_init__(self) -> None:
        dim_value = _validate_dim(self.dim)
        box_count = _validate_shape(self.shape)
        if len(self.box_bounds) != box_count:
            raise ValueError("box_bounds length must match flattened shape")
        _validate_bounds(self.box_bounds, dim=dim_value)

        _validate_statuses(self.statuses)
        if len(self.statuses) != box_count:
            raise ValueError("statuses length must match flattened shape")
        if len(self.errors) != box_count:
            raise ValueError("errors length must match flattened shape")

        target_count = len(self.target_points)
        _validate_points(self.target_points, dim=dim_value)
        if len(self.target_input_index) != target_count:
            raise ValueError("target_input_index length must match target_points")
        _validate_ptr(
            self.target_ptr,
            count=box_count,
            total=target_count,
            name="target_ptr",
        )

        input_count = _validate_shape(self.input_shape)
        for index in self.target_input_index:
            if index < 0 or index >= input_count:
                raise ValueError(
                    "target_input_index entries must reference valid inputs"
                )

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)


@dataclass(frozen=True)
class LocalOperatorBatch:
    """Batched local near-field operators in assembled or matrix-free form."""

    dim: SpatialDim
    operator_mode: NearfieldOperatorMode
    resolution: int
    spline_degree: int
    shape: tuple[int, ...]
    box_bounds: tuple[BoundsND, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    free_dof_ptr: tuple[int, ...]
    rhs: tuple[float, ...]
    free_global_ptr: tuple[int, ...]
    free_global_index: tuple[int, ...]
    fixed_dof_ptr: tuple[int, ...]
    fixed_dof_index: tuple[int, ...]
    fixed_dof_value: tuple[float, ...]
    csr_indptr: tuple[int, ...] | None
    csr_indices: tuple[int, ...] | None
    csr_data: tuple[float, ...] | None
    matvec_kernel_id: str | None
    matvec_payload: _MatrixFreePayload | None = None

    def __post_init__(self) -> None:
        dim = _validate_dim(self.dim)
        if self.operator_mode not in _VALID_OPERATOR_MODES:
            raise ValueError(f"unsupported operator_mode: {self.operator_mode!r}")

        box_count = _validate_shape(self.shape)
        if len(self.box_bounds) != box_count:
            raise ValueError("box_bounds length must match flattened shape")
        _validate_bounds(self.box_bounds, dim=dim)

        _validate_statuses(self.statuses)
        if len(self.statuses) != box_count:
            raise ValueError("statuses length must match flattened shape")
        if len(self.errors) != box_count:
            raise ValueError("errors length must match flattened shape")

        if self.resolution < 1:
            raise ValueError("resolution must be positive")
        if self.spline_degree < 1:
            raise ValueError("spline_degree must be positive")

        n_axis = self.resolution + self.spline_degree
        dof_capacity = n_axis**dim

        free_dof_count = len(self.rhs)
        _validate_ptr(
            self.free_dof_ptr,
            count=box_count,
            total=free_dof_count,
            name="free_dof_ptr",
        )

        _validate_ptr(
            self.free_global_ptr,
            count=box_count,
            total=len(self.free_global_index),
            name="free_global_ptr",
        )
        if len(self.free_global_index) != free_dof_count:
            raise ValueError("free_global_index length must match rhs length")

        _validate_ptr(
            self.fixed_dof_ptr,
            count=box_count,
            total=len(self.fixed_dof_index),
            name="fixed_dof_ptr",
        )
        if len(self.fixed_dof_index) != len(self.fixed_dof_value):
            raise ValueError("fixed_dof_index and fixed_dof_value lengths must match")

        for index in self.free_global_index:
            if index < 0 or index >= dof_capacity:
                raise ValueError("free_global_index contains out-of-range value")
        for index in self.fixed_dof_index:
            if index < 0 or index >= dof_capacity:
                raise ValueError("fixed_dof_index contains out-of-range value")

        if self.operator_mode == "assembled":
            if self.matvec_kernel_id is not None:
                raise ValueError("assembled mode must not provide matvec_kernel_id")
            if self.matvec_payload is not None:
                raise ValueError("assembled mode must not provide matvec_payload")
            if (
                self.csr_indptr is None
                or self.csr_indices is None
                or self.csr_data is None
            ):
                raise ValueError("assembled mode requires CSR payload")
            if len(self.csr_indptr) != free_dof_count + 1:
                raise ValueError("csr_indptr length must be free_dof_count + 1")
            if self.csr_indptr[0] != 0:
                raise ValueError("csr_indptr must start at zero")
            if self.csr_indptr[-1] != len(self.csr_indices):
                raise ValueError("csr_indptr terminal value must match csr_indices")
            if len(self.csr_indices) != len(self.csr_data):
                raise ValueError("csr_indices and csr_data lengths must match")
            return

        if self.matvec_kernel_id is None or self.matvec_kernel_id == "":
            raise ValueError("matrix_free mode requires matvec_kernel_id")
        if (
            self.csr_indptr is not None
            or self.csr_indices is not None
            or self.csr_data is not None
        ):
            raise ValueError("matrix_free mode must not provide CSR payload")

    def matvec(self, x_flat: Sequence[float]) -> tuple[float, ...]:
        size = len(self.rhs)
        if len(x_flat) != size:
            raise ValueError("x_flat length must match operator size")

        if self.operator_mode == "assembled":
            if (
                self.csr_indptr is None
                or self.csr_indices is None
                or self.csr_data is None
            ):
                raise ValueError("assembled mode requires CSR payload")
            out = [0.0] * size
            for row in range(size):
                start = self.csr_indptr[row]
                end = self.csr_indptr[row + 1]
                total = 0.0
                for idx in range(start, end):
                    total += self.csr_data[idx] * float(x_flat[self.csr_indices[idx]])
                out[row] = total
            return tuple(out)

        payload = self.matvec_payload
        if payload is None:
            payload = _get_matrix_free_payload(self.matvec_kernel_id)
        if len(payload.indptr_by_box) != len(self.statuses):
            raise ValueError("matrix_free payload box count mismatch")

        out = [0.0] * size
        for box_index, status in enumerate(self.statuses):
            start = self.free_dof_ptr[box_index]
            end = self.free_dof_ptr[box_index + 1]
            if end <= start or status != "ok":
                continue

            indptr = payload.indptr_by_box[box_index]
            indices = payload.indices_by_box[box_index]
            data = payload.data_by_box[box_index]
            local_size = end - start
            if len(indptr) != local_size + 1:
                raise ValueError("matrix_free payload row pointer mismatch")

            for row in range(local_size):
                r0 = indptr[row]
                r1 = indptr[row + 1]
                total = 0.0
                for idx in range(r0, r1):
                    total += data[idx] * float(x_flat[start + indices[idx]])
                out[start + row] = total
        return tuple(out)

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def as_assembled_arrays(self, *, use_numpy: bool | None = None) -> dict[str, Any]:
        if self.operator_mode != "assembled":
            raise ValueError("as_assembled_arrays requires operator_mode='assembled'")
        if self.csr_indptr is None or self.csr_indices is None or self.csr_data is None:
            raise ValueError("assembled mode requires CSR payload")

        return {
            "dim": _validate_dim(self.dim),
            "shape": self.shape,
            "resolution": self.resolution,
            "spline_degree": self.spline_degree,
            "box_bounds": self.box_bounds,
            "statuses": self.statuses,
            "errors": self.errors,
            "rhs": _materialize_array(
                self.rhs,
                use_numpy=use_numpy,
                dtype=float,
                name="LocalOperatorBatch.rhs",
            ),
            "free_dof_ptr": _materialize_array(
                self.free_dof_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_dof_ptr",
            ),
            "free_global_ptr": _materialize_array(
                self.free_global_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_global_ptr",
            ),
            "free_global_index": _materialize_array(
                self.free_global_index,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_global_index",
            ),
            "fixed_dof_ptr": _materialize_array(
                self.fixed_dof_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.fixed_dof_ptr",
            ),
            "fixed_dof_index": _materialize_array(
                self.fixed_dof_index,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.fixed_dof_index",
            ),
            "fixed_dof_value": _materialize_array(
                self.fixed_dof_value,
                use_numpy=use_numpy,
                dtype=float,
                name="LocalOperatorBatch.fixed_dof_value",
            ),
            "csr_indptr": _materialize_array(
                self.csr_indptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.csr_indptr",
            ),
            "csr_indices": _materialize_array(
                self.csr_indices,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.csr_indices",
            ),
            "csr_data": _materialize_array(
                self.csr_data,
                use_numpy=use_numpy,
                dtype=float,
                name="LocalOperatorBatch.csr_data",
            ),
        }

    def as_matrix_free_descriptor(
        self, *, use_numpy: bool | None = None
    ) -> dict[str, Any]:
        if self.operator_mode != "matrix_free":
            raise ValueError(
                "as_matrix_free_descriptor requires operator_mode='matrix_free'"
            )
        return {
            "dim": _validate_dim(self.dim),
            "shape": self.shape,
            "resolution": self.resolution,
            "spline_degree": self.spline_degree,
            "box_bounds": self.box_bounds,
            "statuses": self.statuses,
            "errors": self.errors,
            "rhs": _materialize_array(
                self.rhs,
                use_numpy=use_numpy,
                dtype=float,
                name="LocalOperatorBatch.rhs",
            ),
            "free_dof_ptr": _materialize_array(
                self.free_dof_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_dof_ptr",
            ),
            "free_global_ptr": _materialize_array(
                self.free_global_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_global_ptr",
            ),
            "free_global_index": _materialize_array(
                self.free_global_index,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.free_global_index",
            ),
            "fixed_dof_ptr": _materialize_array(
                self.fixed_dof_ptr,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.fixed_dof_ptr",
            ),
            "fixed_dof_index": _materialize_array(
                self.fixed_dof_index,
                use_numpy=use_numpy,
                dtype=int,
                name="LocalOperatorBatch.fixed_dof_index",
            ),
            "fixed_dof_value": _materialize_array(
                self.fixed_dof_value,
                use_numpy=use_numpy,
                dtype=float,
                name="LocalOperatorBatch.fixed_dof_value",
            ),
            "matvec_kernel_id": self.matvec_kernel_id,
        }


@dataclass(frozen=True)
class LocalNearfieldSolveBatch:
    """Batched solve outputs for local near-field operators."""

    dim: SpatialDim
    shape: tuple[int, ...]
    statuses: tuple[BatchStatus, ...]
    errors: tuple[str | None, ...]
    free_dof_ptr: tuple[int, ...]
    solution: tuple[float | None, ...]
    residual_norms: tuple[float | None, ...]
    iterations: tuple[int | None, ...]

    def __post_init__(self) -> None:
        _validate_dim(self.dim)
        box_count = _validate_shape(self.shape)

        _validate_statuses(self.statuses)
        if len(self.statuses) != box_count:
            raise ValueError("statuses length must match flattened shape")
        if len(self.errors) != box_count:
            raise ValueError("errors length must match flattened shape")
        if len(self.residual_norms) != box_count:
            raise ValueError("residual_norms length must match flattened shape")
        if len(self.iterations) != box_count:
            raise ValueError("iterations length must match flattened shape")

        dof_count = len(self.solution)
        _validate_ptr(
            self.free_dof_ptr,
            count=box_count,
            total=dof_count,
            name="free_dof_ptr",
        )

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)


@dataclass(frozen=True)
class NearfieldTargetEvaluation:
    """Per-input-target near-field corrections evaluated from local solves."""

    dim: SpatialDim
    input_shape: tuple[int, ...]
    values: tuple[float, ...]
    hit_count: tuple[int, ...]

    def __post_init__(self) -> None:
        _validate_dim(self.dim)
        count = _validate_shape(self.input_shape)
        if len(self.values) != count:
            raise ValueError("values length must match flattened input_shape")
        if len(self.hit_count) != count:
            raise ValueError("hit_count length must match flattened input_shape")

    def values_shaped(self) -> Any:
        return _reshape_flat(self.values, self.input_shape)


@dataclass(frozen=True)
class PotentialCompositionResult:
    """Composed far/near potential values with explicit mode metadata."""

    input_shape: tuple[int, ...]
    far_values: tuple[float, ...]
    near_values: tuple[float, ...]
    combined_values: tuple[float, ...]
    hit_count: tuple[int, ...]
    mode: Literal["far_plus_near", "far_minus_near_direct_plus_near"]

    def __post_init__(self) -> None:
        count = _validate_shape(self.input_shape)
        for name, values in (
            ("far_values", self.far_values),
            ("near_values", self.near_values),
            ("combined_values", self.combined_values),
            ("hit_count", self.hit_count),
        ):
            if len(values) != count:
                raise ValueError(f"{name} length must match flattened input_shape")

    def combined_shaped(self) -> Any:
        return _reshape_flat(self.combined_values, self.input_shape)


def build_signed_source_cloud_2d(
    panel: CurveTrimmedPanel2D,
    *,
    density: Callable[[Any, Any], Any],
    order: int,
    backend_mode: FarfieldBackendMode = "folded",
) -> SignedSourceCloud:
    _validate_order(order, name="order")
    _validate_backend(backend_mode)

    anchor, require_interior_anchor = _panel_anchor_for_backend(
        panel,
        backend_mode=backend_mode,
    )
    folded = folded_curve_quadrature_rule(
        panel,
        order=order,
        anchor=anchor,
        require_interior_anchor=require_interior_anchor,
    )
    points = tuple((float(x), float(y)) for x, y in folded.rule.points)
    weights = tuple(float(weight) for weight in folded.rule.weights)
    densities = _evaluate_density_2d(density, points)
    charges = tuple(
        value * weight for value, weight in zip(densities, weights, strict=True)
    )

    return SignedSourceCloud(
        dim=2,
        points=points,
        weights=weights,
        charges=charges,
        backend_mode=backend_mode,
        order=order,
    )


def build_signed_source_cloud_3d(
    boundary: tuple[tuple[Point3D, Point3D, Point3D], ...],
    *,
    density: Callable[[Any, Any, Any], Any],
    seed: SeedInput3D = "grid-best",
    order: int,
    backend_mode: FarfieldBackendMode = "folded",
) -> SignedSourceCloud:
    _validate_order(order, name="order")
    _validate_backend(backend_mode)

    if not boundary:
        return SignedSourceCloud(
            dim=3,
            points=(),
            weights=(),
            charges=(),
            backend_mode=backend_mode,
            order=order,
        )

    seed_input = seed
    if backend_mode == "jplus" and seed == "grid-best":
        seed_input = "jplus"

    selected_seed = _resolve_seed_3d(boundary, seed=seed_input)
    rule = boundary_quadrature_rule_3d(boundary, seed=selected_seed, order=order)
    points = tuple((float(x), float(y), float(z)) for x, y, z in rule.points)
    weights = tuple(float(weight) for weight in rule.weights)
    densities = _evaluate_density_3d(density, points)
    charges = tuple(
        value * weight for value, weight in zip(densities, weights, strict=True)
    )

    return SignedSourceCloud(
        dim=3,
        points=points,
        weights=weights,
        charges=charges,
        backend_mode=backend_mode,
        order=order,
    )


def source_cloud_over_boxes_2d(
    face: Any,
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
) -> SignedSourceCloudBatch:
    _validate_order(order, name="order")
    _validate_backend(backend_mode)

    clip_batch = face.clip_boxes(
        boxes,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        strict=strict,
    )

    statuses: list[BatchStatus] = []
    errors: list[str | None] = []
    point_ptr = [0]
    points: list[PointND] = []
    weights: list[float] = []
    charges: list[float] = []
    source_box_index: list[int] = []

    for box_index, (status, panel_group, error) in enumerate(
        zip(clip_batch.statuses, clip_batch.panels, clip_batch.errors, strict=True)
    ):
        start = len(points)
        if status != "ok":
            statuses.append(status)
            errors.append(error)
            point_ptr.append(start)
            continue

        try:
            for panel in panel_group:
                cloud = build_signed_source_cloud_2d(
                    panel,
                    density=density,
                    order=order,
                    backend_mode=backend_mode,
                )
                points.extend(cloud.points)
                weights.extend(cloud.weights)
                charges.extend(cloud.charges)
                source_box_index.extend((box_index,) * len(cloud.points))
        except Exception as exc:
            del points[start:]
            del weights[start:]
            del charges[start:]
            del source_box_index[start:]
            if strict:
                raise
            statuses.append("backend_error")
            errors.append(str(exc))
            point_ptr.append(start)
            continue

        statuses.append("ok")
        errors.append(None)
        point_ptr.append(len(points))

    return SignedSourceCloudBatch(
        dim=2,
        shape=clip_batch.shape,
        box_bounds=clip_batch.box_bounds,
        statuses=tuple(statuses),
        errors=tuple(errors),
        point_ptr=tuple(point_ptr),
        points=tuple(points),
        weights=tuple(weights),
        charges=tuple(charges),
        source_box_index=tuple(source_box_index),
        backend_mode=backend_mode,
        order=order,
    )


def source_cloud_over_boxes_3d(
    solid: Any,
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
    linear_deflection: float = 1.0e-3,
    angular_deflection: float = 0.5,
    tol: float = 1.0e-12,
    strict: bool = True,
) -> SignedSourceCloudBatch:
    _validate_order(order, name="order")
    _validate_backend(backend_mode)

    clip_batch = solid.clip_boxes(
        boxes,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        z0=z0,
        z1=z1,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
        tol=tol,
        strict=strict,
        validate_boundary=False,
    )

    statuses: list[BatchStatus] = []
    errors: list[str | None] = []
    point_ptr = [0]
    points: list[PointND] = []
    weights: list[float] = []
    charges: list[float] = []
    source_box_index: list[int] = []

    for box_index, (status, clipped, error) in enumerate(
        zip(clip_batch.statuses, clip_batch.solids, clip_batch.errors, strict=True)
    ):
        start = len(points)
        if status != "ok":
            statuses.append(status)
            errors.append(error)
            point_ptr.append(start)
            continue

        if clipped is None:
            if strict:
                raise RuntimeError("internal clip result is missing solid handle")
            statuses.append("backend_error")
            errors.append("internal clip result is missing solid handle")
            point_ptr.append(start)
            continue

        try:
            boundary = solid_to_oriented_boundary_triangles(
                clipped.solid,
                linear_deflection=linear_deflection,
                angular_deflection=angular_deflection,
                tol=tol,
            )
            cloud = build_signed_source_cloud_3d(
                boundary,
                density=density,
                seed=seed,
                order=order,
                backend_mode=backend_mode,
            )
        except ValueError as exc:
            if _is_empty_boundary_error(exc):
                statuses.append("empty")
                errors.append(None)
                point_ptr.append(start)
                continue
            if strict:
                raise
            statuses.append("backend_error")
            errors.append(str(exc))
            point_ptr.append(start)
            continue
        except Exception as exc:
            if strict:
                raise
            statuses.append("backend_error")
            errors.append(str(exc))
            point_ptr.append(start)
            continue

        points.extend(cloud.points)
        weights.extend(cloud.weights)
        charges.extend(cloud.charges)
        source_box_index.extend((box_index,) * len(cloud.points))

        statuses.append("ok" if cloud.points else "empty")
        errors.append(None)
        point_ptr.append(len(points))

    return SignedSourceCloudBatch(
        dim=3,
        shape=clip_batch.shape,
        box_bounds=clip_batch.box_bounds,
        statuses=tuple(statuses),
        errors=tuple(errors),
        point_ptr=tuple(point_ptr),
        points=tuple(points),
        weights=tuple(weights),
        charges=tuple(charges),
        source_box_index=tuple(source_box_index),
        backend_mode=backend_mode,
        order=order,
    )


def build_source_box_selection_from_lists(
    shape: tuple[int, ...],
    *,
    self_boxes: Any = None,
    list1_boxes: Any = None,
    list3_boxes: Any = None,
    list4_boxes: Any = None,
    include: Sequence[InteractionListName] = ("self", "list1", "list3", "list4"),
) -> SourceBoxSelectionBatch:
    box_count = _validate_shape(shape)

    include_set = set(include)
    unknown = tuple(
        name for name in include_set if name not in _VALID_INTERACTION_LISTS
    )
    if unknown:
        raise ValueError(f"unsupported interaction list name(s): {unknown!r}")

    per_list: dict[str, tuple[tuple[int, ...], ...]] = {
        "self": _coerce_relation_entries(
            self_boxes, box_count=box_count, name="self_boxes"
        ),
        "list1": _coerce_relation_entries(
            list1_boxes, box_count=box_count, name="list1_boxes"
        ),
        "list3": _coerce_relation_entries(
            list3_boxes, box_count=box_count, name="list3_boxes"
        ),
        "list4": _coerce_relation_entries(
            list4_boxes, box_count=box_count, name="list4_boxes"
        ),
    }

    ptr = [0]
    indices: list[int] = []
    ordered_labels = ("self", "list1", "list3", "list4")
    for box_index in range(box_count):
        seen: set[int] = set()
        ordered: list[int] = []
        for label in ordered_labels:
            if label not in include_set:
                continue
            for source_box in per_list[label][box_index]:
                if source_box in seen:
                    continue
                seen.add(source_box)
                ordered.append(source_box)
        indices.extend(ordered)
        ptr.append(len(indices))

    return SourceBoxSelectionBatch(
        shape=shape,
        source_box_ptr=tuple(ptr),
        source_box_index=tuple(indices),
    )


def build_restricted_sources_from_selection(
    *,
    source_cloud: SignedSourceCloudBatch,
    selection: SourceBoxSelectionBatch,
    strict: bool = True,
) -> RestrictedSourceBatch:
    source_box_count = _validate_shape(source_cloud.shape)
    points_by_source_box: list[list[int]] = [[] for _ in range(source_box_count)]
    for point_index, source_box in enumerate(source_cloud.source_box_index):
        if source_box < 0 or source_box >= source_box_count:
            raise ValueError(
                "source_cloud.source_box_index contains out-of-range value"
            )
        points_by_source_box[source_box].append(point_index)

    box_count = _validate_shape(selection.shape)
    ptr = [0]
    points: list[PointND] = []
    charges: list[float] = []

    for box_index in range(box_count):
        start = selection.source_box_ptr[box_index]
        end = selection.source_box_ptr[box_index + 1]
        for source_box in selection.source_box_index[start:end]:
            if source_box < 0 or source_box >= source_box_count:
                if strict:
                    raise ValueError(
                        f"selection source box index out of range: {source_box}"
                    )
                continue
            for point_index in points_by_source_box[source_box]:
                points.append(source_cloud.points[point_index])
                charges.append(source_cloud.charges[point_index])
        ptr.append(len(points))

    return RestrictedSourceBatch(
        dim=source_cloud.dim,
        shape=selection.shape,
        source_ptr=tuple(ptr),
        source_points=tuple(points),
        source_charges=tuple(charges),
    )


def build_restricted_sources_from_interaction_lists(
    *,
    source_cloud: SignedSourceCloudBatch,
    shape: tuple[int, ...],
    self_boxes: Any = None,
    list1_boxes: Any = None,
    list3_boxes: Any = None,
    list4_boxes: Any = None,
    include: Sequence[InteractionListName] = ("self", "list1", "list3", "list4"),
    strict: bool = True,
) -> RestrictedSourceBatch:
    selection = build_source_box_selection_from_lists(
        shape,
        self_boxes=self_boxes,
        list1_boxes=list1_boxes,
        list3_boxes=list3_boxes,
        list4_boxes=list4_boxes,
        include=include,
    )
    return build_restricted_sources_from_selection(
        source_cloud=source_cloud,
        selection=selection,
        strict=strict,
    )


def build_nearfield_target_batch(
    dim: SpatialDim,
    boxes: (
        Box2D
        | Sequence[Box2D]
        | Box2DArray
        | Box3D
        | Sequence[Box3D]
        | Box3DArray
        | None
    ) = None,
    *,
    local_shape: tuple[int, ...] | None = None,
    local_box_bounds: tuple[BoundsND, ...] | None = None,
    points: Any = None,
    x: Any = None,
    y: Any = None,
    z: Any = None,
    x0: Any = None,
    x1: Any = None,
    y0: Any = None,
    y1: Any = None,
    z0: Any = None,
    z1: Any = None,
    strict: bool = True,
) -> NearfieldTargetBatch:
    dim_value = _validate_dim(dim)

    if (points is not None) and any(value is not None for value in (x, y, z)):
        raise ValueError("provide either points=... or x/y(/z) arrays, not both")

    if points is not None:
        input_shape, input_points, input_indices = _normalize_point_input(
            dim_value, points
        )
    else:
        if dim_value == 2:
            if z is not None:
                raise ValueError("z targets are unsupported when dim=2")
            if x is None or y is None:
                raise ValueError("x and y target arrays are required in array mode")
            target_shape, arrays = _cad._broadcast_coordinate_values(  # type: ignore[attr-defined]
                ("x", "y"),
                (x, y),
            )
            input_points = tuple(
                (arrays[0][idx], arrays[1][idx]) for idx in range(len(arrays[0]))
            )
        else:
            if x is None or y is None or z is None:
                raise ValueError("x, y, and z target arrays are required in array mode")
            target_shape, arrays = _cad._broadcast_coordinate_values(  # type: ignore[attr-defined]
                ("x", "y", "z"),
                (x, y, z),
            )
            input_points = tuple(
                (arrays[0][idx], arrays[1][idx], arrays[2][idx])
                for idx in range(len(arrays[0]))
            )
        input_shape = target_shape
        input_indices = tuple(range(len(input_points)))

    if local_box_bounds is None:
        shape, box_bounds = _normalize_box_bounds(
            dim_value,
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
        )
    else:
        if local_shape is None:
            raise ValueError(
                "local_shape is required when local_box_bounds is provided"
            )
        _validate_bounds(local_box_bounds, dim=dim_value)
        if _validate_shape(local_shape) != len(local_box_bounds):
            raise ValueError("local_box_bounds length must match local_shape")
        shape = local_shape
        box_bounds = local_box_bounds

    box_count = _validate_shape(shape)
    statuses: list[BatchStatus] = []
    errors: list[str | None] = []
    target_ptr = [0]
    target_points: list[PointND] = []
    target_index: list[int] = []

    for bounds in box_bounds:
        start = len(target_points)
        try:
            if dim_value == 2:
                Box2D(*cast(tuple[float, float, float, float], bounds))
            else:
                Box3D(*cast(tuple[float, float, float, float, float, float], bounds))
        except (ValueError, TypeError, OverflowError) as exc:
            if strict:
                raise
            statuses.append("invalid_box")
            errors.append(str(exc))
            target_ptr.append(start)
            continue

        for point, input_index in zip(input_points, input_indices, strict=True):
            if _point_inside_bounds(point, bounds, dim=dim_value):
                target_points.append(point)
                target_index.append(input_index)

        statuses.append("ok")
        errors.append(None)
        target_ptr.append(len(target_points))

    if len(statuses) != box_count:
        raise RuntimeError("internal target mapping status mismatch")

    return NearfieldTargetBatch(
        dim=dim,
        shape=shape,
        box_bounds=box_bounds,
        statuses=tuple(statuses),
        errors=tuple(errors),
        target_ptr=tuple(target_ptr),
        target_points=tuple(target_points),
        target_input_index=tuple(target_index),
        input_shape=input_shape,
    )


def build_local_box_boundary_trace(
    dim: SpatialDim,
    boxes: (
        Box2D
        | Sequence[Box2D]
        | Box2DArray
        | Box3D
        | Sequence[Box3D]
        | Box3DArray
        | None
    ) = None,
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
) -> BoundaryTraceBatch:
    dim_value = _validate_dim(dim)
    _validate_order(trace_order, name="trace_order")

    shape, box_bounds = _normalize_box_bounds(
        dim_value,
        boxes,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        z0=z0,
        z1=z1,
    )

    statuses: list[BatchStatus] = []
    errors: list[str | None] = []
    trace_ptr = [0]
    trace_points: list[PointND] = []
    trace_values: list[float] = []

    for bounds in box_bounds:
        start = len(trace_points)
        try:
            if dim_value == 2:
                Box2D(*cast(tuple[float, float, float, float], bounds))
                points = _sample_boundary_points_2d(
                    cast(tuple[float, float, float, float], bounds),
                    trace_order=trace_order,
                )
                values = _evaluate_field_2d(farfield_potential, points)
            else:
                Box3D(*cast(tuple[float, float, float, float, float, float], bounds))
                points = _sample_boundary_points_3d(
                    cast(tuple[float, float, float, float, float, float], bounds),
                    trace_order=trace_order,
                )
                values = _evaluate_field_3d(farfield_potential, points)
        except (ValueError, TypeError, OverflowError) as exc:
            if strict:
                raise
            statuses.append("invalid_box")
            errors.append(str(exc))
            trace_ptr.append(start)
            continue
        except Exception as exc:
            if strict:
                raise
            statuses.append("backend_error")
            errors.append(str(exc))
            trace_ptr.append(start)
            continue

        trace_points.extend(points)
        trace_values.extend(values)
        statuses.append("ok")
        errors.append(None)
        trace_ptr.append(len(trace_points))

    return BoundaryTraceBatch(
        dim=dim,
        shape=shape,
        box_bounds=box_bounds,
        statuses=tuple(statuses),
        errors=tuple(errors),
        trace_ptr=tuple(trace_ptr),
        trace_points=tuple(trace_points),
        trace_values=tuple(trace_values),
    )


def assemble_local_nearfield_operators(
    dim: SpatialDim,
    boxes: (
        Box2D
        | Sequence[Box2D]
        | Box2DArray
        | Box3D
        | Sequence[Box3D]
        | Box3DArray
        | None
    ) = None,
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
) -> LocalOperatorBatch:
    dim_value = _validate_dim(dim)
    if operator_mode not in _VALID_OPERATOR_MODES:
        raise ValueError(f"unsupported operator_mode: {operator_mode!r}")
    if resolution < 1:
        raise ValueError("resolution must be positive")
    if spline_degree < 1:
        raise ValueError("spline_degree must be positive")
    _validate_order(quadrature_order, name="quadrature_order")

    if restricted_sources.dim != dim or boundary_trace.dim != dim:
        raise ValueError(
            "restricted_sources and boundary_trace dimensions must match dim"
        )

    if boxes is None and all(value is None for value in (x0, x1, y0, y1, z0, z1)):
        shape = boundary_trace.shape
        box_bounds = boundary_trace.box_bounds
    else:
        shape, box_bounds = _normalize_box_bounds(
            dim_value,
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
        )

    if shape != boundary_trace.shape:
        raise ValueError("box shape must match boundary_trace shape")
    if shape != restricted_sources.shape:
        raise ValueError("box shape must match restricted_sources shape")
    if not _bounds_match(box_bounds, boundary_trace.box_bounds):
        raise ValueError("box bounds must match boundary_trace.box_bounds")

    box_count = _validate_shape(shape)
    n_axis = resolution + spline_degree

    statuses: list[BatchStatus] = []
    errors: list[str | None] = []
    free_dof_ptr = [0]
    free_global_ptr = [0]
    free_global_index: list[int] = []
    fixed_dof_ptr = [0]
    fixed_dof_index: list[int] = []
    fixed_dof_value: list[float] = []
    rhs: list[float] = []

    global_indptr = [0]
    global_indices: list[int] = []
    global_data: list[float] = []

    mf_indptr_by_box: list[tuple[int, ...]] = []
    mf_indices_by_box: list[tuple[int, ...]] = []
    mf_data_by_box: list[tuple[float, ...]] = []

    knots_by_axis = tuple(
        _open_uniform_knots(num_elements=resolution, degree=spline_degree)
        for _ in range(dim_value)
    )

    for box_index in range(box_count):
        start = len(rhs)
        trace_status = boundary_trace.statuses[box_index]
        if trace_status != "ok":
            statuses.append(trace_status)
            errors.append(boundary_trace.errors[box_index])
            free_dof_ptr.append(start)
            free_global_ptr.append(len(free_global_index))
            fixed_dof_ptr.append(len(fixed_dof_index))
            mf_indptr_by_box.append((0,))
            mf_indices_by_box.append(())
            mf_data_by_box.append(())
            continue

        bounds = box_bounds[box_index]
        try:
            if dim_value == 2:
                Box2D(*cast(tuple[float, float, float, float], bounds))
            else:
                Box3D(*cast(tuple[float, float, float, float, float, float], bounds))

            rows = _assemble_stiffness_rows(
                bounds=bounds,
                dim=dim_value,
                resolution=resolution,
                spline_degree=spline_degree,
                quadrature_order=quadrature_order,
            )
            rhs_full = [0.0 for _ in range(len(rows))]

            source_start = restricted_sources.source_ptr[box_index]
            source_end = restricted_sources.source_ptr[box_index + 1]
            source_points = restricted_sources.source_points[source_start:source_end]
            source_charges = restricted_sources.source_charges[source_start:source_end]

            for point, charge in zip(source_points, source_charges, strict=True):
                if not _point_inside_bounds(point, bounds, dim=dim_value):
                    if strict:
                        raise ValueError(
                            "restricted source point lies outside local box"
                        )
                    continue
                terms = _basis_terms_at_point_nd(
                    tuple(float(value) for value in point),
                    bounds=bounds,
                    dim=dim_value,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_axis=n_axis,
                    knots_by_axis=knots_by_axis,
                )
                for index, basis_value, _grad in terms:
                    rhs_full[index] += float(charge) * basis_value

            trace_start = boundary_trace.trace_ptr[box_index]
            trace_end = boundary_trace.trace_ptr[box_index + 1]
            trace_points = boundary_trace.trace_points[trace_start:trace_end]
            trace_values = boundary_trace.trace_values[trace_start:trace_end]
            fixed_values = _fixed_dof_values_from_trace(
                bounds=bounds,
                dim=dim_value,
                n_axis=n_axis,
                trace_points=trace_points,
                trace_values=trace_values,
            )

            local_rows, local_rhs, free_indices = _apply_dirichlet_and_reduce(
                rows,
                rhs_full,
                fixed_values=fixed_values,
            )
            local_indptr, local_indices, local_data = _rows_to_csr(local_rows)

            fixed_indices = tuple(sorted(fixed_values))
            for fixed_index in fixed_indices:
                fixed_dof_index.append(fixed_index)
                fixed_dof_value.append(float(fixed_values[fixed_index]))
            fixed_dof_ptr.append(len(fixed_dof_index))

            free_global_index.extend(free_indices)
            free_global_ptr.append(len(free_global_index))
        except (ValueError, TypeError, OverflowError) as exc:
            if strict:
                raise
            statuses.append("invalid_box")
            errors.append(str(exc))
            free_dof_ptr.append(start)
            free_global_ptr.append(len(free_global_index))
            fixed_dof_ptr.append(len(fixed_dof_index))
            mf_indptr_by_box.append((0,))
            mf_indices_by_box.append(())
            mf_data_by_box.append(())
            continue
        except Exception as exc:
            if strict:
                raise
            statuses.append("backend_error")
            errors.append(str(exc))
            free_dof_ptr.append(start)
            free_global_ptr.append(len(free_global_index))
            fixed_dof_ptr.append(len(fixed_dof_index))
            mf_indptr_by_box.append((0,))
            mf_indices_by_box.append(())
            mf_data_by_box.append(())
            continue

        rhs.extend(local_rhs)
        end = len(rhs)
        free_dof_ptr.append(end)

        mf_indptr_by_box.append(local_indptr)
        mf_indices_by_box.append(local_indices)
        mf_data_by_box.append(local_data)

        if operator_mode == "assembled":
            local_size = len(local_rhs)
            for row in range(local_size):
                r0 = local_indptr[row]
                r1 = local_indptr[row + 1]
                for entry in range(r0, r1):
                    global_indices.append(start + local_indices[entry])
                    global_data.append(local_data[entry])
                global_indptr.append(len(global_indices))

        statuses.append("ok")
        errors.append(None)

    if operator_mode == "assembled":
        csr_indptr_value: tuple[int, ...] | None = tuple(global_indptr)
        csr_indices_value: tuple[int, ...] | None = tuple(global_indices)
        csr_data_value: tuple[float, ...] | None = tuple(global_data)
        kernel_id: str | None = None
        payload_value: _MatrixFreePayload | None = None
    else:
        payload = _MatrixFreePayload(
            indptr_by_box=tuple(mf_indptr_by_box),
            indices_by_box=tuple(mf_indices_by_box),
            data_by_box=tuple(mf_data_by_box),
        )
        csr_indptr_value = None
        csr_indices_value = None
        csr_data_value = None
        kernel_id = _register_matrix_free_payload(payload)
        payload_value = payload

    return LocalOperatorBatch(
        dim=dim,
        operator_mode=operator_mode,
        resolution=resolution,
        spline_degree=spline_degree,
        shape=shape,
        box_bounds=box_bounds,
        statuses=tuple(statuses),
        errors=tuple(errors),
        free_dof_ptr=tuple(free_dof_ptr),
        rhs=tuple(rhs),
        free_global_ptr=tuple(free_global_ptr),
        free_global_index=tuple(free_global_index),
        fixed_dof_ptr=tuple(fixed_dof_ptr),
        fixed_dof_index=tuple(fixed_dof_index),
        fixed_dof_value=tuple(fixed_dof_value),
        csr_indptr=csr_indptr_value,
        csr_indices=csr_indices_value,
        csr_data=csr_data_value,
        matvec_kernel_id=kernel_id,
        matvec_payload=payload_value,
    )


def solve_local_operator_batch(
    operators: LocalOperatorBatch,
    *,
    tolerance: float = 1.0e-10,
    max_iterations: int | None = None,
) -> LocalNearfieldSolveBatch:
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    box_count = _validate_shape(operators.shape)
    statuses = list(operators.statuses)
    errors = list(operators.errors)
    residual_norms: list[float | None] = [None] * box_count
    iterations: list[int | None] = [None] * box_count
    solution: list[float | None] = [None] * len(operators.rhs)

    for box_index, status in enumerate(operators.statuses):
        start = operators.free_dof_ptr[box_index]
        end = operators.free_dof_ptr[box_index + 1]
        size = end - start
        if size <= 0 or status != "ok":
            continue

        rhs_segment = tuple(float(value) for value in operators.rhs[start:end])

        if operators.operator_mode == "assembled":
            if (
                operators.csr_indptr is None
                or operators.csr_indices is None
                or operators.csr_data is None
            ):
                raise ValueError("assembled mode requires CSR payload")

            row_start = operators.csr_indptr[start]
            row_end = operators.csr_indptr[end]
            local_indptr = tuple(
                operators.csr_indptr[idx] - row_start for idx in range(start, end + 1)
            )
            local_indices = tuple(
                operators.csr_indices[idx] - start for idx in range(row_start, row_end)
            )
            local_data = operators.csr_data[row_start:row_end]

            def matvec_local(vector: tuple[float, ...]) -> tuple[float, ...]:
                out = [0.0] * size
                for row in range(size):
                    r0 = local_indptr[row]
                    r1 = local_indptr[row + 1]
                    total = 0.0
                    for idx in range(r0, r1):
                        total += local_data[idx] * vector[local_indices[idx]]
                    out[row] = total
                return tuple(out)

        else:
            payload = operators.matvec_payload
            if payload is None:
                payload = _get_matrix_free_payload(operators.matvec_kernel_id)
            if len(payload.indptr_by_box) != len(operators.statuses):
                raise ValueError("matrix_free payload box count mismatch")

            local_indptr = payload.indptr_by_box[box_index]
            local_indices = payload.indices_by_box[box_index]
            local_data = payload.data_by_box[box_index]
            if len(local_indptr) != size + 1:
                raise ValueError("matrix_free local CSR pointer mismatch")

            def matvec_local(vector: tuple[float, ...]) -> tuple[float, ...]:
                out = [0.0] * size
                for row in range(size):
                    r0 = local_indptr[row]
                    r1 = local_indptr[row + 1]
                    total = 0.0
                    for idx in range(r0, r1):
                        total += local_data[idx] * vector[local_indices[idx]]
                    out[row] = total
                return tuple(out)

        try:
            local_max_iterations = (
                max_iterations if max_iterations is not None else max(8 * size, 200)
            )
            local_solution, local_iters, local_residual = _cg_solve(
                matvec_local,
                rhs_segment,
                tolerance=tolerance,
                max_iterations=local_max_iterations,
            )
            for local_idx, value in enumerate(local_solution):
                solution[start + local_idx] = value
            residual_norms[box_index] = local_residual
            iterations[box_index] = local_iters
        except Exception as exc:
            statuses[box_index] = "backend_error"
            errors[box_index] = str(exc)
            residual_norms[box_index] = None
            iterations[box_index] = None
            for local_idx in range(start, end):
                solution[local_idx] = None

    return LocalNearfieldSolveBatch(
        dim=operators.dim,
        shape=operators.shape,
        statuses=tuple(statuses),
        errors=tuple(errors),
        free_dof_ptr=operators.free_dof_ptr,
        solution=tuple(solution),
        residual_norms=tuple(residual_norms),
        iterations=tuple(iterations),
    )


def evaluate_local_nearfield_targets(
    *,
    operators: LocalOperatorBatch,
    solve: LocalNearfieldSolveBatch,
    targets: NearfieldTargetBatch,
    aggregation: Literal["sum", "average"] = "sum",
) -> NearfieldTargetEvaluation:
    if operators.dim != solve.dim or operators.dim != targets.dim:
        raise ValueError("operators, solve, and targets dimensions must match")
    if operators.shape != solve.shape or operators.shape != targets.shape:
        raise ValueError("operators, solve, and targets shapes must match")
    if not _bounds_match(operators.box_bounds, targets.box_bounds):
        raise ValueError("targets.box_bounds must match operators.box_bounds")
    if operators.free_dof_ptr != solve.free_dof_ptr:
        raise ValueError("solve and operators free_dof_ptr must match")
    if aggregation not in {"sum", "average"}:
        raise ValueError(f"unsupported aggregation mode: {aggregation!r}")

    dim_value = _validate_dim(operators.dim)
    n_axis = operators.resolution + operators.spline_degree
    knots_by_axis = tuple(
        _open_uniform_knots(
            num_elements=operators.resolution, degree=operators.spline_degree
        )
        for _ in range(dim_value)
    )

    input_count = _validate_shape(targets.input_shape)
    accum = [0.0 for _ in range(input_count)]
    hit = [0 for _ in range(input_count)]

    box_count = _validate_shape(operators.shape)
    for box_index in range(box_count):
        if (
            operators.statuses[box_index] != "ok"
            or solve.statuses[box_index] != "ok"
            or targets.statuses[box_index] != "ok"
        ):
            continue

        target_start = targets.target_ptr[box_index]
        target_end = targets.target_ptr[box_index + 1]
        if target_end <= target_start:
            continue

        free_start = operators.free_dof_ptr[box_index]
        free_end = operators.free_dof_ptr[box_index + 1]
        free_global_start = operators.free_global_ptr[box_index]
        free_global_end = operators.free_global_ptr[box_index + 1]

        free_values = solve.solution[free_start:free_end]
        free_indices = operators.free_global_index[free_global_start:free_global_end]
        if len(free_values) != len(free_indices):
            raise ValueError("free solution slice length mismatch")

        coeff: dict[int, float] = {}
        for global_index, value in zip(free_indices, free_values, strict=True):
            if value is None:
                continue
            coeff[global_index] = float(value)

        fixed_start = operators.fixed_dof_ptr[box_index]
        fixed_end = operators.fixed_dof_ptr[box_index + 1]
        fixed_indices = operators.fixed_dof_index[fixed_start:fixed_end]
        fixed_values = operators.fixed_dof_value[fixed_start:fixed_end]
        for global_index, value in zip(fixed_indices, fixed_values, strict=True):
            coeff[global_index] = float(value)

        bounds = operators.box_bounds[box_index]
        for target_index in range(target_start, target_end):
            point = targets.target_points[target_index]
            terms = _basis_terms_at_point_nd(
                tuple(float(component) for component in point),
                bounds=bounds,
                dim=dim_value,
                resolution=operators.resolution,
                spline_degree=operators.spline_degree,
                n_axis=n_axis,
                knots_by_axis=knots_by_axis,
            )
            value = 0.0
            for global_index, basis_value, _grad in terms:
                value += coeff.get(global_index, 0.0) * basis_value

            input_index = targets.target_input_index[target_index]
            accum[input_index] += value
            hit[input_index] += 1

    if aggregation == "average":
        for idx, count in enumerate(hit):
            if count > 0:
                accum[idx] /= float(count)

    return NearfieldTargetEvaluation(
        dim=operators.dim,
        input_shape=targets.input_shape,
        values=tuple(accum),
        hit_count=tuple(hit),
    )


def compose_far_and_near_potentials(
    *,
    far_values: Any,
    near_evaluation: NearfieldTargetEvaluation,
    far_includes_near: bool = False,
    near_direct_values: Any | None = None,
) -> PotentialCompositionResult:
    """Compose far and near values with explicit anti-double-counting semantics.

    - If ``far_includes_near`` is ``False``: ``combined = far + near``.
    - If ``far_includes_near`` is ``True``:
      ``combined = far - near_direct + near`` and ``near_direct_values`` is required.
    """

    near_values = near_evaluation.values
    count = len(near_values)

    far_flat = _flatten_numeric_values(far_values, name="far_values")
    if len(far_flat) == 1 and count != 1:
        far_flat = far_flat * count
    if len(far_flat) != count:
        raise ValueError("far_values length must match near evaluation input size")

    if far_includes_near:
        if near_direct_values is None:
            raise ValueError(
                "near_direct_values is required when far_includes_near=True"
            )
        near_direct_flat = _flatten_numeric_values(
            near_direct_values,
            name="near_direct_values",
        )
        if len(near_direct_flat) == 1 and count != 1:
            near_direct_flat = near_direct_flat * count
        if len(near_direct_flat) != count:
            raise ValueError(
                "near_direct_values length must match near evaluation input size"
            )
        combined = tuple(
            far_flat[idx] - near_direct_flat[idx] + near_values[idx]
            for idx in range(count)
        )
        mode: Literal["far_plus_near", "far_minus_near_direct_plus_near"] = (
            "far_minus_near_direct_plus_near"
        )
    else:
        combined = tuple(far_flat[idx] + near_values[idx] for idx in range(count))
        mode = "far_plus_near"

    return PotentialCompositionResult(
        input_shape=near_evaluation.input_shape,
        far_values=tuple(float(value) for value in far_flat),
        near_values=near_values,
        combined_values=combined,
        hit_count=near_evaluation.hit_count,
        mode=mode,
    )


__all__ = [
    "BoundaryTraceBatch",
    "BoundsND",
    "FarfieldBackendMode",
    "InteractionListName",
    "LocalNearfieldSolveBatch",
    "LocalOperatorBatch",
    "NearfieldTargetEvaluation",
    "NearfieldTargetBatch",
    "NearfieldOperatorMode",
    "PointND",
    "PotentialCompositionResult",
    "RestrictedSourceBatch",
    "SignedSourceCloud",
    "SignedSourceCloudBatch",
    "SourceBoxSelectionBatch",
    "SpatialDim",
    "assemble_local_nearfield_operators",
    "build_nearfield_target_batch",
    "build_local_box_boundary_trace",
    "build_restricted_sources_from_interaction_lists",
    "build_restricted_sources_from_selection",
    "build_signed_source_cloud_2d",
    "build_signed_source_cloud_3d",
    "build_source_box_selection_from_lists",
    "compose_far_and_near_potentials",
    "evaluate_local_nearfield_targets",
    "solve_local_operator_batch",
    "source_cloud_over_boxes_2d",
    "source_cloud_over_boxes_3d",
]
