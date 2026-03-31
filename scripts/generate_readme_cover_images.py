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
    x = margin + (point[0] - xmin) * (width - 2.0 * margin) / (xmax - xmin)
    y = margin + (ymax - point[1]) * (height - 2.0 * margin) / (ymax - ymin)
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
    x = margin + (point[0] - xmin) * (width - 2.0 * margin) / (xmax - xmin)
    y = margin + (ymax - point[1]) * (height - 2.0 * margin) / (ymax - ymin)
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

    local_anchor = (cell[0], cell[1])
    local_panel = TrimmedPanel2D(outer=PanelLoop2D(polygon))
    folded = folded_quadrature_rule(
        local_panel,
        order=6,
        anchor=local_anchor,
        require_interior_anchor=False,
    )

    rays = tuple(
        (
            local_anchor,
            (
                0.5 * (float(triangle.p0[0]) + float(triangle.p1[0])),
                0.5 * (float(triangle.p0[1]) + float(triangle.p1[1])),
            ),
        )
        for triangle in folded.triangles
    )
    points = tuple((float(x), float(y)) for x, y in folded.rule.points)
    return {
        "polygon": polygon,
        "cell": cell,
        "anchor": local_anchor,
        "rays": rays,
        "points": points,
        "triangle_count": len(folded.triangles),
    }


