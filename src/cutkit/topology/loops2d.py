"""Loop topology utilities for 2D trimmed panels."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from cutkit.geometry import PanelLoop2D, Point2D, TrimmedPanel2D


def _coerce_loop(loop: PanelLoop2D | Iterable[Point2D]) -> PanelLoop2D:
    if isinstance(loop, PanelLoop2D):
        return loop
    return PanelLoop2D(tuple(loop))


def _coerce_panel(panel: TrimmedPanel2D | object) -> TrimmedPanel2D:
    if isinstance(panel, TrimmedPanel2D):
        return panel
    raise TypeError("panel must be a TrimmedPanel2D")


def signed_area(loop: PanelLoop2D | Iterable[Point2D]) -> float:
    """Return signed area from the shoelace formula."""

    normalized = _coerce_loop(loop)
    points = normalized.points
    accum = 0.0
    for idx, (x0, y0) in enumerate(points):
        x1, y1 = points[(idx + 1) % len(points)]
        accum += x0 * y1 - x1 * y0
    return 0.5 * accum


def orientation(
    loop: PanelLoop2D | Iterable[Point2D], *, area_tol: float = 1.0e-14
) -> str:
    """Return ``ccw``, ``cw`` or ``degenerate`` for one loop."""

    area = signed_area(loop)
    if area > area_tol:
        return "ccw"
    if area < -area_tol:
        return "cw"
    return "degenerate"


def enforce_orientation(loop: PanelLoop2D, target: str) -> PanelLoop2D:
    """Return a copy of *loop* with target orientation."""

    current = orientation(loop)
    if current == "degenerate":
        raise ValueError("cannot orient a degenerate loop")
    if current == target:
        return loop
    if target not in {"ccw", "cw"}:
        raise ValueError(f"unknown target orientation: {target!r}")
    return PanelLoop2D(tuple(reversed(loop.points)))


def normalize_panel_orientations(panel: TrimmedPanel2D) -> TrimmedPanel2D:
    """Normalize panel loops to outer=ccw and holes=cw."""

    panel = _coerce_panel(panel)
    outer = enforce_orientation(panel.outer, "ccw")
    holes = tuple(enforce_orientation(hole, "cw") for hole in panel.holes)
    return TrimmedPanel2D(outer=outer, holes=holes)


def _point_on_segment(point: Point2D, a: Point2D, b: Point2D, tol: float) -> bool:
    px, py = point
    ax, ay = a
    bx, by = b

    abx = bx - ax
    aby = by - ay
    apx = px - ax
    apy = py - ay

    cross = abx * apy - aby * apx
    if abs(cross) > tol:
        return False

    dot = apx * abx + apy * aby
    if dot < -tol:
        return False

    sq_len = abx * abx + aby * aby
    if dot - sq_len > tol:
        return False

    return True


def point_in_loop(
    point: Point2D,
    loop: PanelLoop2D | Iterable[Point2D],
    *,
    include_boundary: bool = True,
    tol: float = 1.0e-12,
) -> bool:
    """Return whether *point* lies in a polygon loop."""

    normalized = _coerce_loop(loop)
    points = normalized.points
    px, py = point

    inside = False
    for idx, a in enumerate(points):
        b = points[(idx + 1) % len(points)]

        if _point_on_segment(point, a, b, tol):
            return include_boundary

        ax, ay = a
        bx, by = b

        intersects = (ay > py) != (by > py)
        if not intersects:
            continue

        x_intersection = ax + (py - ay) * (bx - ax) / (by - ay)
        if x_intersection > px:
            inside = not inside

    return inside


def point_in_panel(
    point: Point2D,
    panel: TrimmedPanel2D,
    *,
    include_boundary: bool = True,
    tol: float = 1.0e-12,
) -> bool:
    """Return whether *point* lies inside the trimmed panel."""

    panel = _coerce_panel(panel)

    if _point_on_loop_boundary(point, panel.outer, tol=tol):
        return include_boundary

    if not point_in_loop(point, panel.outer, include_boundary=False, tol=tol):
        return False

    for hole in panel.holes:
        if _point_on_loop_boundary(point, hole, tol=tol):
            return include_boundary
        if point_in_loop(point, hole, include_boundary=False, tol=tol):
            return False

    return True


def _point_on_loop_boundary(
    point: Point2D,
    loop: PanelLoop2D | Iterable[Point2D],
    *,
    tol: float = 1.0e-12,
) -> bool:
    normalized = _coerce_loop(loop)
    for a, b in normalized.edges():
        if _point_on_segment(point, a, b, tol):
            return True
    return False


def polygon_centroid(
    loop: PanelLoop2D | Iterable[Point2D], *, area_tol: float = 1.0e-14
) -> Point2D:
    """Return polygon centroid for a non-degenerate loop."""

    normalized = _coerce_loop(loop)
    points = normalized.points
    area2 = 0.0
    cx_accum = 0.0
    cy_accum = 0.0
    for idx, (x0, y0) in enumerate(points):
        x1, y1 = points[(idx + 1) % len(points)]
        cross = x0 * y1 - x1 * y0
        area2 += cross
        cx_accum += (x0 + x1) * cross
        cy_accum += (y0 + y1) * cross

    if abs(area2) <= area_tol:
        x_mean = sum(point[0] for point in points) / len(points)
        y_mean = sum(point[1] for point in points) / len(points)
        return (x_mean, y_mean)

    scale = 1.0 / (3.0 * area2)
    return (cx_accum * scale, cy_accum * scale)


def select_interior_anchor(
    panel: TrimmedPanel2D,
    *,
    grid_size: int = 17,
    tol: float = 1.0e-12,
) -> Point2D:
    """Select a deterministic interior anchor for folded decomposition."""

    panel = normalize_panel_orientations(_coerce_panel(panel))

    outer_points = panel.outer.points
    bbox = panel.bbox()
    xmin, ymin, xmax, ymax = bbox

    candidates: list[Point2D] = [
        polygon_centroid(panel.outer),
        ((xmin + xmax) * 0.5, (ymin + ymax) * 0.5),
        (
            sum(point[0] for point in outer_points) / len(outer_points),
            sum(point[1] for point in outer_points) / len(outer_points),
        ),
    ]

    for candidate in candidates:
        if point_in_panel(candidate, panel, include_boundary=False, tol=tol):
            return candidate

    center = ((xmin + xmax) * 0.5, (ymin + ymax) * 0.5)
    for factor in (
        1.0 / 16.0,
        1.0 / 32.0,
        1.0 / 64.0,
        1.0 / 128.0,
        1.0 / 256.0,
        1.0 / 512.0,
        1.0 / 1024.0,
        1.0 / 2048.0,
        1.0 / 4096.0,
    ):
        for vx, vy in outer_points:
            candidate = (vx + factor * (center[0] - vx), vy + factor * (center[1] - vy))
            if point_in_panel(candidate, panel, include_boundary=False, tol=tol):
                return candidate

    if grid_size < 2:
        grid_size = 2

    x_span = xmax - xmin
    y_span = ymax - ymin
    for refinement in (1, 2, 4, 8, 16, 32):
        current_grid_size = max(2, grid_size * refinement)
        for ix in range(current_grid_size):
            for iy in range(current_grid_size):
                candidate = (
                    xmin + (ix + 0.5) * x_span / current_grid_size,
                    ymin + (iy + 0.5) * y_span / current_grid_size,
                )
                if point_in_panel(candidate, panel, include_boundary=False, tol=tol):
                    return candidate

    raise ValueError("unable to find interior anchor for panel")


@dataclass(frozen=True)
class LoopValidationDiagnostics:
    """Structured diagnostics for one loop in panel validation."""

    orientation: str
    signed_area: float
    area_abs: float
    self_intersects: bool


@dataclass(frozen=True)
class PanelValidationDiagnostics:
    """Structured diagnostics for panel-level topology validation."""

    outer: LoopValidationDiagnostics
    holes: tuple[LoopValidationDiagnostics, ...]
    holes_strictly_inside_outer: tuple[bool, ...]
    holes_intersect_outer_boundary: tuple[bool, ...]
    overlapping_hole_pairs: tuple[tuple[int, int], ...]
    panel_area: float


@dataclass(frozen=True)
class PanelValidationResult:
    """Validation result for panel loop orientation and positivity checks."""

    panel: TrimmedPanel2D
    errors: tuple[str, ...]
    diagnostics: PanelValidationDiagnostics


def validate_panel(
    panel: TrimmedPanel2D, *, area_tol: float = 1.0e-14
) -> PanelValidationResult:
    """Validate orientation and positive area invariants for a panel."""

    panel = _coerce_panel(panel)
    errors: list[str] = []

    outer_signed_area = signed_area(panel.outer)
    outer_area_abs = abs(outer_signed_area)
    outer_orientation = orientation(panel.outer, area_tol=area_tol)
    outer_self_intersects = _loop_self_intersects(panel.outer)
    outer_diagnostics = LoopValidationDiagnostics(
        orientation=outer_orientation,
        signed_area=outer_signed_area,
        area_abs=outer_area_abs,
        self_intersects=outer_self_intersects,
    )

    if outer_orientation == "degenerate":
        errors.append("outer loop must be non-degenerate")
    elif outer_orientation != "ccw":
        errors.append("outer loop orientation must be ccw")

    if outer_self_intersects:
        errors.append("outer loop must be simple (non-self-intersecting)")

    if outer_area_abs <= area_tol:
        errors.append("outer loop area must be positive")

    holes = panel.holes
    hole_diagnostics: list[LoopValidationDiagnostics] = []
    holes_strictly_inside_outer: list[bool] = []
    holes_intersect_outer_boundary: list[bool] = []
    hole_area_sum = 0.0
    for idx, hole in enumerate(holes):
        hole_signed_area = signed_area(hole)
        hole_area_abs = abs(hole_signed_area)
        hole_orientation = orientation(hole, area_tol=area_tol)
        hole_self_intersects = _loop_self_intersects(hole)
        hole_inside_outer = _loop_strictly_inside_outer(hole, panel.outer)
        hole_intersects_outer = _loops_edge_intersect(hole, panel.outer)

        hole_diagnostics.append(
            LoopValidationDiagnostics(
                orientation=hole_orientation,
                signed_area=hole_signed_area,
                area_abs=hole_area_abs,
                self_intersects=hole_self_intersects,
            )
        )
        holes_strictly_inside_outer.append(hole_inside_outer)
        holes_intersect_outer_boundary.append(hole_intersects_outer)

        if hole_orientation == "degenerate":
            errors.append(f"hole {idx} must be non-degenerate")
        elif hole_orientation != "cw":
            errors.append(f"hole {idx} orientation must be cw")

        if hole_area_abs <= area_tol:
            errors.append(f"hole {idx} area magnitude must be positive")

        if hole_self_intersects:
            errors.append(f"hole {idx} must be simple (non-self-intersecting)")

        if not hole_inside_outer:
            errors.append(f"hole {idx} must lie strictly inside outer loop")

        if hole_intersects_outer:
            errors.append(f"hole {idx} intersects outer loop boundary")

        hole_area_sum += hole_area_abs

    overlapping_hole_pairs: list[tuple[int, int]] = []
    for i in range(len(holes)):
        for j in range(i + 1, len(holes)):
            if _loops_overlap_or_touch(holes[i], holes[j]):
                overlapping_hole_pairs.append((i, j))
                errors.append(f"holes {i} and {j} overlap or touch")

    panel_area = outer_area_abs - hole_area_sum
    if panel_area <= area_tol:
        errors.append("trimmed panel area must be positive")

    diagnostics = PanelValidationDiagnostics(
        outer=outer_diagnostics,
        holes=tuple(hole_diagnostics),
        holes_strictly_inside_outer=tuple(holes_strictly_inside_outer),
        holes_intersect_outer_boundary=tuple(holes_intersect_outer_boundary),
        overlapping_hole_pairs=tuple(overlapping_hole_pairs),
        panel_area=panel_area,
    )

    return PanelValidationResult(
        panel=panel, errors=tuple(errors), diagnostics=diagnostics
    )


def _loop_strictly_inside_outer(hole: PanelLoop2D, outer: PanelLoop2D) -> bool:
    for point in hole.points:
        if not point_in_loop(point, outer, include_boundary=False):
            return False
    return True


def _segment_cross(a: Point2D, b: Point2D, c: Point2D) -> float:
    return (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])


def _segments_intersect(
    a: Point2D,
    b: Point2D,
    c: Point2D,
    d: Point2D,
    *,
    tol: float = 1.0e-12,
) -> bool:
    o1 = _segment_cross(a, b, c)
    o2 = _segment_cross(a, b, d)
    o3 = _segment_cross(c, d, a)
    o4 = _segment_cross(c, d, b)

    if _point_on_segment(c, a, b, tol):
        return True
    if _point_on_segment(d, a, b, tol):
        return True
    if _point_on_segment(a, c, d, tol):
        return True
    if _point_on_segment(b, c, d, tol):
        return True

    return (o1 > 0.0) != (o2 > 0.0) and (o3 > 0.0) != (o4 > 0.0)


def _loops_edge_intersect(loop_a: PanelLoop2D, loop_b: PanelLoop2D) -> bool:
    for a0, a1 in loop_a.edges():
        for b0, b1 in loop_b.edges():
            if _segments_intersect(a0, a1, b0, b1):
                return True
    return False


def _loops_overlap_or_touch(loop_a: PanelLoop2D, loop_b: PanelLoop2D) -> bool:
    for point in loop_a.points:
        if point_in_loop(point, loop_b, include_boundary=True):
            return True
    for point in loop_b.points:
        if point_in_loop(point, loop_a, include_boundary=True):
            return True
    return _loops_edge_intersect(loop_a, loop_b)


def _loop_self_intersects(loop: PanelLoop2D, *, tol: float = 1.0e-12) -> bool:
    points = loop.points
    edge_count = len(points)
    if edge_count < 4:
        return False

    for i in range(edge_count):
        a0 = points[i]
        a1 = points[(i + 1) % edge_count]
        for j in range(i + 1, edge_count):
            if j == i:
                continue
            if j == (i + 1) % edge_count:
                continue
            if i == (j + 1) % edge_count:
                continue

            b0 = points[j]
            b1 = points[(j + 1) % edge_count]
            if _segments_intersect(a0, a1, b0, b1, tol=tol):
                return True

    for i in range(edge_count):
        for j in range(i + 1, edge_count):
            if j == i + 1:
                continue
            if i == 0 and j == edge_count - 1:
                continue
            if (
                abs(points[i][0] - points[j][0]) <= tol
                and abs(points[i][1] - points[j][1]) <= tol
            ):
                return True

    return False
