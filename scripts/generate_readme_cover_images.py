#!/usr/bin/env python3
"""Generate README cover SVGs from real folded decomposition workflows."""

from __future__ import annotations

import argparse
import math
from pathlib import Path
from typing import Any

import cutkit.evals.antolin_wei_buffa_2022_3d as awb3d
from cutkit.evals import (
    build_poisson_galerkin_geometry_snapshot,
    build_section_6_1_1_bspline_panel,
    build_section_6_1_3_boundary_triangles,
)
from cutkit.quadrature import folded_quadrature_rule

Point2D = tuple[float, float]
Point3D = tuple[float, float, float]
Projected3D = tuple[float, float, float]


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


def _rect_polygon(cell: Any) -> tuple[Point2D, ...]:
    return (
        (float(cell.x0), float(cell.y0)),
        (float(cell.x1), float(cell.y0)),
        (float(cell.x1), float(cell.y1)),
        (float(cell.x0), float(cell.y1)),
    )


def _render_cover_2d(*, width: int = 1280, height: int = 720) -> str:
    panel = build_section_6_1_1_bspline_panel(sample_count=128)
    snapshot = build_poisson_galerkin_geometry_snapshot(panel, resolution=16)
    folded = folded_quadrature_rule(panel, order=4)

    panel_polygon = tuple((float(x), float(y)) for x, y in snapshot.panel_polygon)
    clips = tuple(snapshot.clipped_cells)
    anchor = (float(folded.anchor[0]), float(folded.anchor[1]))

    all_points: list[Point2D] = [anchor]
    all_points.extend(panel_polygon)
    for clip in clips:
        polygon = tuple((float(x), float(y)) for x, y in clip.polygon)
        if polygon:
            all_points.extend(polygon)
        else:
            all_points.extend(_rect_polygon(clip.cell))

    bounds = _bounds_2d(tuple(all_points), pad_fraction=0.12)
    xmin, ymin, xmax, ymax = bounds
    margin = 58.0

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg2d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#061225"/>'
        '<stop offset="48%" stop-color="#102949"/>'
        '<stop offset="100%" stop-color="#1e2d3c"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="halo2d_a" cx="16%" cy="14%" r="76%">'
        '<stop offset="0%" stop-color="#34d399" stop-opacity="0.34"/>'
        '<stop offset="100%" stop-color="#34d399" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="halo2d_b" cx="86%" cy="26%" r="62%">'
        '<stop offset="0%" stop-color="#f59e0b" stop-opacity="0.20"/>'
        '<stop offset="100%" stop-color="#f59e0b" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="anchor2d" cx="50%" cy="50%" r="50%">'
        '<stop offset="0%" stop-color="#fb7185" stop-opacity="0.96"/>'
        '<stop offset="100%" stop-color="#fb7185" stop-opacity="0.16"/>'
        "</radialGradient>"
    )
    lines.append(
        '<linearGradient id="trimmed2d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#f59e0b"/>'
        '<stop offset="100%" stop-color="#f97316"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="inside2d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#22d3ee"/>'
        '<stop offset="100%" stop-color="#38bdf8"/>'
        "</linearGradient>"
    )
    lines.append(
        '<linearGradient id="panelStroke2d" x1="0" y1="0" x2="1" y2="0">'
        '<stop offset="0%" stop-color="#e2e8f0"/>'
        '<stop offset="50%" stop-color="#cbd5e1"/>'
        '<stop offset="100%" stop-color="#e2e8f0"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="vignette2d" cx="50%" cy="48%" r="72%">'
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

    for idx in range(snapshot.resolution + 1):
        if idx % 2 != 0:
            continue

        gx = xmin + (xmax - xmin) * idx / snapshot.resolution
        gy = ymin + (ymax - ymin) * idx / snapshot.resolution

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
            'stroke="#94a3b8" stroke-opacity="0.12" stroke-width="0.9"/>'
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
            'stroke="#94a3b8" stroke-opacity="0.12" stroke-width="0.9"/>'
        )

    fill_map = {
        "inside": ("url(#inside2d)", "0.34"),
        "trimmed": ("url(#trimmed2d)", "0.72"),
    }

    for clip in clips:
        kind = str(clip.kind)
        if kind == "outside":
            continue

        polygon = tuple((float(x), float(y)) for x, y in clip.polygon)
        if not polygon:
            polygon = _rect_polygon(clip.cell)

        points_attr = _polygon_points_attr(
            polygon,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        fill, opacity = fill_map.get(kind, ("#94a3b8", "0.24"))
        lines.append(
            f'<polygon points="{points_attr}" fill="{fill}" fill-opacity="{opacity}" '
            'stroke="#d1d5db" stroke-opacity="0.20" stroke-width="0.8"/>'
        )

    triangle_step = max(1, len(folded.triangles) // 96)
    anchor_px, anchor_py = _map_point_2d(
        anchor,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    for triangle in folded.triangles[::triangle_step]:
        mid = (
            0.5 * (float(triangle.p0[0]) + float(triangle.p1[0])),
            0.5 * (float(triangle.p0[1]) + float(triangle.p1[1])),
        )
        px, py = _map_point_2d(
            mid,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        distance = math.hypot(px - anchor_px, py - anchor_py)
        opacity = 0.14 if distance > 260.0 else 0.24
        lines.append(
            f'<line x1="{anchor_px:.3f}" y1="{anchor_py:.3f}" x2="{px:.3f}" y2="{py:.3f}" '
            f'stroke="#7dd3fc" stroke-opacity="{opacity:.3f}" stroke-width="1.15"/>'
        )

    point_step = max(1, len(folded.rule.points) // 620)
    for x, y in folded.rule.points[::point_step]:
        px, py = _map_point_2d(
            (float(x), float(y)),
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        lines.append(
            f'<circle cx="{px:.3f}" cy="{py:.3f}" r="1.15" fill="#f8fafc" fill-opacity="0.48"/>'
        )

    boundary_points = panel_polygon + (panel_polygon[0],)
    boundary_attr = _polygon_points_attr(
        boundary_points,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    lines.append(
        f'<polyline points="{boundary_attr}" fill="none" stroke="#e2e8f0" '
        'stroke-width="5.4" stroke-opacity="0.20"/>'
    )
    lines.append(
        f'<polyline points="{boundary_attr}" fill="none" stroke="url(#panelStroke2d)" '
        'stroke-width="2.8" stroke-opacity="0.95"/>'
    )

    lines.append(
        f'<circle cx="{anchor_px:.3f}" cy="{anchor_py:.3f}" r="16.0" fill="url(#anchor2d)"/>'
    )
    lines.append(
        f'<circle cx="{anchor_px:.3f}" cy="{anchor_py:.3f}" r="4.8" fill="#fb7185" fill-opacity="0.96"/>'
    )

    lines.append(
        '<rect x="58" y="554" width="498" height="116" rx="16" '
        'fill="#0b1224" fill-opacity="0.54" stroke="#e2e8f0" '
        'stroke-opacity="0.22"/>'
    )
    lines.append('<circle cx="92" cy="588" r="7" fill="url(#trimmed2d)"/>')
    lines.append(
        '<text x="108" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "trimmed cells</text>"
    )
    lines.append('<circle cx="246" cy="588" r="7" fill="url(#inside2d)"/>')
    lines.append(
        '<text x="262" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "inside cells</text>"
    )
    lines.append('<circle cx="388" cy="588" r="7" fill="#fb7185"/>')
    lines.append(
        '<text x="404" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "fold anchor</text>"
    )
    lines.append(
        '<text x="92" y="630" fill="#bfdbfe" font-size="14" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "real CUTKIT 2D pipeline: CAD-like panel -> cut classification -> "
        "folded quadrature cloud</text>"
    )

    lines.append(
        '<text x="70" y="76" fill="#f8fafc" font-size="40" '
        'font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "2D Folded Decomposition</text>"
    )
    lines.append(
        '<text x="70" y="108" fill="#bae6fd" font-size="18" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "topology-aware CAD clipping rendered as a solver-ready folded "
        "field</text>"
    )

    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#vignette2d)"/>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _project_3d(point: Point3D) -> Projected3D:
    x, y, z = point
    xc = x - 0.58
    yc = y - 0.62
    zc = z - 0.48

    az = math.radians(34.0)
    ax = math.radians(-28.0)

    xz = xc * math.cos(az) - yc * math.sin(az)
    yz = xc * math.sin(az) + yc * math.cos(az)
    zz = zc

    xp = xz
    yp = yz * math.cos(ax) - zz * math.sin(ax)
    zp = yz * math.sin(ax) + zz * math.cos(ax)
    return (xp, yp, zp)


def _build_surface_mesh_lines(boundary: Any) -> tuple[tuple[Point3D, ...], ...]:
    lines: list[tuple[Point3D, ...]] = []
    for patch in tuple(awb3d._BOUNDARY_PATCHES):
        s_count = max(8, int(boundary.surface_resolution))
        if patch in {"curved", "x1"}:
            t_count = max(8, int(boundary.surface_resolution))
        else:
            t_count = max(6, int(boundary.side_resolution) * 6)

        for i in range(s_count + 1):
            s = i / s_count
            line = tuple(
                awb3d._patch_point(patch, s, j / t_count) for j in range(t_count + 1)
            )
            lines.append(line)

        for j in range(t_count + 1):
            t = j / t_count
            line = tuple(
                awb3d._patch_point(patch, i / s_count, t) for i in range(s_count + 1)
            )
            lines.append(line)

    return tuple(lines)


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


def _render_cover_3d(*, width: int = 1280, height: int = 720) -> str:
    boundary = build_section_6_1_3_boundary_triangles(
        surface_resolution=12,
        side_resolution=3,
    )
    seed: Point3D = (1.0, 1.0, 0.5)

    mesh_lines = _build_surface_mesh_lines(boundary)[::2]
    surface_rule = awb3d._surface_rule(boundary, order=5)
    folded_points, _ = awb3d._folded_volume_rule(boundary, seed=seed, order=3)

    projected_seed = _project_3d(seed)
    projected_mesh = tuple(
        tuple(_project_3d(point) for point in line) for line in mesh_lines
    )
    projected_surface = tuple(_project_3d(point) for point in surface_rule.points)
    projected_folded = tuple(_project_3d(point) for point in folded_points)

    all_projected: list[Projected3D] = [projected_seed]
    for line in projected_mesh:
        all_projected.extend(line)
    all_projected.extend(projected_surface)
    all_projected.extend(projected_folded)

    bounds = _bounds_projected(tuple(all_projected), pad_fraction=0.15)
    _, _, _, _, zmin, zmax = bounds
    margin = 58.0

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" '
        f'height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append("<defs>")
    lines.append(
        '<linearGradient id="bg3d" x1="0" y1="0" x2="1" y2="1">'
        '<stop offset="0%" stop-color="#090f23"/>'
        '<stop offset="52%" stop-color="#171e3d"/>'
        '<stop offset="100%" stop-color="#22273d"/>'
        "</linearGradient>"
    )
    lines.append(
        '<radialGradient id="halo3d_a" cx="80%" cy="18%" r="68%">'
        '<stop offset="0%" stop-color="#f472b6" stop-opacity="0.24"/>'
        '<stop offset="100%" stop-color="#f472b6" stop-opacity="0"/>'
        "</radialGradient>"
    )
    lines.append(
        '<radialGradient id="halo3d_b" cx="18%" cy="82%" r="74%">'
        '<stop offset="0%" stop-color="#22d3ee" stop-opacity="0.22"/>'
        '<stop offset="100%" stop-color="#22d3ee" stop-opacity="0"/>'
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

    seed_px, seed_py = _map_projected(
        projected_seed,
        bounds=bounds,
        width=width,
        height=height,
        margin=margin,
    )
    ray_step = max(1, len(projected_surface) // 92)
    for point in projected_surface[::ray_step]:
        px, py = _map_projected(
            point,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        depth = _normalize(point[2], lower=zmin, upper=zmax)
        opacity = 0.11 + 0.20 * (1.0 - depth)
        lines.append(
            f'<line x1="{seed_px:.3f}" y1="{seed_py:.3f}" x2="{px:.3f}" y2="{py:.3f}" '
            f'stroke="#f9a8d4" stroke-opacity="{opacity:.3f}" stroke-width="1.0"/>'
        )

    mesh_with_depth: list[tuple[float, tuple[Projected3D, ...]]] = []
    for polyline in projected_mesh:
        avg_depth = sum(point[2] for point in polyline) / len(polyline)
        mesh_with_depth.append((avg_depth, polyline))
    mesh_with_depth.sort(key=lambda item: item[0])

    for avg_depth, polyline in mesh_with_depth:
        points_attr = " ".join(
            f"{px:.3f},{py:.3f}"
            for px, py in (
                _map_projected(
                    point,
                    bounds=bounds,
                    width=width,
                    height=height,
                    margin=margin,
                )
                for point in polyline
            )
        )
        depth = _normalize(avg_depth, lower=zmin, upper=zmax)
        opacity = 0.20 + 0.46 * (1.0 - depth)
        stroke = "#7dd3fc" if depth > 0.5 else "#bfdbfe"
        lines.append(
            f'<polyline points="{points_attr}" fill="none" stroke="{stroke}" '
            f'stroke-opacity="{opacity:.3f}" stroke-width="1.10"/>'
        )

    surface_step = max(1, len(projected_surface) // 280)
    for point in projected_surface[::surface_step]:
        px, py = _map_projected(
            point,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        depth = _normalize(point[2], lower=zmin, upper=zmax)
        radius = 0.85 + 0.55 * (1.0 - depth)
        opacity = 0.10 + 0.20 * (1.0 - depth)
        lines.append(
            f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{radius:.3f}" fill="#93c5fd" '
            f'fill-opacity="{opacity:.3f}"/>'
        )

    folded_step = max(1, len(projected_folded) // 760)
    for point in projected_folded[::folded_step]:
        px, py = _map_projected(
            point,
            bounds=bounds,
            width=width,
            height=height,
            margin=margin,
        )
        depth = _normalize(point[2], lower=zmin, upper=zmax)
        radius = 0.85 + 1.0 * (1.0 - depth)
        opacity = 0.20 + 0.42 * (1.0 - depth)
        lines.append(
            f'<circle cx="{px:.3f}" cy="{py:.3f}" r="{radius:.3f}" fill="#f8fafc" '
            f'fill-opacity="{opacity:.3f}"/>'
        )

    lines.append(
        f'<circle cx="{seed_px:.3f}" cy="{seed_py:.3f}" r="15.8" fill="#fb7185" fill-opacity="0.26"/>'
    )
    lines.append(
        f'<circle cx="{seed_px:.3f}" cy="{seed_py:.3f}" r="5.4" fill="#fb7185" fill-opacity="0.97"/>'
    )

    lines.append(
        '<rect x="58" y="554" width="568" height="116" rx="16" '
        'fill="#0a1327" fill-opacity="0.56" stroke="#dbeafe" '
        'stroke-opacity="0.20"/>'
    )
    lines.append('<circle cx="92" cy="588" r="7" fill="#7dd3fc"/>')
    lines.append(
        '<text x="108" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "curved CAD boundary mesh</text>"
    )
    lines.append('<circle cx="292" cy="588" r="7" fill="#f9a8d4"/>')
    lines.append(
        '<text x="308" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "folded rays from interior seed</text>"
    )
    lines.append('<circle cx="514" cy="588" r="7" fill="#f8fafc"/>')
    lines.append(
        '<text x="530" y="594" fill="#f8fafc" font-size="15" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "quadrature cloud</text>"
    )
    lines.append(
        '<text x="92" y="630" fill="#c7d2fe" font-size="14" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "real CUTKIT 3D path: Section 6.1.3 boundary -> folded volume "
        "sampling without triangulation</text>"
    )

    lines.append(
        '<text x="70" y="76" fill="#f8fafc" font-size="40" '
        'font-weight="700" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "3D Folded Decomposition</text>"
    )
    lines.append(
        '<text x="70" y="108" fill="#c7d2fe" font-size="18" '
        'font-family="Avenir Next, Futura, Trebuchet MS, sans-serif">'
        "curved solid clipping and folded quadrature rendered as a "
        "solver-facing field</text>"
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
