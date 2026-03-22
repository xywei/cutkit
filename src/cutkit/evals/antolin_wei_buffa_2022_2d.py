"""Section 6 protocol reproductions for Antolin-Wei-Buffa (2022, 2D).

This module implements the grid/cell protocol and error definitions described
in Section 6 of:

Pablo Antolin, Xiaodong Wei, Annalisa Buffa (2022),
"Robust Numerical Integration on Curved Polyhedra Based on Folded
Decompositions", Computer Methods in Applied Mechanics and Engineering.
DOI: 10.1016/j.cma.2022.114948.
arXiv: https://arxiv.org/abs/2109.03734.

The implementation targets Sections 6.1.1, 6.1.2, and 6.2 with two paths:

- polygonized CUTKIT MVP helpers (fast fallback), and
- CAD-native helpers with OpenCascade exact cell clipping.
"""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import cos, exp, sin, sqrt
from typing import Any, Callable, Literal, cast

import importlib.util

from cutkit.geometry import (
    CurveTrimmedPanel2D,
    PanelLoop2D,
    Point2D,
    TrimmedPanel2D,
    curve_loop_signed_area,
)
from cutkit.io import (
    OpenCascadeUnavailableError,
    build_section_6_1_1_face,
    build_section_6_1_2_face,
    intersect_face_with_rectangle,
    opencascade_available,
)
from cutkit.quadrature import (
    folded_curve_quadrature_rule,
    folded_quadrature_rule,
    gauss_legendre_01,
)

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

NUMPY_ACCELERATION_ENABLED = _np is not None
OPENCASCADE_CAD_AVAILABLE = opencascade_available()
CAD_ANCHOR_SAMPLE_POINTS = 128

Polygon2D = tuple[Point2D, ...]


def _bspline_basis(i: int, degree: int, u: float, knots: tuple[float, ...]) -> float:
    if degree == 0:
        left = knots[i]
        right = knots[i + 1]
        if left <= u < right:
            return 1.0
        if u == knots[-1] and right == knots[-1]:
            return 1.0
        return 0.0

    value = 0.0

    denom_left = knots[i + degree] - knots[i]
    if denom_left > 0.0:
        value += ((u - knots[i]) / denom_left) * _bspline_basis(i, degree - 1, u, knots)

    denom_right = knots[i + degree + 1] - knots[i + 1]
    if denom_right > 0.0:
        value += ((knots[i + degree + 1] - u) / denom_right) * _bspline_basis(
            i + 1,
            degree - 1,
            u,
            knots,
        )

    return value


def _eval_quadratic_bspline_curve(u: float) -> Point2D:
    knots = (0.0, 0.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 1.0)
    controls: tuple[Point2D, ...] = (
        (0.0, 0.25),
        (0.25, 0.0),
        (0.5, 0.5),
        (0.9, 0.25),
        (0.8, 0.125),
        (0.75, 0.0),
    )

    x = 0.0
    y = 0.0
    for i, point in enumerate(controls):
        coeff = _bspline_basis(i, 2, u, knots)
        x += coeff * point[0]
        y += coeff * point[1]
    return (x, y)


def _eval_quarter_circle_rational_bezier(t: float) -> Point2D:
    p0 = (0.0, 0.5)
    p1 = (0.0, 0.0)
    p2 = (0.5, 0.0)
    w0 = 1.0
    w1 = 1.0 / sqrt(2.0)
    w2 = 1.0

    b0 = (1.0 - t) * (1.0 - t)
    b1 = 2.0 * t * (1.0 - t)
    b2 = t * t

    denominator = w0 * b0 + w1 * b1 + w2 * b2
    x = (w0 * b0 * p0[0] + w1 * b1 * p1[0] + w2 * b2 * p2[0]) / denominator
    y = (w0 * b0 * p0[1] + w1 * b1 * p1[1] + w2 * b2 * p2[1]) / denominator
    return (x, y)


def _sample_curve(
    evaluator: Callable[[float], Point2D],
    *,
    sample_count: int,
) -> Polygon2D:
    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")

    points: list[Point2D] = []
    for i in range(sample_count + 1):
        points.append(evaluator(i / sample_count))
    return tuple(points)


