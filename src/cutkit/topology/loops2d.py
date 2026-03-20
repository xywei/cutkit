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
    if not point_in_loop(
        point, panel.outer, include_boundary=include_boundary, tol=tol
    ):
        return False

    for hole in panel.holes:
        if point_in_loop(point, hole, include_boundary=include_boundary, tol=tol):
            return False

    return True


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

    if grid_size < 2:
        grid_size = 2

    x_span = xmax - xmin
    y_span = ymax - ymin
    for ix in range(grid_size):
        for iy in range(grid_size):
            candidate = (
                xmin + (ix + 0.5) * x_span / grid_size,
                ymin + (iy + 0.5) * y_span / grid_size,
            )
            if point_in_panel(candidate, panel, include_boundary=False, tol=tol):
                return candidate

    raise ValueError("unable to find interior anchor for panel")


@dataclass(frozen=True)
class PanelValidationResult:
    """Validation result for panel loop orientation and positivity checks."""

    panel: TrimmedPanel2D
    errors: tuple[str, ...]


def validate_panel(
    panel: TrimmedPanel2D, *, area_tol: float = 1.0e-14
) -> PanelValidationResult:
    """Validate orientation and positive area invariants for a panel."""

    panel = normalize_panel_orientations(_coerce_panel(panel))
    errors: list[str] = []

    outer_area = signed_area(panel.outer)
    if outer_area <= area_tol:
        errors.append("outer loop area must be positive")

    hole_area_sum = 0.0
    for idx, hole in enumerate(panel.holes):
        hole_signed = signed_area(hole)
        if hole_signed >= -area_tol:
            errors.append(f"hole {idx} area must be negative")
        hole_area_sum += abs(hole_signed)

    panel_area = outer_area - hole_area_sum
    if panel_area <= area_tol:
        errors.append("trimmed panel area must be positive")

    return PanelValidationResult(panel=panel, errors=tuple(errors))