def _render_cover_2d(*, width: int = 1280, height: int = 720) -> str:
    data = _build_single_cell_2d_data()
    polygon = data["polygon"]
    cell = data["cell"]
    anchor = data["anchor"]
    rays = data["rays"]
    points = data["points"]
    triangle_count = data["triangle_count"]

    cell_corners = (
        (cell[0], cell[1]),
        (cell[2], cell[1]),
        (cell[2], cell[3]),
        (cell[0], cell[3]),
    )
    bounds = _bounds_2d(tuple((*polygon, *cell_corners, anchor)), pad_fraction=0.25)
    margin = 62.0

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

    ray_step = max(1, len(rays) // 160)
    for ray_start, ray_end in rays[::ray_step]:
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
        lines.append(
            f'<line x1="{sx:.3f}" y1="{sy:.3f}" x2="{ex:.3f}" y2="{ey:.3f}" '
            'stroke="#67e8f9" stroke-opacity="0.22" stroke-width="1.15"/>'
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
        '<text x="70" y="76" fill="#f8fafc" font-size="40" font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "2D Single-Cell Folded Cut</text>"
    )
    lines.append(
        '<text x="70" y="108" fill="#bae6fd" font-size="18" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "one Cartesian cut-cell, one local anchor, one scary curved clip</text>"
    )

    lines.append(
        '<rect x="58" y="554" width="626" height="116" rx="16" '
        'fill="#0b1224" fill-opacity="0.56" stroke="#e2e8f0" '
        'stroke-opacity="0.22"/>'
    )
    lines.append('<circle cx="92" cy="588" r="7" fill="#f97316"/>')
    lines.append(
        '<text x="108" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "trimmed polygon from one box/panel intersection</text>"
    )
    lines.append('<circle cx="430" cy="588" r="7" fill="#67e8f9"/>')
    lines.append(
        '<text x="446" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "folded rays</text>"
    )
    lines.append(
        f'<text x="92" y="628" fill="#bfdbfe" font-size="14" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        f"cell=[{cell[0]:.3f},{cell[2]:.3f}] x [{cell[1]:.3f},{cell[3]:.3f}], "
        f"folded triangles={triangle_count}</text>"
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
    anchor = (cell.x0, cell.y0, cell.z0)

    grid_size = 31
    grid, active_points = _sample_lower_surface_grid(cell, size=grid_size)
    if not active_points:
        raise ValueError("selected 3D cell has no active cut points")

    lower_lines = _grid_polylines(grid)
    upper_lines = tuple(
        tuple((cell.x1, point[1], point[2]) for point in polyline)
        for polyline in lower_lines
    )

    struts: list[tuple[Point3D, Point3D]] = []
    boundary_points_raw: list[Point3D] = []
    stride = 3
    for iy in range(0, grid_size, stride):
        for iz in range(0, grid_size, stride):
            point = grid[iy][iz]
            if point is None:
                continue
            top = (cell.x1, point[1], point[2])
            struts.append((point, top))
            if (
                abs(point[0] - anchor[0]) > 1.0e-12
                or abs(point[1] - anchor[1]) > 1.0e-12
                or abs(point[2] - anchor[2]) > 1.0e-12
            ):
                boundary_points_raw.append(point)
            boundary_points_raw.append(top)

    seen: set[tuple[int, int, int]] = set()
    boundary_points: list[Point3D] = []
    for point in boundary_points_raw:
        key = (
            int(round(point[0] * 1.0e6)),
            int(round(point[1] * 1.0e6)),
            int(round(point[2] * 1.0e6)),
        )
        if key in seen:
            continue
        seen.add(key)
        boundary_points.append(point)

    ray_step = max(1, len(boundary_points) // 140)
    rays = tuple((anchor, point) for point in boundary_points[::ray_step])

    radial_nodes, _ = gauss_legendre_01(4)
    cloud_sources = boundary_points[:: max(1, len(boundary_points) // 210)]
    cloud_points: list[Point3D] = []
    for boundary_point in cloud_sources:
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
    }


def _render_cover_3d(*, width: int = 1280, height: int = 720) -> str:
    data = _build_single_cell_3d_data()
    cell: CartesianCell3D = data["cell"]
    anchor: Point3D = data["anchor"]
    lower_lines: tuple[tuple[Point3D, ...], ...] = data["lower_lines"]
    upper_lines: tuple[tuple[Point3D, ...], ...] = data["upper_lines"]
    struts: tuple[tuple[Point3D, Point3D], ...] = data["struts"]
    rays: tuple[tuple[Point3D, Point3D], ...] = data["rays"]
    cloud_points: tuple[Point3D, ...] = data["cloud_points"]
    box_edges: tuple[tuple[Point3D, Point3D], ...] = data["box_edges"]

    center = (
        0.5 * (cell.x0 + cell.x1),
        0.5 * (cell.y0 + cell.y1),
        0.5 * (cell.z0 + cell.z1),
    )

    projected_points: list[Projected3D] = [_project_3d(anchor, center=center)]
    for polyline in (*lower_lines, *upper_lines):
        projected_points.extend(_project_3d(point, center=center) for point in polyline)
    for start, end in (*rays, *struts, *box_edges):
        projected_points.append(_project_3d(start, center=center))
        projected_points.append(_project_3d(end, center=center))
    projected_points.extend(_project_3d(point, center=center) for point in cloud_points)

    bounds = _bounds_projected(tuple(projected_points), pad_fraction=0.20)
    margin = 60.0
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

    for start, end in rays:
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
        opacity = 0.11 + 0.24 * (1.0 - depth)
        lines.append(
            f'<line x1="{x0:.3f}" y1="{y0:.3f}" x2="{x1:.3f}" y2="{y1:.3f}" '
            f'stroke="#f9a8d4" stroke-opacity="{opacity:.3f}" stroke-width="1.0"/>'
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
        '<text x="70" y="76" fill="#f8fafc" font-size="40" font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "3D Single-Cell Folded Cut</text>"
    )
    lines.append(
        '<text x="70" y="108" fill="#c7d2fe" font-size="18" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "one clipped box, one local anchor, one intimidating curved volume cut</text>"
    )

    lines.append(
        '<rect x="58" y="554" width="752" height="116" rx="16" '
        'fill="#0a1327" fill-opacity="0.56" stroke="#dbeafe" '
        'stroke-opacity="0.20"/>'
    )
    lines.append('<circle cx="92" cy="588" r="7" fill="#7dd3fc"/>')
    lines.append(
        '<text x="108" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "curved lower cut-surface mesh</text>"
    )
    lines.append('<circle cx="318" cy="588" r="7" fill="#f9a8d4"/>')
    lines.append(
        '<text x="334" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "folded rays from local box vertex</text>"
    )
    lines.append('<circle cx="616" cy="588" r="7" fill="#f8fafc"/>')
    lines.append(
        '<text x="632" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "volume quadrature cloud</text>"
    )
    lines.append(
        f'<text x="92" y="628" fill="#c7d2fe" font-size="14" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        f"cell=[{cell.x0:.3f},{cell.x1:.3f}] x [{cell.y0:.3f},{cell.y1:.3f}] x "
        f"[{cell.z0:.3f},{cell.z1:.3f}]</text>"
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