def build_section_6_1_1_bspline_panel(*, sample_count: int = 256) -> TrimmedPanel2D:
    """Build the 2D B-rep from Section 6.1.1 (quadratic B-spline edge)."""

    curved = _sample_curve(_eval_quadratic_bspline_curve, sample_count=sample_count)
    loop_points = (*curved, (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return TrimmedPanel2D(outer=PanelLoop2D(loop_points))


def build_section_6_1_2_rational_panel(*, sample_count: int = 256) -> TrimmedPanel2D:
    """Build the 2D B-rep variant from Section 6.1.2 (rational curve edge)."""

    curved = _sample_curve(
        _eval_quarter_circle_rational_bezier, sample_count=sample_count
    )
    loop_points = (*curved, (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return TrimmedPanel2D(outer=PanelLoop2D(loop_points))


@dataclass(frozen=True)
class CartesianCell2D:
    """One Cartesian cell in the background grid."""

    ix: int
    iy: int
    x0: float
    x1: float
    y0: float
    y1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def area(self) -> float:
        return self.width * self.height


@dataclass(frozen=True)
class CellClipResult:
    """Cell classification with clipped polygon in the cell coordinates."""

    cell: CartesianCell2D
    kind: Literal["outside", "inside", "trimmed"]
    polygon: Polygon2D
    area: float


def _signed_area(polygon: Polygon2D) -> float:
    if len(polygon) < 3:
        return 0.0
    accum = 0.0
    for idx, (x0, y0) in enumerate(polygon):
        x1, y1 = polygon[(idx + 1) % len(polygon)]
        accum += x0 * y1 - x1 * y0
    return 0.5 * accum


def _clean_polygon(points: list[Point2D], *, tol: float = 1.0e-14) -> Polygon2D:
    cleaned: list[Point2D] = []
    for point in points:
        if not cleaned:
            cleaned.append(point)
            continue
        if (
            abs(point[0] - cleaned[-1][0]) <= tol
            and abs(point[1] - cleaned[-1][1]) <= tol
        ):
            continue
        cleaned.append(point)

    if len(cleaned) > 1:
        first = cleaned[0]
        last = cleaned[-1]
        if abs(first[0] - last[0]) <= tol and abs(first[1] - last[1]) <= tol:
            cleaned.pop()

    if len(cleaned) < 3:
        return ()
    return tuple(cleaned)


def _intersect_with_x(a: Point2D, b: Point2D, x_target: float) -> Point2D:
    ax, ay = a
    bx, by = b
    dx = bx - ax
    if abs(dx) <= 1.0e-16:
        return (x_target, ay)
    t = (x_target - ax) / dx
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return (x_target, ay + t * (by - ay))


def _intersect_with_y(a: Point2D, b: Point2D, y_target: float) -> Point2D:
    ax, ay = a
    bx, by = b
    dy = by - ay
    if abs(dy) <= 1.0e-16:
        return (ax, y_target)
    t = (y_target - ay) / dy
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    return (ax + t * (bx - ax), y_target)


def _clip_left(polygon: Polygon2D, x_min: float) -> Polygon2D:
    if not polygon:
        return ()

    out: list[Point2D] = []
    prev = polygon[-1]
    prev_in = prev[0] >= x_min
    for curr in polygon:
        curr_in = curr[0] >= x_min
        if curr_in:
            if not prev_in:
                out.append(_intersect_with_x(prev, curr, x_min))
            out.append(curr)
        elif prev_in:
            out.append(_intersect_with_x(prev, curr, x_min))
        prev = curr
        prev_in = curr_in
    return _clean_polygon(out)


def _clip_right(polygon: Polygon2D, x_max: float) -> Polygon2D:
    if not polygon:
        return ()

    out: list[Point2D] = []
    prev = polygon[-1]
    prev_in = prev[0] <= x_max
    for curr in polygon:
        curr_in = curr[0] <= x_max
        if curr_in:
            if not prev_in:
                out.append(_intersect_with_x(prev, curr, x_max))
            out.append(curr)
        elif prev_in:
            out.append(_intersect_with_x(prev, curr, x_max))
        prev = curr
        prev_in = curr_in
    return _clean_polygon(out)


def _clip_bottom(polygon: Polygon2D, y_min: float) -> Polygon2D:
    if not polygon:
        return ()

    out: list[Point2D] = []
    prev = polygon[-1]
    prev_in = prev[1] >= y_min
    for curr in polygon:
        curr_in = curr[1] >= y_min
        if curr_in:
            if not prev_in:
                out.append(_intersect_with_y(prev, curr, y_min))
            out.append(curr)
        elif prev_in:
            out.append(_intersect_with_y(prev, curr, y_min))
        prev = curr
        prev_in = curr_in
    return _clean_polygon(out)


def _clip_top(polygon: Polygon2D, y_max: float) -> Polygon2D:
    if not polygon:
        return ()

    out: list[Point2D] = []
    prev = polygon[-1]
    prev_in = prev[1] <= y_max
    for curr in polygon:
        curr_in = curr[1] <= y_max
        if curr_in:
            if not prev_in:
                out.append(_intersect_with_y(prev, curr, y_max))
            out.append(curr)
        elif prev_in:
            out.append(_intersect_with_y(prev, curr, y_max))
        prev = curr
        prev_in = curr_in
    return _clean_polygon(out)


def clip_polygon_with_cell(polygon: Polygon2D, cell: CartesianCell2D) -> Polygon2D:
    """Clip one polygon by one Cartesian cell rectangle."""

    clipped = _clip_left(polygon, cell.x0)
    clipped = _clip_right(clipped, cell.x1)
    clipped = _clip_bottom(clipped, cell.y0)
    clipped = _clip_top(clipped, cell.y1)
    return clipped


def build_cartesian_grid(
    *,
    resolution: int,
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
) -> tuple[CartesianCell2D, ...]:
    """Build a Cartesian grid matching the Section 6 element protocol."""

    if resolution < 1:
        raise ValueError("resolution must be positive")

    xmin, ymin, xmax, ymax = bounds
    hx = (xmax - xmin) / resolution
    hy = (ymax - ymin) / resolution
    cells: list[CartesianCell2D] = []
    for iy in range(resolution):
        y0 = ymin + iy * hy
        y1 = y0 + hy
        for ix in range(resolution):
            x0 = xmin + ix * hx
            x1 = x0 + hx
            cells.append(CartesianCell2D(ix=ix, iy=iy, x0=x0, x1=x1, y0=y0, y1=y1))
    return tuple(cells)


@lru_cache(maxsize=64)
def _cached_clipped_cells(
    panel_polygon: Polygon2D,
    resolution: int,
    bounds: tuple[float, float, float, float],
) -> tuple[CellClipResult, ...]:
    cells = build_cartesian_grid(resolution=resolution, bounds=bounds)
    area_tol = 1.0e-13

    clipped_results: list[CellClipResult] = []
    for cell in cells:
        polygon = clip_polygon_with_cell(panel_polygon, cell)
        area = abs(_signed_area(polygon))
        if area <= area_tol:
            clipped_results.append(
                CellClipResult(cell=cell, kind="outside", polygon=(), area=0.0)
            )
            continue

        if abs(area - cell.area) <= area_tol:
            rect_polygon: Polygon2D = (
                (cell.x0, cell.y0),
                (cell.x1, cell.y0),
                (cell.x1, cell.y1),
                (cell.x0, cell.y1),
            )
            clipped_results.append(
                CellClipResult(
                    cell=cell, kind="inside", polygon=rect_polygon, area=cell.area
                )
            )
            continue

        clipped_results.append(
            CellClipResult(cell=cell, kind="trimmed", polygon=polygon, area=area)
        )

    return tuple(clipped_results)


def _panel_polygon(panel: TrimmedPanel2D) -> Polygon2D:
    if panel.holes:
        raise NotImplementedError(
            "Section 6 2D protocol helper currently supports panels without holes"
        )
    return panel.outer.points


def _panel_from_polygon(polygon: Polygon2D) -> TrimmedPanel2D:
    return TrimmedPanel2D(outer=PanelLoop2D(polygon))


def _seed_grid_for_cell(
    cell: CartesianCell2D, *, grid_size: int
) -> tuple[Point2D, ...]:
    if grid_size < 2:
        raise ValueError("seed grid size must be at least 2")

    seeds: list[Point2D] = []
    for i in range(grid_size):
        x = cell.x0 + i * cell.width / (grid_size - 1)
        for j in range(grid_size):
            y = cell.y0 + j * cell.height / (grid_size - 1)
            seeds.append((x, y))
    return tuple(seeds)


def _resolve_panel_bounds(
    panel: TrimmedPanel2D,
    bounds: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float]:
    panel_bounds = panel.bbox()
    if bounds is None:
        return panel_bounds

    xmin, ymin, xmax, ymax = bounds
    pxmin, pymin, pxmax, pymax = panel_bounds
    tol = 1.0e-12
    if (
        pxmin < xmin - tol
        or pymin < ymin - tol
        or pxmax > xmax + tol
        or pymax > ymax + tol
    ):
        raise ValueError("panel bounding box must be contained in bounds")
    return bounds


def _h_values_from_bounds(
    grid_resolutions: tuple[int, ...],
    bounds: tuple[float, float, float, float],
) -> tuple[float, ...]:
    xmin, ymin, xmax, ymax = bounds
    span = max(xmax - xmin, ymax - ymin)
    return tuple(span / resolution for resolution in grid_resolutions)


def _section_bounds_for_label(label: str) -> tuple[float, float, float, float]:
    if label in {"6.1.1", "6.1.2"}:
        return (0.0, 0.0, 1.0, 1.0)
    raise ValueError(f"unsupported Section 6 label for CAD path: {label!r}")


def _resolve_cad_bounds(
    label: str,
    bounds: tuple[float, float, float, float] | None,
) -> tuple[float, float, float, float]:
    section_bounds = _section_bounds_for_label(label)
    if bounds is None:
        return section_bounds

    xmin, ymin, xmax, ymax = bounds
    sxmin, symin, sxmax, symax = section_bounds
    tol = 1.0e-12
    if (
        sxmin < xmin - tol
        or symin < ymin - tol
        or sxmax > xmax + tol
        or symax > ymax + tol
    ):
        raise ValueError("bounds must contain the full Section 6 CAD geometry")
    return bounds


@lru_cache(maxsize=65536)
def _cached_rule(
    polygon: Polygon2D,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> tuple[tuple[Point2D, ...], tuple[float, ...]]:
    panel = _panel_from_polygon(polygon)
    folded = folded_quadrature_rule(
        panel,
        order=order,
        anchor=anchor,
        require_interior_anchor=require_interior_anchor,
    )
    return folded.rule.points, folded.rule.weights


@lru_cache(maxsize=65536)
def _cached_rule_arrays(
    polygon: Polygon2D,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> tuple[Any, Any]:
    """Return cached rule as NumPy arrays when NumPy is available."""

    assert _np is not None
    points, weights = _cached_rule(polygon, order, anchor, require_interior_anchor)
    return _np.asarray(points, dtype=float), _np.asarray(weights, dtype=float)


@lru_cache(maxsize=64)
def _cached_gauss_arrays(order: int) -> tuple[Any, Any]:
    """Return Gauss nodes/weights as NumPy arrays when NumPy is available."""

    assert _np is not None
    nodes, quad_weights = gauss_legendre_01(order)
    return _np.asarray(nodes, dtype=float), _np.asarray(quad_weights, dtype=float)


def _bernstein_all(p: int, t: float) -> tuple[float, ...]:
    """Return all Bernstein basis values ``B_i^p(t)`` for ``i=0..p``."""

    if t <= 0.0:
        out = [0.0] * (p + 1)
        out[0] = 1.0
        return tuple(out)

    if t >= 1.0:
        out = [0.0] * (p + 1)
        out[p] = 1.0
        return tuple(out)

    one_minus_t = 1.0 - t
    ratio = t / one_minus_t

    out = [0.0] * (p + 1)
    value = one_minus_t**p
    out[0] = value
    for i in range(p):
        value *= ratio * (p - i) / (i + 1)
        out[i + 1] = value
    return tuple(out)


def _bernstein_matrix_numpy(p: int, t_values: Any) -> Any:
    """Return Bernstein values for all samples (NumPy acceleration path)."""

    assert _np is not None

    t = _np.asarray(t_values, dtype=float)
    out = _np.zeros((t.size, p + 1), dtype=float)

    mask_low = t <= 0.0
    mask_high = t >= 1.0
    mask_mid = ~(mask_low | mask_high)

    out[mask_low, 0] = 1.0
    out[mask_high, p] = 1.0

    if _np.any(mask_mid):
        tm = t[mask_mid]
        one_minus_t = 1.0 - tm
        ratio = tm / one_minus_t
        values = one_minus_t**p

        out_mid = out[mask_mid]
        out_mid[:, 0] = values
        for i in range(p):
            values = values * ratio * (p - i) / (i + 1)
            out_mid[:, i + 1] = values
        out[mask_mid] = out_mid

    return out


def _max_abs(values: tuple[float, ...]) -> float:
    if not values:
        return 0.0
    return max(abs(value) for value in values)


def _max_abs_diff(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


def _integrate_local_bernstein_over_rule(
    points: tuple[Point2D, ...] | Any,
    weights: tuple[float, ...] | Any,
    *,
    degree: int,
    cell: CartesianCell2D,
) -> tuple[float, ...]:
    count = degree + 1

    if _np is not None:
        points_arr = cast(Any, points)
        weights_arr = cast(Any, weights)
        if not (hasattr(points_arr, "shape") and hasattr(weights_arr, "shape")):
            points_arr = _np.asarray(points, dtype=float)
            weights_arr = _np.asarray(weights, dtype=float)

        x0 = cell.x0
        y0 = cell.y0
        width = cell.width
        height = cell.height

        u = _np.clip((points_arr[:, 0] - x0) / width, 0.0, 1.0)
        v = _np.clip((points_arr[:, 1] - y0) / height, 0.0, 1.0)

        bx = _bernstein_matrix_numpy(degree, u)
        by = _bernstein_matrix_numpy(degree, v)
        values = (bx * weights_arr[:, None]).T @ by
        return tuple(values.reshape(count * count).tolist())

    values = [0.0] * (count * count)

    x0 = cell.x0
    y0 = cell.y0
    width = cell.width
    height = cell.height

    for (x, y), weight in zip(points, weights):
        u = (x - x0) / width
        v = (y - y0) / height
        if u < 0.0:
            u = 0.0
        elif u > 1.0:
            u = 1.0
        if v < 0.0:
            v = 0.0
        elif v > 1.0:
            v = 1.0

        bx = _bernstein_all(degree, u)
        by = _bernstein_all(degree, v)
        for i in range(count):
            base = i * count
            bxi_w = bx[i] * weight
            for j in range(count):
                values[base + j] += bxi_w * by[j]

    return tuple(values)


def _integrate_bernstein_trimmed_cell(
    polygon: Polygon2D,
    *,
    cell: CartesianCell2D,
    degree: int,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> tuple[float, ...]:
    if _np is not None:
        points, weights = _cached_rule_arrays(
            polygon, order, anchor, require_interior_anchor
        )
    else:
        points, weights = _cached_rule(polygon, order, anchor, require_interior_anchor)

    return _integrate_local_bernstein_over_rule(
        points, weights, degree=degree, cell=cell
    )


def _integrate_function_rectangle(
    func: Callable[[float, float], float],
    *,
    cell: CartesianCell2D,
    order: int,
) -> float:
    if _np is not None:
        nodes_arr, weights_arr = _cached_gauss_arrays(order)
        xs = cell.x0 + nodes_arr * cell.width
        ys = cell.y0 + nodes_arr * cell.height
        xx, yy = _np.meshgrid(xs, ys, indexing="ij")
        w2 = _np.outer(weights_arr, weights_arr) * cell.area
        try:
            values = func(xx, yy)
            return float(_np.sum(values * w2))
        except Exception:
            pass

    nodes, quad_weights = gauss_legendre_01(order)

    total = 0.0
    for ux, wx in zip(nodes, quad_weights):
        x = cell.x0 + ux * cell.width
        for uy, wy in zip(nodes, quad_weights):
            y = cell.y0 + uy * cell.height
            total += func(x, y) * wx * wy * cell.area
    return total


def _integrate_function_trimmed_cell(
    func: Callable[[float, float], float],
    polygon: Polygon2D,
    *,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> float:
    if _np is not None:
        points_arr, weights_arr = _cached_rule_arrays(
            polygon, order, anchor, require_interior_anchor
        )
    else:
        points_arr, weights_arr = _cached_rule(
            polygon, order, anchor, require_interior_anchor
        )

    if _np is not None:
        np_points: Any = cast(Any, points_arr)
        np_weights: Any = cast(Any, weights_arr)
        try:
            values = func(np_points[:, 0], np_points[:, 1])
            return float(_np.dot(values, np_weights))
        except Exception:
            pass

    total = 0.0
    for (x, y), weight in zip(points_arr, weights_arr):
        total += func(x, y) * weight
    return total


@dataclass(frozen=True)
class PolynomialDegreeResult:
    """Section 6.1 error curves for one Bernstein degree."""

    degree: int
    orders: tuple[int, ...]
    trimmed_cell_count: int
    folded_abs_error: tuple[float, ...]
    jplus_abs_error: tuple[float, ...]
    folded_rel_error: tuple[float, ...]
    jplus_rel_error: tuple[float, ...]
    folded_reference_scale: float
    jplus_reference_scale: float


@dataclass(frozen=True)
class PolynomialExperimentResult:
    """Section 6.1 polynomial-integration reproduction output."""

    label: str
    grid_resolution: int
    reference_order: int
    seed_grid_size: int
    degree_results: tuple[PolynomialDegreeResult, ...]


def run_polynomial_experiment(
    panel: TrimmedPanel2D,
    *,
    label: str,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    grid_resolution: int = 8,
    reference_order: int = 64,
    seed_grid_size: int = 11,
    bounds: tuple[float, float, float, float] | None = None,
) -> PolynomialExperimentResult:
    """Run Section 6.1 style elementwise Bernstein tests.

    Error follows Eq. (18):

        Err = max_{K in G, K cap Gamma != empty} max_i |I^h_{K,i} - I^ref_{K,i}|.

    The folded path follows the Antolin-Wei-Buffa 2022 seed-vertex sweep in
    Section 6.1:
    for each trimmed cell, a uniform ``seed_grid_size x seed_grid_size`` seed set
    is evaluated and the worst error is retained.
    """

    panel_polygon = _panel_polygon(panel)
    effective_bounds = _resolve_panel_bounds(panel, bounds)
    clipped = _cached_clipped_cells(panel_polygon, grid_resolution, effective_bounds)
    trimmed = tuple(result for result in clipped if result.kind == "trimmed")

    if not trimmed:
        raise ValueError("no trimmed cells were found for the requested grid")

    degree_results: list[PolynomialDegreeResult] = []

    for degree in degrees:
        jplus_refs: dict[int, tuple[float, ...]] = {}
        cell_seeds: dict[int, tuple[Point2D, ...]] = {}

        jplus_scale = 0.0

        for cell_idx, clip in enumerate(trimmed):
            jref = _integrate_bernstein_trimmed_cell(
                clip.polygon,
                cell=clip.cell,
                degree=degree,
                order=reference_order,
                anchor=None,
                require_interior_anchor=True,
            )
            jplus_refs[cell_idx] = jref
            jplus_scale = max(jplus_scale, _max_abs(jref))

            seeds = _seed_grid_for_cell(clip.cell, grid_size=seed_grid_size)
            cell_seeds[cell_idx] = seeds

        jplus_abs_curve: list[float] = []
        folded_abs_curve: list[float] = []

        for order in orders:
            jplus_err = 0.0
            folded_err = 0.0

            for cell_idx, clip in enumerate(trimmed):
                japprox = _integrate_bernstein_trimmed_cell(
                    clip.polygon,
                    cell=clip.cell,
                    degree=degree,
                    order=order,
                    anchor=None,
                    require_interior_anchor=True,
                )
                jerr_cell = _max_abs_diff(japprox, jplus_refs[cell_idx])
                if jerr_cell > jplus_err:
                    jplus_err = jerr_cell

                worst_cell = 0.0
                seeds = cell_seeds[cell_idx]
                for seed in seeds:
                    fapprox = _integrate_bernstein_trimmed_cell(
                        clip.polygon,
                        cell=clip.cell,
                        degree=degree,
                        order=order,
                        anchor=seed,
                        require_interior_anchor=False,
                    )
                    ferr = _max_abs_diff(fapprox, jplus_refs[cell_idx])
                    if ferr > worst_cell:
                        worst_cell = ferr

                if worst_cell > folded_err:
                    folded_err = worst_cell

            jplus_abs_curve.append(jplus_err)
            folded_abs_curve.append(folded_err)

        j_scale = max(jplus_scale, 1.0e-30)
        f_scale = j_scale
        jplus_rel_curve = tuple(value / j_scale for value in jplus_abs_curve)
        folded_rel_curve = tuple(value / f_scale for value in folded_abs_curve)

        degree_results.append(
            PolynomialDegreeResult(
                degree=degree,
                orders=orders,
                trimmed_cell_count=len(trimmed),
                folded_abs_error=tuple(folded_abs_curve),
                jplus_abs_error=tuple(jplus_abs_curve),
                folded_rel_error=folded_rel_curve,
                jplus_rel_error=jplus_rel_curve,
                folded_reference_scale=f_scale,
                jplus_reference_scale=j_scale,
            )
        )

    return PolynomialExperimentResult(
        label=label,
        grid_resolution=grid_resolution,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
        degree_results=tuple(degree_results),
    )


def section_6_2_integrand(x: float, y: float) -> float:
    """2D non-polynomial integrand used in Section 6.2."""

    if _np is not None:
        return _np.exp(y) * _np.sin(x) * _np.cos(y)
    return exp(y) * sin(x) * cos(y)


def _integrate_general_over_grid(
    panel: TrimmedPanel2D,
    *,
    func: Callable[[float, float], float],
    grid_resolution: int,
    order: int,
    mode: Literal["jplus", "folded"],
    folded_anchor_mode: Literal["cell-origin", "cell-center"] = "cell-origin",
    bounds: tuple[float, float, float, float] = (0.0, 0.0, 1.0, 1.0),
) -> float:
    panel_polygon = _panel_polygon(panel)
    clipped = _cached_clipped_cells(panel_polygon, grid_resolution, bounds)

    total = 0.0
    for clip in clipped:
        if clip.kind == "outside":
            continue

        if clip.kind == "inside":
            total += _integrate_function_rectangle(func, cell=clip.cell, order=order)
            continue

        if mode == "jplus":
            total += _integrate_function_trimmed_cell(
                func,
                clip.polygon,
                order=order,
                anchor=None,
                require_interior_anchor=True,
            )
            continue

        if folded_anchor_mode == "cell-origin":
            anchor = (clip.cell.x0, clip.cell.y0)
        else:
            anchor = (
                (clip.cell.x0 + clip.cell.x1) * 0.5,
                (clip.cell.y0 + clip.cell.y1) * 0.5,
            )

        total += _integrate_function_trimmed_cell(
            func,
            clip.polygon,
            order=order,
            anchor=anchor,
            require_interior_anchor=False,
        )

    return total


@dataclass(frozen=True)
class GeneralFunctionOrderResult:
    """Section 6.2 convergence data for one quadrature order ``n``."""

    order: int
    grid_resolutions: tuple[int, ...]
    h_values: tuple[float, ...]
    folded_abs_error: tuple[float, ...]
    jplus_abs_error: tuple[float, ...]
    folded_rel_error: tuple[float, ...]
    jplus_rel_error: tuple[float, ...]


@dataclass(frozen=True)
class GeneralFunctionResult:
    """Section 6.2 elementwise convergence reproduction output."""

    reference_value: float
    reference_grid_resolution: int
    reference_order: int
    order_results: tuple[GeneralFunctionOrderResult, ...]


def run_general_function_experiment(
    panel: TrimmedPanel2D,
    *,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...] = (2, 4, 8, 16, 32, 64, 128),
    reference_grid_resolution: int = 128,
    reference_order: int = 64,
    folded_anchor_mode: Literal["cell-origin", "cell-center"] = "cell-origin",
    bounds: tuple[float, float, float, float] | None = None,
) -> GeneralFunctionResult:
    """Run Section 6.2 style elementwise integration and convergence sweeps.

    A dense-grid, high-order result is used as reference. For each ``n`` in
    ``orders``, this returns errors over ``grid_resolutions`` with
    ``h = 1 / resolution``.
    """

    effective_bounds = _resolve_panel_bounds(panel, bounds)

    reference = _integrate_general_over_grid(
        panel,
        func=section_6_2_integrand,
        grid_resolution=reference_grid_resolution,
        order=reference_order,
        mode="jplus",
        folded_anchor_mode=folded_anchor_mode,
        bounds=effective_bounds,
    )
    reference_scale = max(abs(reference), 1.0e-30)

    order_results: list[GeneralFunctionOrderResult] = []
    h_values = _h_values_from_bounds(grid_resolutions, effective_bounds)

    for order in orders:
        folded_abs: list[float] = []
        jplus_abs: list[float] = []

        for resolution in grid_resolutions:
            folded_value = _integrate_general_over_grid(
                panel,
                func=section_6_2_integrand,
                grid_resolution=resolution,
                order=order,
                mode="folded",
                folded_anchor_mode=folded_anchor_mode,
                bounds=effective_bounds,
            )
            jplus_value = _integrate_general_over_grid(
                panel,
                func=section_6_2_integrand,
                grid_resolution=resolution,
                order=order,
                mode="jplus",
                folded_anchor_mode=folded_anchor_mode,
                bounds=effective_bounds,
            )

            folded_abs.append(abs(folded_value - reference))
            jplus_abs.append(abs(jplus_value - reference))

        order_results.append(
            GeneralFunctionOrderResult(
                order=order,
                grid_resolutions=grid_resolutions,
                h_values=h_values,
                folded_abs_error=tuple(folded_abs),
                jplus_abs_error=tuple(jplus_abs),
                folded_rel_error=tuple(value / reference_scale for value in folded_abs),
                jplus_rel_error=tuple(value / reference_scale for value in jplus_abs),
            )
        )

    return GeneralFunctionResult(
        reference_value=reference,
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
        order_results=tuple(order_results),
    )


@dataclass(frozen=True)
class CadCellClipResult:
    """Cell clipping result from OpenCascade exact CAD boolean operations."""

    cell: CartesianCell2D
    kind: Literal["outside", "inside", "trimmed"]
    panels: tuple[CurveTrimmedPanel2D, ...]
    area: float


def _section_face_for_label(label: str) -> Any:
    if label == "6.1.1":
        return build_section_6_1_1_face()
    if label == "6.1.2":
        return build_section_6_1_2_face()
    raise ValueError(f"unsupported Section 6 label for CAD path: {label!r}")


def _integrate_curve_panels_constant(
    panels: tuple[CurveTrimmedPanel2D, ...],
    *,
    order: int,
) -> float:
    total = 0.0
    for panel in panels:
        outer = abs(curve_loop_signed_area(panel.outer, order=order))
        holes = sum(
            abs(curve_loop_signed_area(hole, order=order)) for hole in panel.holes
        )
        total += outer - holes
    return total


@lru_cache(maxsize=64)
def _cached_cad_clipped_cells(
    label: str,
    resolution: int,
    bounds: tuple[float, float, float, float],
) -> tuple[CadCellClipResult, ...]:
    try:
        face = _section_face_for_label(label)
    except OpenCascadeUnavailableError as exc:
        raise RuntimeError(
            "OpenCascade backend is unavailable; install with `uv sync --extra cad` "
            "and ensure system OpenGL libraries are present"
        ) from exc

    area_tol = 1.0e-11
    clipped_results: list[CadCellClipResult] = []
    for cell in build_cartesian_grid(resolution=resolution, bounds=bounds):
        panels = intersect_face_with_rectangle(
            face,
            x0=cell.x0,
            x1=cell.x1,
            y0=cell.y0,
            y1=cell.y1,
        )
        if not panels:
            clipped_results.append(
                CadCellClipResult(cell=cell, kind="outside", panels=(), area=0.0)
            )
            continue

        area = _integrate_curve_panels_constant(panels, order=8)
        if abs(area - cell.area) <= area_tol:
            clipped_results.append(
                CadCellClipResult(cell=cell, kind="inside", panels=panels, area=area)
            )
        else:
            clipped_results.append(
                CadCellClipResult(cell=cell, kind="trimmed", panels=panels, area=area)
            )

    return tuple(clipped_results)


def _integrate_bernstein_trimmed_cell_cad(
    panels: tuple[CurveTrimmedPanel2D, ...],
    *,
    cell: CartesianCell2D,
    degree: int,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> tuple[float, ...]:
    count = degree + 1
    total = [0.0] * (count * count)

    for panel in panels:
        try:
            folded = folded_curve_quadrature_rule(
                panel,
                order=order,
                anchor=anchor,
                require_interior_anchor=require_interior_anchor,
                anchor_sample_points=CAD_ANCHOR_SAMPLE_POINTS,
            )
        except ValueError as exc:
            if require_interior_anchor and anchor is None:
                raise RuntimeError(
                    "failed to select interior anchor for CAD trimmed cell "
                    f"({cell.ix}, {cell.iy}) in jplus mode"
                ) from exc
            raise
        values = _integrate_local_bernstein_over_rule(
            folded.rule.points,
            folded.rule.weights,
            degree=degree,
            cell=cell,
        )
        for idx, value in enumerate(values):
            total[idx] += value

    return tuple(total)


def _integrate_function_trimmed_cell_cad(
    func: Callable[[float, float], float],
    panels: tuple[CurveTrimmedPanel2D, ...],
    *,
    cell: CartesianCell2D | None,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> float:
    total = 0.0
    for panel in panels:
        try:
            folded = folded_curve_quadrature_rule(
                panel,
                order=order,
                anchor=anchor,
                require_interior_anchor=require_interior_anchor,
                anchor_sample_points=CAD_ANCHOR_SAMPLE_POINTS,
            )
        except ValueError as exc:
            if require_interior_anchor and anchor is None and cell is not None:
                raise RuntimeError(
                    "failed to select interior anchor for CAD trimmed cell "
                    f"({cell.ix}, {cell.iy}) in jplus mode"
                ) from exc
            raise

        if _np is not None:
            points_arr = _np.asarray(folded.rule.points, dtype=float)
            weights_arr = _np.asarray(folded.rule.weights, dtype=float)
            try:
                values = func(points_arr[:, 0], points_arr[:, 1])
                total += float(_np.dot(values, weights_arr))
                continue
            except Exception:
                pass

        for (x, y), weight in zip(folded.rule.points, folded.rule.weights):
            total += func(x, y) * weight

    return total


def run_polynomial_experiment_cad(
    *,
    label: str,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    grid_resolution: int = 8,
    reference_order: int = 64,
    seed_grid_size: int = 11,
    bounds: tuple[float, float, float, float] | None = None,
) -> PolynomialExperimentResult:
    """Run Section 6.1 polynomial protocol with exact CAD cell clipping."""

    effective_bounds = _resolve_cad_bounds(label, bounds)
    clipped = _cached_cad_clipped_cells(label, grid_resolution, effective_bounds)
    trimmed = tuple(result for result in clipped if result.kind == "trimmed")
    if not trimmed:
        raise ValueError("no trimmed cells were found for the requested CAD grid")

    degree_results: list[PolynomialDegreeResult] = []

    for degree in degrees:
        jplus_refs: dict[int, tuple[float, ...]] = {}
        cell_seeds: dict[int, tuple[Point2D, ...]] = {}

        jplus_scale = 0.0

        for cell_idx, clip in enumerate(trimmed):
            jref = _integrate_bernstein_trimmed_cell_cad(
                clip.panels,
                cell=clip.cell,
                degree=degree,
                order=reference_order,
                anchor=None,
                require_interior_anchor=True,
            )
            jplus_refs[cell_idx] = jref
            jplus_scale = max(jplus_scale, _max_abs(jref))

            seeds = _seed_grid_for_cell(clip.cell, grid_size=seed_grid_size)
            cell_seeds[cell_idx] = seeds

        jplus_abs_curve: list[float] = []
        folded_abs_curve: list[float] = []

        for order in orders:
            jplus_err = 0.0
            folded_err = 0.0

            for cell_idx, clip in enumerate(trimmed):
                japprox = _integrate_bernstein_trimmed_cell_cad(
                    clip.panels,
                    cell=clip.cell,
                    degree=degree,
                    order=order,
                    anchor=None,
                    require_interior_anchor=True,
                )
                jerr_cell = _max_abs_diff(japprox, jplus_refs[cell_idx])
                if jerr_cell > jplus_err:
                    jplus_err = jerr_cell

                worst_cell = 0.0
                seeds = cell_seeds[cell_idx]
                for seed in seeds:
                    fapprox = _integrate_bernstein_trimmed_cell_cad(
                        clip.panels,
                        cell=clip.cell,
                        degree=degree,
                        order=order,
                        anchor=seed,
                        require_interior_anchor=False,
                    )
                    ferr = _max_abs_diff(fapprox, jplus_refs[cell_idx])
                    if ferr > worst_cell:
                        worst_cell = ferr

                if worst_cell > folded_err:
                    folded_err = worst_cell

            jplus_abs_curve.append(jplus_err)
            folded_abs_curve.append(folded_err)

        j_scale = max(jplus_scale, 1.0e-30)
        f_scale = j_scale
        jplus_rel_curve = tuple(value / j_scale for value in jplus_abs_curve)
        folded_rel_curve = tuple(value / f_scale for value in folded_abs_curve)

        degree_results.append(
            PolynomialDegreeResult(
                degree=degree,
                orders=orders,
                trimmed_cell_count=len(trimmed),
                folded_abs_error=tuple(folded_abs_curve),
                jplus_abs_error=tuple(jplus_abs_curve),
                folded_rel_error=folded_rel_curve,
                jplus_rel_error=jplus_rel_curve,
                folded_reference_scale=f_scale,
                jplus_reference_scale=j_scale,
            )
        )

    return PolynomialExperimentResult(
        label=label,
        grid_resolution=grid_resolution,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
        degree_results=tuple(degree_results),
    )


def _integrate_general_over_grid_cad(
    *,
    label: str,
    func: Callable[[float, float], float],
    grid_resolution: int,
    order: int,
    mode: Literal["jplus", "folded"],
    folded_anchor_mode: Literal["cell-origin", "cell-center"] = "cell-origin",
    bounds: tuple[float, float, float, float] | None = None,
) -> float:
    effective_bounds = _resolve_cad_bounds(label, bounds)
    clipped = _cached_cad_clipped_cells(label, grid_resolution, effective_bounds)

    total = 0.0
    for clip in clipped:
        if clip.kind == "outside":
            continue

        if clip.kind == "inside":
            total += _integrate_function_rectangle(func, cell=clip.cell, order=order)
            continue

        if mode == "jplus":
            total += _integrate_function_trimmed_cell_cad(
                func,
                clip.panels,
                cell=clip.cell,
                order=order,
                anchor=None,
                require_interior_anchor=True,
            )
            continue

        if folded_anchor_mode == "cell-origin":
            anchor = (clip.cell.x0, clip.cell.y0)
        else:
            anchor = (
                (clip.cell.x0 + clip.cell.x1) * 0.5,
                (clip.cell.y0 + clip.cell.y1) * 0.5,
            )

        total += _integrate_function_trimmed_cell_cad(
            func,
            clip.panels,
            cell=clip.cell,
            order=order,
            anchor=anchor,
            require_interior_anchor=False,
        )

    return total


def run_general_function_experiment_cad(
    *,
    label: str,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...] = (2, 4, 8, 16, 32, 64, 128),
    reference_grid_resolution: int = 128,
    reference_order: int = 64,
    folded_anchor_mode: Literal["cell-origin", "cell-center"] = "cell-origin",
    bounds: tuple[float, float, float, float] | None = None,
) -> GeneralFunctionResult:
    """Run Section 6.2 protocol with exact CAD clipping + folded quadrature."""

    effective_bounds = _resolve_cad_bounds(label, bounds)

    reference = _integrate_general_over_grid_cad(
        label=label,
        func=section_6_2_integrand,
        grid_resolution=reference_grid_resolution,
        order=reference_order,
        mode="jplus",
        folded_anchor_mode=folded_anchor_mode,
        bounds=effective_bounds,
    )
    reference_scale = max(abs(reference), 1.0e-30)

    order_results: list[GeneralFunctionOrderResult] = []
    h_values = _h_values_from_bounds(grid_resolutions, effective_bounds)

    for order in orders:
        folded_abs: list[float] = []
        jplus_abs: list[float] = []

        for resolution in grid_resolutions:
            folded_value = _integrate_general_over_grid_cad(
                label=label,
                func=section_6_2_integrand,
                grid_resolution=resolution,
                order=order,
                mode="folded",
                folded_anchor_mode=folded_anchor_mode,
                bounds=effective_bounds,
            )
            jplus_value = _integrate_general_over_grid_cad(
                label=label,
                func=section_6_2_integrand,
                grid_resolution=resolution,
                order=order,
                mode="jplus",
                folded_anchor_mode=folded_anchor_mode,
                bounds=effective_bounds,
            )

            folded_abs.append(abs(folded_value - reference))
            jplus_abs.append(abs(jplus_value - reference))

        order_results.append(
            GeneralFunctionOrderResult(
                order=order,
                grid_resolutions=grid_resolutions,
                h_values=h_values,
                folded_abs_error=tuple(folded_abs),
                jplus_abs_error=tuple(jplus_abs),
                folded_rel_error=tuple(value / reference_scale for value in folded_abs),
                jplus_rel_error=tuple(value / reference_scale for value in jplus_abs),
            )
        )

    return GeneralFunctionResult(
        reference_value=reference,
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
        order_results=tuple(order_results),
    )
