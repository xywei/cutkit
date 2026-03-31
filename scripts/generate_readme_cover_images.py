#!/usr/bin/env python3
"""Generate README cover SVGs from real folded decomposition workflows."""

from __future__ import annotations

import argparse
import math
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import cutkit.evals.antolin_wei_buffa_2022_3d as awb3d
from cutkit.evals import (
    build_poisson_galerkin_geometry_snapshot,
    build_section_6_1_1_bspline_panel,
)
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.quadrature import folded_quadrature_rule, gauss_legendre_01

Point2D = tuple[float, float]
Point3D = tuple[float, float, float]
Projected3D = tuple[float, float, float]


@dataclass(frozen=True)
class CartesianCell3D:
    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float


def _bounds_2d(
    points: tuple[Point2D, ...],
    *,
    pad_fraction: float,
) -> tuple[float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    xmin = min(xs)
    xmax = max(xs)
    ymin = min(ys)
    ymax = max(ys)
    span_x = max(xmax - xmin, 1.0e-12)
    span_y = max(ymax - ymin, 1.0e-12)
    pad_x = span_x * pad_fraction
    pad_y = span_y * pad_fraction
    return (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y)


def _map_point_2d(
    point: Point2D,
    *,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    margin: float,
) -> Point2D:
    xmin, ymin, xmax, ymax = bounds
    span_x = max(xmax - xmin, 1.0e-12)
    span_y = max(ymax - ymin, 1.0e-12)
    avail_w = max(width - 2.0 * margin, 1.0e-12)
    avail_h = max(height - 2.0 * margin, 1.0e-12)
    scale = min(avail_w / span_x, avail_h / span_y)
    pad_x = 0.5 * (avail_w - scale * span_x)
    pad_y = 0.5 * (avail_h - scale * span_y)

    x = margin + pad_x + (point[0] - xmin) * scale
    y = margin + pad_y + (ymax - point[1]) * scale
    return (x, y)


def _polygon_points_attr(
    polygon: tuple[Point2D, ...],
    *,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    margin: float,
) -> str:
    mapped = (
        _map_point_2d(
            point,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        for point in polygon
    )
    return " ".join(f"{x:.3f},{y:.3f}" for x, y in mapped)


def _project_3d(point: Point3D, *, center: Point3D) -> Projected3D:
    x, y, z = point
    xc = x - center[0]
    yc = y - center[1]
    zc = z - center[2]

    az = math.radians(38.0)
    ax = math.radians(-26.0)

    xz = xc * math.cos(az) - yc * math.sin(az)
    yz = xc * math.sin(az) + yc * math.cos(az)
    zz = zc

    xp = xz
    yp = yz * math.cos(ax) - zz * math.sin(ax)
    zp = yz * math.sin(ax) + zz * math.cos(ax)
    return (xp, yp, zp)


def _bounds_projected(
    points: tuple[Projected3D, ...],
    *,
    pad_fraction: float,
) -> tuple[float, float, float, float, float, float]:
    xs = [point[0] for point in points]
    ys = [point[1] for point in points]
    zs = [point[2] for point in points]
    xmin = min(xs)
    xmax = max(xs)
    ymin = min(ys)
    ymax = max(ys)
    zmin = min(zs)
    zmax = max(zs)

    span_x = max(xmax - xmin, 1.0e-12)
    span_y = max(ymax - ymin, 1.0e-12)
    pad_x = span_x * pad_fraction
    pad_y = span_y * pad_fraction

    return (xmin - pad_x, ymin - pad_y, xmax + pad_x, ymax + pad_y, zmin, zmax)


def _map_projected(
    point: Projected3D,
    *,
    bounds: tuple[float, float, float, float, float, float],
    width: int,
    height: int,
    margin: float,
) -> Point2D:
    xmin, ymin, xmax, ymax, _, _ = bounds
    span_x = max(xmax - xmin, 1.0e-12)
    span_y = max(ymax - ymin, 1.0e-12)
    avail_w = max(width - 2.0 * margin, 1.0e-12)
    avail_h = max(height - 2.0 * margin, 1.0e-12)
    scale = min(avail_w / span_x, avail_h / span_y)
    pad_x = 0.5 * (avail_w - scale * span_x)
    pad_y = 0.5 * (avail_h - scale * span_y)

    x = margin + pad_x + (point[0] - xmin) * scale
    y = margin + pad_y + (ymax - point[1]) * scale
    return (x, y)


def _normalize(value: float, *, lower: float, upper: float) -> float:
    if upper <= lower + 1.0e-20:
        return 0.5
    t = (value - lower) / (upper - lower)
    if t < 0.0:
        return 0.0
    if t > 1.0:
        return 1.0
    return t


def _rect_polygon(cell: Any) -> tuple[Point2D, ...]:
    return (
        (float(cell.x0), float(cell.y0)),
        (float(cell.x1), float(cell.y0)),
        (float(cell.x1), float(cell.y1)),
        (float(cell.x0), float(cell.y1)),
    )


def _choose_contrast_anchor_2d(
    local_panel: TrimmedPanel2D,
    cell: tuple[float, float, float, float],
) -> tuple[Point2D, tuple[int, int]]:
    x0, y0, x1, y1 = cell
    dx = x1 - x0
    dy = y1 - y0
    cx = 0.5 * (x0 + x1)
    cy = 0.5 * (y0 + y1)

    candidates: tuple[Point2D, ...] = (
        (x0, y0),
        (x1, y0),
        (x1, y1),
        (x0, y1),
        (cx, y0),
        (x1, cy),
        (cx, y1),
        (x0, cy),
        (cx, cy),
        (x0 - 0.18 * dx, y0),
        (x0, y0 - 0.18 * dy),
        (x1 + 0.18 * dx, y1),
        (x1, y1 + 0.18 * dy),
    )

    best_mixed_anchor = (x0, y0)
    best_mixed_stats = (0, 0)
    best_mixed_score = -1.0

    best_any_anchor = (x0, y0)
    best_any_stats = (0, 0)
    best_any_score = -1.0

    for candidate in candidates:
        try:
            folded = folded_quadrature_rule(
                local_panel,
                order=4,
                anchor=candidate,
                require_interior_anchor=False,
            )
        except ValueError:
            continue

        pos = sum(1 for triangle in folded.triangles if triangle.det_jacobian > 1.0e-13)
        neg = sum(
            1 for triangle in folded.triangles if triangle.det_jacobian < -1.0e-13
        )
        total = pos + neg
        if total == 0:
            continue

        balance = min(pos, neg) / total
        if balance > best_any_score:
            best_any_score = balance
            best_any_anchor = candidate
            best_any_stats = (pos, neg)

        if pos > 0 and neg > 0 and balance > best_mixed_score:
            best_mixed_score = balance
            best_mixed_anchor = candidate
            best_mixed_stats = (pos, neg)

    if best_mixed_score >= 0.0:
        return best_mixed_anchor, best_mixed_stats
    return best_any_anchor, best_any_stats


def _build_single_cell_2d_data() -> dict[str, Any]:
    panel = build_section_6_1_1_bspline_panel(sample_count=512)
    snapshot = build_poisson_galerkin_geometry_snapshot(panel, resolution=8)

    trimmed = [clip for clip in snapshot.clipped_cells if str(clip.kind) == "trimmed"]
    if not trimmed:
        raise ValueError("expected at least one trimmed cell")

    target = max(trimmed, key=lambda clip: (len(clip.polygon), float(clip.area)))
    polygon = tuple((float(x), float(y)) for x, y in target.polygon)
    cell = (
        float(target.cell.x0),
        float(target.cell.y0),
        float(target.cell.x1),
        float(target.cell.y1),
    )

    local_panel = TrimmedPanel2D(outer=PanelLoop2D(polygon))
    local_anchor, _anchor_stats = _choose_contrast_anchor_2d(local_panel, cell)
    folded = folded_quadrature_rule(
        local_panel,
        order=6,
        anchor=local_anchor,
        require_interior_anchor=False,
    )

    rays = []
    folded_count = 0
    non_folded_count = 0
    for triangle in folded.triangles:
        det = float(triangle.det_jacobian)
        sign = -1 if det < 0.0 else 1
        if sign < 0:
            folded_count += 1
        else:
            non_folded_count += 1

        rays.append(
            (
                local_anchor,
                (
                    0.5 * (float(triangle.p0[0]) + float(triangle.p1[0])),
                    0.5 * (float(triangle.p0[1]) + float(triangle.p1[1])),
                ),
                sign,
            )
        )

    points = tuple((float(x), float(y)) for x, y in folded.rule.points)
    return {
        "polygon": polygon,
        "cell": cell,
        "anchor": local_anchor,
        "rays": tuple(rays),
        "points": points,
        "triangle_count": len(folded.triangles),
        "folded_count": folded_count,
        "non_folded_count": non_folded_count,
    }


def _render_cover_2d(*, width: int = 1280, height: int = 720) -> str:
    data = _build_single_cell_2d_data()
    polygon = data["polygon"]
    cell = data["cell"]
    anchor = data["anchor"]
    rays = data["rays"]
    points = data["points"]
    triangle_count = data["triangle_count"]
    folded_count = data["folded_count"]
    non_folded_count = data["non_folded_count"]

    cell_corners = (
        (cell[0], cell[1]),
        (cell[2], cell[1]),
        (cell[2], cell[3]),
        (cell[0], cell[3]),
    )
    bounds = _bounds_2d(tuple((*polygon, *cell_corners, anchor)), pad_fraction=0.14)
    margin = 34.0

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg2d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#071126"/>'
        '<stop offset="52%" stop-color="#102b49"/>'
        '<stop offset="100%" stop-color="#1f2f3d"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="halo2d_a" cx="16%" cy="16%" r="72%">'
        '<stop offset="0%" stop-color="#34d399" stop-opacity="0.34"/>'
        '<stop offset="100%" stop-color="#34d399" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="halo2d_b" cx="82%" cy="24%" r="64%">'
        '<stop offset="0%" stop-color="#f59e0b" stop-opacity="0.22"/>'
        '<stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<linearGradient id="fillTrimmed2d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#fb923c"/>'
        '<stop offset="100%" stop-color="#f97316"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="anchor2d" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="#fb7185" stop-opacity="0.96"/>'
        '<stop offset="100%" stop-color="#fb7185" stop-opacity="0.18"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="vignette2d" cx="50%" cy="50%" r="74%">'
        '<stop offset="70%" stop-color="#000000" stop-opacity="0"/>'
        '<stop offset="100%" stop-color="#000000" stop-opacity="0.28"/>'
        "</radialGradient>"
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg2d)"/>'
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#halo2d_a)"/>'
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#halo2d_b)"/>'
    )

    grid_count = 10
    xmin, ymin, xmax, ymax = bounds
    for index in range(grid_count + 1):
        gx = xmin + (xmax - xmin) * index / grid_count
        gy = ymin + (ymax - ymin) * index / grid_count

        x0, y0 = _map_point_2d(
            (gx, ymin),
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        x1, y1 = _map_point_2d(
            (gx, ymax),
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<line x1="{x0:.3f}" y1="{y0:.3f}" x2="{x1:.3f}" y2="{y1:.3f}" '
            'stroke="#a5b4fc" stroke-opacity="0.10" stroke-width="0.9"/>'
        )

        q0x, q0y = _map_point_2d(
            (xmin, gy),
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        q1x, q1y = _map_point_2d(
            (xmax, gy),
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<line x1="{q0x:.3f}" y1="{q0y:.3f}" x2="{q1x:.3f}" y2="{q1y:.3f}" '
            'stroke="#a5b4fc" stroke-opacity="0.10" stroke-width="0.9"/>'
        )

    cell_attr = _polygon_points_attr(
        cell_corners,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    lines.append(
        f'<polygon points="{cell_attr}" fill="#0b1220" fill-opacity="0.22" '
        'stroke="#f8fafc" stroke-opacity="0.85" stroke-width="2.0" '
        'stroke-dasharray="7 6"/>'
    )

    polygon_attr = _polygon_points_attr(
        polygon,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    lines.append(
        f'<polygon points="{polygon_attr}" fill="url(#fillTrimmed2d)" '
        'fill-opacity="0.74" stroke="#f8fafc" stroke-opacity="0.92" '
        'stroke-width="2.6"/>'
    )

    ray_step = max(1, len(rays) // 170)
    for ray_start, ray_end, sign in rays[::ray_step]:
        sx, sy = _map_point_2d(
            ray_start,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        ex, ey = _map_point_2d(
            ray_end,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        color = "#67e8f9" if sign > 0 else "#f472b6"
        opacity = "0.20" if sign > 0 else "0.30"
        lines.append(
            f'<line x1="{sx:.3f}" y1="{sy:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" '
            f'stroke="{color}" stroke-opacity="{opacity}" stroke-width="1.15"/>'
        )

    point_step = max(1, len(points) // 760)
    for point in points[::point_step]:
        px, py = _map_point_2d(
            point,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<circle cx="{px:.3f}" cy="{py:.3f}" r="1.2" fill="#f8fafc" '
            'fill-opacity="0.52"/>'
        )

    ax, ay = _map_point_2d(
        anchor,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    lines.append(
        f'<circle cx="{ax:.3f}" cy="{ay:.3f}" r="15.0" fill="url(#anchor2d)"/>'
    )
    lines.append(f'<circle cx="{ax:.3f}" cy="{ay:.3f}" r="4.8" fill="#fb7185"/>')

    lines.append(
        '<text x="46" y="56" fill="#f8fafc" font-size="34" font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "2D Single-Cell Folded Cut</text>"
    )
    lines.append(
        '<text x="46" y="80" fill="#bae6fd" font-size="13" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "local anchor + curved trim</text>"
    )

    legend_x = width - 306
    legend_y = 24
    lines.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="260" height="74" rx="12" '
        'fill="#0b1224" fill-opacity="0.52" stroke="#e2e8f0" '
        'stroke-opacity="0.20"/>'
    )
    lines.append(
        f'<circle cx="{legend_x + 24}" cy="{legend_y + 24}" r="6" fill="#f97316"/>'
    )
    lines.append(
        f'<text x="{legend_x + 38}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "trimmed curve</text>"
    )
    lines.append(
        f'<circle cx="{legend_x + 132}" cy="{legend_y + 24}" r="6" fill="#67e8f9"/>'
    )
    lines.append(
        f'<text x="{legend_x + 146}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "non-folded</text>"
    )
    lines.append(
        f'<circle cx="{legend_x + 216}" cy="{legend_y + 24}" r="6" fill="#f472b6"/>'
    )
    lines.append(
        f'<text x="{legend_x + 230}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "folded</text>"
    )
    lines.append(
        f'<text x="{legend_x + 20}" y="{legend_y + 55}" fill="#bfdbfe" '
        'font-size="12" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        f"cell [{cell[0]:.3f},{cell[2]:.3f}] x [{cell[1]:.3f},{cell[3]:.3f}], "
        f"triangles={triangle_count}, +={non_folded_count}, -={folded_count}</text>"
    )

    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#vignette2d)"/>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _select_scary_cell_3d(*, resolution: int = 8) -> CartesianCell3D:
    samples = 11
    best_score = -1.0
    best_cell: CartesianCell3D | None = None

    for ix in range(resolution):
        x0 = ix / resolution
        x1 = (ix + 1) / resolution
        for iy in range(resolution):
            y0 = iy / resolution
            y1 = (iy + 1) / resolution
            for iz in range(resolution):
                z0 = iz / resolution
                z1 = (iz + 1) / resolution

                lowers: list[float] = []
                xsurfaces: list[float] = []
                for jy in range(samples):
                    y = y0 + (y1 - y0) * jy / (samples - 1)
                    for jz in range(samples):
                        z = z0 + (z1 - z0) * jz / (samples - 1)
                        x_surface = awb3d._x_surface_from_yz(y, z)
                        if x_surface is None:
                            continue

                        x_surface = float(x_surface)
                        lower = max(x0, x_surface)
                        if lower >= x1 - 1.0e-12:
                            continue

                        lowers.append(lower)
                        xsurfaces.append(x_surface)

                if len(lowers) < 45:
                    continue

                coverage = len(lowers) / (samples * samples)
                if coverage < 0.55:
                    continue

                lower_span = max(lowers) - min(lowers)
                surface_span = max(xsurfaces) - min(xsurfaces)
                avg_thickness = sum(x1 - lower for lower in lowers) / len(lowers)

                interior_bonus = (
                    1.15
                    if 0 < ix < resolution - 1
                    and 0 < iy < resolution - 1
                    and 0 < iz < resolution - 1
                    else 1.0
                )
                score = (
                    (1.25 * lower_span + 0.45 * surface_span)
                    * (0.35 + avg_thickness)
                    * coverage
                    * interior_bonus
                )

                if score > best_score:
                    best_score = score
                    best_cell = CartesianCell3D(
                        x0=x0,
                        x1=x1,
                        y0=y0,
                        y1=y1,
                        z0=z0,
                        z1=z1,
                    )

    if best_cell is None:
        return CartesianCell3D(x0=0.75, x1=0.875, y0=0.5, y1=0.625, z0=0.25, z1=0.375)
    return best_cell


def _sample_lower_surface_grid(
    cell: CartesianCell3D,
    *,
    size: int,
) -> tuple[list[list[Point3D | None]], list[Point3D]]:
    grid: list[list[Point3D | None]] = []
    active_points: list[Point3D] = []

    for iy in range(size):
        y = cell.y0 + (cell.y1 - cell.y0) * iy / (size - 1)
        row: list[Point3D | None] = []
        for iz in range(size):
            z = cell.z0 + (cell.z1 - cell.z0) * iz / (size - 1)
            x_surface = awb3d._x_surface_from_yz(y, z)
            if x_surface is None:
                row.append(None)
                continue

            lower = max(cell.x0, float(x_surface))
            if lower >= cell.x1 - 1.0e-12:
                row.append(None)
                continue

            point = (lower, y, z)
            row.append(point)
            active_points.append(point)
        grid.append(row)

    return grid, active_points


def _contiguous_polylines(
    points: list[Point3D | None],
) -> tuple[tuple[Point3D, ...], ...]:
    polylines: list[tuple[Point3D, ...]] = []
    current: list[Point3D] = []
    for point in points:
        if point is None:
            if len(current) >= 2:
                polylines.append(tuple(current))
            current = []
            continue
        current.append(point)

    if len(current) >= 2:
        polylines.append(tuple(current))
    return tuple(polylines)


def _grid_polylines(
    grid: list[list[Point3D | None]],
) -> tuple[tuple[Point3D, ...], ...]:
    lines: list[tuple[Point3D, ...]] = []

    for row in grid:
        lines.extend(_contiguous_polylines(row))

    width = len(grid[0]) if grid else 0
    for iz in range(width):
        column = [grid[iy][iz] for iy in range(len(grid))]
        lines.extend(_contiguous_polylines(column))

    return tuple(lines)


def _sub3(a: Point3D, b: Point3D) -> Point3D:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot3(a: Point3D, b: Point3D) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross3(a: Point3D, b: Point3D) -> Point3D:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _lower_surface_normal(
    grid: list[list[Point3D | None]],
    iy: int,
    iz: int,
) -> Point3D | None:
    point = grid[iy][iz]
    if point is None:
        return None

    size_y = len(grid)
    size_z = len(grid[0]) if grid else 0

    up = down = left = right = None
    for step in range(1, size_y):
        idx = iy + step
        if idx < size_y and grid[idx][iz] is not None:
            up = grid[idx][iz]
            break
    for step in range(1, size_y):
        idx = iy - step
        if idx >= 0 and grid[idx][iz] is not None:
            down = grid[idx][iz]
            break
    for step in range(1, size_z):
        idx = iz + step
        if idx < size_z and grid[iy][idx] is not None:
            right = grid[iy][idx]
            break
    for step in range(1, size_z):
        idx = iz - step
        if idx >= 0 and grid[iy][idx] is not None:
            left = grid[iy][idx]
            break

    if up is None or down is None or right is None or left is None:
        return None

    tangent_y = _sub3(up, down)
    tangent_z = _sub3(right, left)
    normal = _cross3(tangent_y, tangent_z)
    norm = abs(normal[0]) + abs(normal[1]) + abs(normal[2])
    if norm <= 1.0e-16:
        return None

    if normal[0] > 0.0:
        normal = (-normal[0], -normal[1], -normal[2])
    return normal


def _boundary_samples_with_normals(
    grid: list[list[Point3D | None]],
    cell: CartesianCell3D,
    *,
    stride: int,
) -> tuple[tuple[Point3D, Point3D], ...]:
    samples: list[tuple[Point3D, Point3D]] = []
    size_y = len(grid)
    size_z = len(grid[0]) if grid else 0

    for iy in range(0, size_y, stride):
        for iz in range(0, size_z, stride):
            point = grid[iy][iz]
            if point is None:
                continue

            lower_normal = _lower_surface_normal(grid, iy, iz)
            if lower_normal is None:
                lower_normal = (-1.0, 0.0, 0.0)
            samples.append((point, lower_normal))

            top = (cell.x1, point[1], point[2])
            samples.append((top, (1.0, 0.0, 0.0)))

    return tuple(samples)


def _choose_contrast_anchor_3d(
    cell: CartesianCell3D,
    samples: tuple[tuple[Point3D, Point3D], ...],
) -> tuple[Point3D, tuple[int, int]]:
    cx = 0.5 * (cell.x0 + cell.x1)
    cy = 0.5 * (cell.y0 + cell.y1)
    cz = 0.5 * (cell.z0 + cell.z1)

    candidates: tuple[Point3D, ...] = (
        (cell.x0, cell.y0, cell.z0),
        (cell.x0, cell.y0, cell.z1),
        (cell.x0, cell.y1, cell.z0),
        (cell.x0, cell.y1, cell.z1),
        (cell.x1, cell.y0, cell.z0),
        (cell.x1, cell.y0, cell.z1),
        (cell.x1, cell.y1, cell.z0),
        (cell.x1, cell.y1, cell.z1),
        (cx, cy, cz),
        (cell.x0, cy, cz),
        (cx, cell.y0, cz),
        (cx, cy, cell.z0),
        (cx, cell.y1, cz),
        (cx, cy, cell.z1),
        (cell.x0 + 0.30 * (cell.x1 - cell.x0), cy, cz),
        (cell.x0 + 0.50 * (cell.x1 - cell.x0), cy, cz),
    )

    best_mixed_anchor = candidates[0]
    best_mixed_stats = (0, 0)
    best_mixed_score = -1.0

    best_any_anchor = candidates[0]
    best_any_stats = (0, 0)
    best_any_score = -1.0

    for candidate in candidates:
        pos = 0
        neg = 0
        for point, normal in samples:
            measure = _dot3(_sub3(point, candidate), normal)
            if measure > 1.0e-14:
                pos += 1
            elif measure < -1.0e-14:
                neg += 1

        total = pos + neg
        if total == 0:
            continue

        balance = min(pos, neg) / total
        if balance > best_any_score:
            best_any_score = balance
            best_any_anchor = candidate
            best_any_stats = (pos, neg)

        if pos > 0 and neg > 0 and balance > best_mixed_score:
            best_mixed_score = balance
            best_mixed_anchor = candidate
            best_mixed_stats = (pos, neg)

    if best_mixed_score >= 0.0:
        return best_mixed_anchor, best_mixed_stats
    return best_any_anchor, best_any_stats


def _box_corners(cell: CartesianCell3D) -> tuple[Point3D, ...]:
    return (
        (cell.x0, cell.y0, cell.z0),
        (cell.x1, cell.y0, cell.z0),
        (cell.x1, cell.y1, cell.z0),
        (cell.x0, cell.y1, cell.z0),
        (cell.x0, cell.y0, cell.z1),
        (cell.x1, cell.y0, cell.z1),
        (cell.x1, cell.y1, cell.z1),
        (cell.x0, cell.y1, cell.z1),
    )


def _box_edges(cell: CartesianCell3D) -> tuple[tuple[Point3D, Point3D], ...]:
    corners = _box_corners(cell)
    indices = (
        (0, 1),
        (1, 2),
        (2, 3),
        (3, 0),
        (4, 5),
        (5, 6),
        (6, 7),
        (7, 4),
        (0, 4),
        (1, 5),
        (2, 6),
        (3, 7),
    )
    return tuple((corners[i0], corners[i1]) for i0, i1 in indices)


def _build_single_cell_3d_data() -> dict[str, Any]:
    cell = _select_scary_cell_3d(resolution=8)

    grid_size = 31
    grid, active_points = _sample_lower_surface_grid(cell, size=grid_size)
    if not active_points:
        raise ValueError("selected 3D cell has no active cut points")

    lower_lines = _grid_polylines(grid)
    upper_lines = tuple(
        tuple((cell.x1, point[1], point[2]) for point in polyline)
        for polyline in lower_lines
    )

    anchor_samples = _boundary_samples_with_normals(grid, cell, stride=2)
    anchor, _anchor_stats = _choose_contrast_anchor_3d(cell, anchor_samples)

    struts: list[tuple[Point3D, Point3D]] = []
    stride = 3
    for iy in range(0, grid_size, stride):
        for iz in range(0, grid_size, stride):
            point = grid[iy][iz]
            if point is None:
                continue
            top = (cell.x1, point[1], point[2])
            struts.append((point, top))

    boundary_samples = _boundary_samples_with_normals(grid, cell, stride=3)
    signed_points: dict[tuple[int, int, int], tuple[Point3D, float]] = {}
    for point, normal in boundary_samples:
        if (
            abs(point[0] - anchor[0]) <= 1.0e-12
            and abs(point[1] - anchor[1]) <= 1.0e-12
            and abs(point[2] - anchor[2]) <= 1.0e-12
        ):
            continue

        signed_measure = _dot3(_sub3(point, anchor), normal)
        if abs(signed_measure) <= 1.0e-14:
            continue

        key = (
            int(round(point[0] * 1.0e6)),
            int(round(point[1] * 1.0e6)),
            int(round(point[2] * 1.0e6)),
        )

        sign_vote = 1.0 if signed_measure > 0.0 else -1.0
        if key in signed_points:
            existing_point, vote = signed_points[key]
            signed_points[key] = (existing_point, vote + sign_vote)
        else:
            signed_points[key] = (point, sign_vote)

    boundary_points_signed = [
        (point, 1 if vote >= 0.0 else -1) for point, vote in signed_points.values()
    ]

    if not boundary_points_signed:
        for point in _box_corners(cell):
            if (
                abs(point[0] - anchor[0]) <= 1.0e-12
                and abs(point[1] - anchor[1]) <= 1.0e-12
                and abs(point[2] - anchor[2]) <= 1.0e-12
            ):
                continue
            boundary_points_signed.append((point, 1 if point[0] >= anchor[0] else -1))

    folded_count = sum(1 for _, sign in boundary_points_signed if sign < 0)
    non_folded_count = sum(1 for _, sign in boundary_points_signed if sign > 0)

    ray_step = max(1, len(boundary_points_signed) // 150)
    rays = tuple(
        (anchor, point, sign) for point, sign in boundary_points_signed[::ray_step]
    )

    radial_nodes, _ = gauss_legendre_01(4)
    cloud_sources = boundary_points_signed[
        :: max(1, len(boundary_points_signed) // 210)
    ]
    cloud_points: list[Point3D] = []
    for boundary_point, _sign in cloud_sources:
        delta = (
            boundary_point[0] - anchor[0],
            boundary_point[1] - anchor[1],
            boundary_point[2] - anchor[2],
        )
        for node in radial_nodes:
            r = float(node)
            cloud_points.append(
                (
                    anchor[0] + r * delta[0],
                    anchor[1] + r * delta[1],
                    anchor[2] + r * delta[2],
                )
            )

    return {
        "cell": cell,
        "anchor": anchor,
        "lower_lines": lower_lines,
        "upper_lines": upper_lines,
        "struts": tuple(struts),
        "rays": rays,
        "cloud_points": tuple(cloud_points),
        "box_edges": _box_edges(cell),
        "folded_count": folded_count,
        "non_folded_count": non_folded_count,
    }


def _render_cover_3d(*, width: int = 1280, height: int = 720) -> str:
    data = _build_single_cell_3d_data()
    cell: CartesianCell3D = data["cell"]
    anchor: Point3D = data["anchor"]
    lower_lines: tuple[tuple[Point3D, ...], ...] = data["lower_lines"]
    upper_lines: tuple[tuple[Point3D, ...], ...] = data["upper_lines"]
    struts: tuple[tuple[Point3D, Point3D], ...] = data["struts"]
    rays: tuple[tuple[Point3D, Point3D, int], ...] = data["rays"]
    cloud_points: tuple[Point3D, ...] = data["cloud_points"]
    box_edges: tuple[tuple[Point3D, Point3D], ...] = data["box_edges"]
    folded_count = data["folded_count"]
    non_folded_count = data["non_folded_count"]

    center = (
        0.5 * (cell.x0 + cell.x1),
        0.5 * (cell.y0 + cell.y1),
        0.5 * (cell.z0 + cell.z1),
    )

    projected_points: list[Projected3D] = [_project_3d(anchor, center=center)]
    for polyline in (*lower_lines, *upper_lines):
        projected_points.extend(_project_3d(point, center=center) for point in polyline)
    for start, end, _sign in rays:
        projected_points.append(_project_3d(start, center=center))
        projected_points.append(_project_3d(end, center=center))
    for start, end in (*struts, *box_edges):
        projected_points.append(_project_3d(start, center=center))
        projected_points.append(_project_3d(end, center=center))
    projected_points.extend(_project_3d(point, center=center) for point in cloud_points)

    bounds = _bounds_projected(tuple(projected_points), pad_fraction=0.14)
    margin = 34.0
    _, _, _, _, zmin, zmax = bounds

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg3d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#090f23"/>'
        '<stop offset="52%" stop-color="#171f3f"/>'
        '<stop offset="100%" stop-color="#22283d"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="halo3d_a" cx="82%" cy="18%" r="68%">'
        '<stop offset="0%" stop-color="#f472b6" stop-opacity="0.24"/>'
        '<stop offset="100%" stop-color="#f472b6" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="halo3d_b" cx="20%" cy="82%" r="74%">'
        '<stop offset="0%" stop-color="#22d3ee" stop-opacity="0.22"/>'
        '<stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="anchor3d" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="#fb7185" stop-opacity="0.96"/>'
        '<stop offset="100%" stop-color="#fb7185" stop-opacity="0.16"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="vignette3d" cx="50%" cy="52%" r="74%">'
        '<stop offset="72%" stop-color="#000000" stop-opacity="0"/>'
        '<stop offset="100%" stop-color="#000000" stop-opacity="0.30"/>'
        "</radialGradient>"
    )
    lines.append("</defs>")

    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#bg3d)"/>'
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#halo3d_a)"/>'
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#halo3d_b)"/>'
    )

    for start, end, sign in rays:
        p0 = _project_3d(start, center=center)
        p1 = _project_3d(end, center=center)
        x0, y0 = _map_projected(
            p0,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        x1, y1 = _map_projected(
            p1,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        depth = _normalize(p1[2], lower=zmin, upper=zmax)
        opacity = 0.10 + (0.26 if sign < 0 else 0.18) * (1.0 - depth)
        color = "#f9a8d4" if sign < 0 else "#67e8f9"
        lines.append(
            f'<line x1="{x0:.3f}" y1="{y0:.3f}" x2="{x1:.3f}" y2="{y1:.3f}" '
            f'stroke="{color}" stroke-opacity="{opacity:.3f}" stroke-width="1.0"/>'
        )

    lower_with_depth = []
    for polyline in lower_lines:
        projected = tuple(_project_3d(point, center=center) for point in polyline)
        depth = sum(point[2] for point in projected) / len(projected)
        lower_with_depth.append((depth, projected))
    lower_with_depth.sort(key=lambda item: item[0])

    for depth, projected in lower_with_depth:
        points_attr = " ".join(
            f"{x:.3f},{y:.3f}"
            for x, y in (
                _map_projected(
                    point,
                    bounds=bounds,
                    width=width,
                    height=height,
                    margin=margin,
                )
                for point in projected
            )
        )
        alpha = 0.22 + 0.50 * (1.0 - _normalize(depth, lower=zmin, upper=zmax))
        lines.append(
            f'<polyline points="{points_attr}" fill="none" stroke="#7dd3fc" '
            f'stroke-opacity="{alpha:.3f}" stroke-width="1.20"/>'
        )

    upper_with_depth = []
    for polyline in upper_lines:
        projected = tuple(_project_3d(point, center=center) for point in polyline)
        depth = sum(point[2] for point in projected) / len(projected)
        upper_with_depth.append((depth, projected))
    upper_with_depth.sort(key=lambda item: item[0])

    for depth, projected in upper_with_depth[::2]:
        points_attr = " ".join(
            f"{x:.3f},{y:.3f}"
            for x, y in (
                _map_projected(
                    point,
                    bounds=bounds,
                    width=width,
                    height=height,
                    margin=margin,
                )
                for point in projected
            )
        )
        alpha = 0.10 + 0.22 * (1.0 - _normalize(depth, lower=zmin, upper=zmax))
        lines.append(
            f'<polyline points="{points_attr}" fill="none" stroke="#c4b5fd" '
            f'stroke-opacity="{alpha:.3f}" stroke-width="1.0"/>'
        )

    for start, end in struts:
        p0 = _project_3d(start, center=center)
        p1 = _project_3d(end, center=center)
        x0, y0 = _map_projected(
            p0,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        x1, y1 = _map_projected(
            p1,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<line x1="{x0:.3f}" y1="{y0:.3f}" x2="{x1:.3f}" y2="{y1:.3f}" '
            'stroke="#93c5fd" stroke-opacity="0.12" stroke-width="0.9"/>'
        )

    cloud_with_depth = []
    cloud_step = max(1, len(cloud_points) // 950)
    for point in cloud_points[::cloud_step]:
        projected = _project_3d(point, center=center)
        cloud_with_depth.append((projected[2], projected))
    cloud_with_depth.sort(key=lambda item: item[0])

    for depth, projected in cloud_with_depth:
        x, y = _map_projected(
            projected,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        depth_norm = _normalize(depth, lower=zmin, upper=zmax)
        radius = 0.85 + 1.10 * (1.0 - depth_norm)
        opacity = 0.18 + 0.46 * (1.0 - depth_norm)
        lines.append(
            f'<circle cx="{x:.3f}" cy="{y:.3f}" r="{radius:.3f}" fill="#f8fafc" '
            f'fill-opacity="{opacity:.3f}"/>'
        )

    for start, end in box_edges:
        p0 = _project_3d(start, center=center)
        p1 = _project_3d(end, center=center)
        x0, y0 = _map_projected(
            p0,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        x1, y1 = _map_projected(
            p1,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<line x1="{x0:.3f}" y1="{y0:.3f}" x2="{x1:.3f}" y2="{y1:.3f}" '
            'stroke="#e2e8f0" stroke-opacity="0.70" stroke-width="1.4" '
            'stroke-dasharray="6 5"/>'
        )

    anchor_projected = _project_3d(anchor, center=center)
    ax, ay = _map_projected(
        anchor_projected,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    lines.append(
        f'<circle cx="{ax:.3f}" cy="{ay:.3f}" r="15.2" fill="url(#anchor3d)"/>'
    )
    lines.append(f'<circle cx="{ax:.3f}" cy="{ay:.3f}" r="5.0" fill="#fb7185"/>')

    lines.append(
        '<text x="46" y="56" fill="#f8fafc" font-size="34" font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "3D Single-Cell Folded Cut</text>"
    )
    lines.append(
        '<text x="46" y="80" fill="#c7d2fe" font-size="13" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "local anchor + curved volume cut</text>"
    )

    legend_x = width - 392
    legend_y = 24
    lines.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="346" height="74" rx="12" '
        'fill="#0a1327" fill-opacity="0.52" stroke="#dbeafe" '
        'stroke-opacity="0.20"/>'
    )
    lines.append(
        f'<circle cx="{legend_x + 24}" cy="{legend_y + 24}" r="6" fill="#7dd3fc"/>'
    )
    lines.append(
        f'<text x="{legend_x + 38}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "cut surface</text>"
    )
    lines.append(
        f'<circle cx="{legend_x + 138}" cy="{legend_y + 24}" r="6" fill="#f9a8d4"/>'
    )
    lines.append(
        f'<text x="{legend_x + 152}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "folded rays</text>"
    )
    lines.append(
        f'<circle cx="{legend_x + 222}" cy="{legend_y + 24}" r="6" fill="#67e8f9"/>'
    )
    lines.append(
        f'<text x="{legend_x + 236}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "non-folded rays</text>"
    )
    lines.append(
        f'<circle cx="{legend_x + 312}" cy="{legend_y + 24}" r="6" fill="#f8fafc"/>'
    )
    lines.append(
        f'<text x="{legend_x + 326}" y="{legend_y + 29}" fill="#f8fafc" '
        'font-size="13" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "quad cloud</text>"
    )
    lines.append(
        f'<text x="{legend_x + 20}" y="{legend_y + 55}" fill="#c7d2fe" '
        'font-size="12" font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        f"cell [{cell.x0:.3f},{cell.x1:.3f}] x [{cell.y0:.3f},{cell.y1:.3f}] x "
        f"[{cell.z0:.3f},{cell.z1:.3f}], +={non_folded_count}, -={folded_count}</text>"
    )

    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#vignette3d)"/>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(__file__).resolve().parents[1] / "docs" / "assets",
        help="Directory where README cover SVGs are written.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    output_dir = args.output_dir.resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    cover_2d = output_dir / "readme-cover-folded-2d.svg"
    cover_3d = output_dir / "readme-cover-folded-3d.svg"

    cover_2d.write_text(_render_cover_2d(), encoding="utf-8")
    cover_3d.write_text(_render_cover_3d(), encoding="utf-8")

    print(f"wrote: {cover_2d}")
    print(f"wrote: {cover_3d}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
