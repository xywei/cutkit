"""Reusable geometry/solution figure helpers for Poisson Galerkin workflows."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, cast
from xml.sax.saxutils import escape


_FONT_FAMILY = "'IBM Plex Sans','Avenir Next','Segoe UI',sans-serif"
_CANVAS_BACKGROUND_TOP = "#f1f7ff"
_CANVAS_BACKGROUND_BOTTOM = "#fbf6ff"
_GRID_COLOR = "#d6e4f7"
_TEXT_PRIMARY = "#15253a"
_TEXT_SECONDARY = "#3e536d"


@dataclass(frozen=True)
class PoissonGalerkinFigureArtifact:
    """One generated Poisson Galerkin figure artifact."""

    kind: str
    file_path: Path


def _as_rect_polygon(cell: Any) -> tuple[tuple[float, float], ...]:
    return (
        (float(cell.x0), float(cell.y0)),
        (float(cell.x1), float(cell.y0)),
        (float(cell.x1), float(cell.y1)),
        (float(cell.x0), float(cell.y1)),
    )


def _map_point(
    x: float,
    y: float,
    *,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    margin_left: float,
    margin_top: float,
    plot_width: float,
    plot_height: float,
) -> tuple[float, float]:
    xmin, ymin, xmax, ymax = bounds
    px = margin_left + (x - xmin) * plot_width / (xmax - xmin)
    py = margin_top + (ymax - y) * plot_height / (ymax - ymin)
    return (px, py)


def _polygon_points_attr_fast(
    polygon: tuple[tuple[float, float], ...],
    *,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    margin_left: float,
    margin_top: float,
    plot_width: float,
    plot_height: float,
) -> str:
    points: list[str] = []
    for x, y in polygon:
        px, py = _map_point(
            x,
            y,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        points.append(f"{px:.3f},{py:.3f}")
    return " ".join(points)


def _panel_polyline(
    panel_polygon: tuple[tuple[float, float], ...],
    *,
    bounds: tuple[float, float, float, float],
    width: int,
    height: int,
    margin_left: float,
    margin_top: float,
    plot_width: float,
    plot_height: float,
) -> str:
    closed = panel_polygon + (panel_polygon[0],)
    points: list[str] = []
    for x, y in closed:
        px, py = _map_point(
            x,
            y,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        points.append(f"{px:.3f},{py:.3f}")
    return " ".join(points)


def _color_blend(c0: tuple[int, int, int], c1: tuple[int, int, int], t: float) -> str:
    if t < 0.0:
        t = 0.0
    elif t > 1.0:
        t = 1.0
    r = round(c0[0] * (1.0 - t) + c1[0] * t)
    g = round(c0[1] * (1.0 - t) + c1[1] * t)
    b = round(c0[2] * (1.0 - t) + c1[2] * t)
    return f"#{r:02x}{g:02x}{b:02x}"


def _diverging_color(value: float, *, vmin: float, vmax: float) -> str:
    if vmax <= vmin + 1.0e-30:
        return "#f0f0f0"
    t = (value - vmin) / (vmax - vmin)
    low = (35, 108, 171)
    mid = (251, 248, 228)
    high = (216, 86, 56)
    if t <= 0.5:
        return _color_blend(low, mid, t * 2.0)
    return _color_blend(mid, high, (t - 0.5) * 2.0)


def render_trimmed_geometry_svg(
    snapshot: Any,
    *,
    title: str = "Trimmed Geometry",
    width: int = 920,
    height: int = 620,
) -> str:
    """Render trimmed-domain geometry + Cartesian grid as SVG."""

    raw_bounds = snapshot.bounds
    bounds = cast(
        tuple[float, float, float, float],
        (
            float(raw_bounds[0]),
            float(raw_bounds[1]),
            float(raw_bounds[2]),
            float(raw_bounds[3]),
        ),
    )
    panel_polygon = tuple((float(x), float(y)) for x, y in snapshot.panel_polygon)
    resolution = int(snapshot.resolution)

    margin_left = 70.0
    margin_top = 58.0
    margin_right = 24.0
    margin_bottom = 54.0
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    xmin, ymin, xmax, ymax = bounds
    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append(
        "<defs>"
        '<linearGradient id="figure-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{_CANVAS_BACKGROUND_TOP}"/>'
        f'<stop offset="100%" stop-color="{_CANVAS_BACKGROUND_BOTTOM}"/>'
        "</linearGradient>"
        "</defs>"
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#figure-bg)"/>'
    )
    lines.append(
        f'<rect x="{margin_left - 8:.3f}" y="{margin_top - 8:.3f}" width="{plot_width + 16:.3f}" height="{plot_height + 16:.3f}" fill="#ffffff" stroke="#c7d8ee" stroke-width="1.0" rx="10"/>'
    )

    for idx in range(resolution + 1):
        x = xmin + (xmax - xmin) * idx / resolution
        y = ymin + (ymax - ymin) * idx / resolution
        px0, py0 = _map_point(
            x,
            ymin,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        px1, py1 = _map_point(
            x,
            ymax,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        lines.append(
            f'<line x1="{px0:.3f}" y1="{py0:.3f}" x2="{px1:.3f}" y2="{py1:.3f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )

        qx0, qy0 = _map_point(
            xmin,
            y,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        qx1, qy1 = _map_point(
            xmax,
            y,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        lines.append(
            f'<line x1="{qx0:.3f}" y1="{qy0:.3f}" x2="{qx1:.3f}" y2="{qy1:.3f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )

    panel_fill_points = _polygon_points_attr_fast(
        panel_polygon,
        bounds=bounds,
        width=width,
        height=height,
        margin_left=margin_left,
        margin_top=margin_top,
        plot_width=plot_width,
        plot_height=plot_height,
    )
    lines.append(
        f'<polygon points="{panel_fill_points}" fill="#ffefcf" fill-opacity="0.58" stroke="none"/>'
    )

    boundary_points = _panel_polyline(
        panel_polygon,
        bounds=bounds,
        width=width,
        height=height,
        margin_left=margin_left,
        margin_top=margin_top,
        plot_width=plot_width,
        plot_height=plot_height,
    )
    lines.append(
        f'<polyline points="{boundary_points}" fill="none" stroke="#1f3752" stroke-width="2.6"/>'
    )

    lines.append(
        f'<text x="{width / 2:.3f}" y="32" text-anchor="middle" font-size="19" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}" font-weight="600">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="{width / 2:.3f}" y="{height - 18:.3f}" text-anchor="middle" font-size="13" fill="{_TEXT_SECONDARY}" font-family="{_FONT_FAMILY}">resolution = {resolution}</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def render_cell_classification_svg(
    snapshot: Any,
    *,
    title: str = "Cell Classification",
    width: int = 920,
    height: int = 620,
) -> str:
    """Render inside/trimmed/outside cell classification as SVG."""

    raw_bounds = snapshot.bounds
    bounds = cast(
        tuple[float, float, float, float],
        (
            float(raw_bounds[0]),
            float(raw_bounds[1]),
            float(raw_bounds[2]),
            float(raw_bounds[3]),
        ),
    )
    panel_polygon = tuple((float(x), float(y)) for x, y in snapshot.panel_polygon)
    clips = tuple(snapshot.clipped_cells)

    margin_left = 70.0
    margin_top = 58.0
    margin_right = 24.0
    margin_bottom = 54.0
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    fill_map = {
        "outside": "#edf2fa",
        "inside": "#cdeed3",
        "trimmed": "#ffd7a3",
    }

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append(
        "<defs>"
        '<linearGradient id="class-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{_CANVAS_BACKGROUND_TOP}"/>'
        f'<stop offset="100%" stop-color="{_CANVAS_BACKGROUND_BOTTOM}"/>'
        "</linearGradient>"
        "</defs>"
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#class-bg)"/>'
    )
    lines.append(
        f'<rect x="{margin_left - 8:.3f}" y="{margin_top - 8:.3f}" width="{plot_width + 16:.3f}" height="{plot_height + 16:.3f}" fill="#ffffff" stroke="#c7d8ee" stroke-width="1.0" rx="10"/>'
    )

    for clip in clips:
        kind = str(clip.kind)
        polygon = tuple((float(x), float(y)) for x, y in clip.polygon)
        if not polygon:
            polygon = _as_rect_polygon(clip.cell)
        points_attr = _polygon_points_attr_fast(
            polygon,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        color = fill_map.get(kind, "#eeeeee")
        lines.append(
            f'<polygon points="{points_attr}" fill="{color}" stroke="#ccdaeb" stroke-width="0.8"/>'
        )

    boundary_points = _panel_polyline(
        panel_polygon,
        bounds=bounds,
        width=width,
        height=height,
        margin_left=margin_left,
        margin_top=margin_top,
        plot_width=plot_width,
        plot_height=plot_height,
    )
    lines.append(
        f'<polyline points="{boundary_points}" fill="none" stroke="#1f3752" stroke-width="2.4"/>'
    )

    legend_x = width - 210
    legend_y = 74
    lines.append(
        f'<rect x="{legend_x}" y="{legend_y}" width="180" height="90" fill="#ffffffdd" stroke="#c4d5ee" rx="8"/>'
    )
    legend_items = (
        ("inside", fill_map["inside"]),
        ("trimmed", fill_map["trimmed"]),
        ("outside", fill_map["outside"]),
    )
    for index, (label, color) in enumerate(legend_items):
        y = legend_y + 24 * index + 16
        lines.append(
            f'<rect x="{legend_x + 12}" y="{y}" width="18" height="12" fill="{color}" stroke="#999"/>'
        )
        lines.append(
            f'<text x="{legend_x + 40}" y="{y + 11}" font-size="13" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{escape(label)}</text>'
        )

    inside_count = int(snapshot.inside_cell_count)
    trimmed_count = int(snapshot.trimmed_cell_count)
    lines.append(
        f'<text x="{width / 2:.3f}" y="32" text-anchor="middle" font-size="19" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}" font-weight="600">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="{width / 2:.3f}" y="{height - 18:.3f}" text-anchor="middle" font-size="13" fill="{_TEXT_SECONDARY}" font-family="{_FONT_FAMILY}">inside={inside_count}, trimmed={trimmed_count}</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def _cell_center_value(
    solution: tuple[float, ...], clip: Any, *, resolution: int
) -> float:
    ix = int(clip.cell.ix)
    iy = int(clip.cell.iy)
    stride = resolution + 1
    n0 = iy * stride + ix
    n1 = iy * stride + (ix + 1)
    n2 = (iy + 1) * stride + (ix + 1)
    n3 = (iy + 1) * stride + ix
    return 0.25 * (solution[n0] + solution[n1] + solution[n2] + solution[n3])


def render_solution_field_svg(
    snapshot: Any,
    *,
    solution: tuple[float, ...],
    title: str,
    width: int = 920,
    height: int = 620,
) -> str:
    """Render immersed Poisson solution field over active cells as SVG."""

    raw_bounds = snapshot.bounds
    bounds = cast(
        tuple[float, float, float, float],
        (
            float(raw_bounds[0]),
            float(raw_bounds[1]),
            float(raw_bounds[2]),
            float(raw_bounds[3]),
        ),
    )
    panel_polygon = tuple((float(x), float(y)) for x, y in snapshot.panel_polygon)
    clips = tuple(snapshot.clipped_cells)
    resolution = int(snapshot.resolution)

    margin_left = 70.0
    margin_top = 58.0
    margin_right = 80.0
    margin_bottom = 54.0
    plot_width = width - margin_left - margin_right
    plot_height = height - margin_top - margin_bottom

    active_clips = tuple(clip for clip in clips if str(clip.kind) != "outside")
    if not active_clips:
        raise ValueError("snapshot contains no active cells")

    values = [
        _cell_center_value(solution, clip, resolution=resolution)
        for clip in active_clips
    ]
    vmin = min(values)
    vmax = max(values)

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" viewBox="0 0 {width} {height}">'
    )
    lines.append(
        "<defs>"
        '<linearGradient id="solution-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{_CANVAS_BACKGROUND_TOP}"/>'
        f'<stop offset="100%" stop-color="{_CANVAS_BACKGROUND_BOTTOM}"/>'
        "</linearGradient>"
        "</defs>"
    )
    lines.append(
        f'<rect x="0" y="0" width="{width}" height="{height}" fill="url(#solution-bg)"/>'
    )
    lines.append(
        f'<rect x="{margin_left - 8:.3f}" y="{margin_top - 8:.3f}" width="{plot_width + 16:.3f}" height="{plot_height + 16:.3f}" fill="#ffffff" stroke="#c7d8ee" stroke-width="1.0" rx="10"/>'
    )

    for clip in active_clips:
        polygon = tuple((float(x), float(y)) for x, y in clip.polygon)
        if not polygon:
            polygon = _as_rect_polygon(clip.cell)
        points_attr = _polygon_points_attr_fast(
            polygon,
            bounds=bounds,
            width=width,
            height=height,
            margin_left=margin_left,
            margin_top=margin_top,
            plot_width=plot_width,
            plot_height=plot_height,
        )
        value = _cell_center_value(solution, clip, resolution=resolution)
        color = _diverging_color(value, vmin=vmin, vmax=vmax)
        lines.append(
            f'<polygon points="{points_attr}" fill="{color}" stroke="#d5e1ef" stroke-width="0.6"/>'
        )

    boundary_points = _panel_polyline(
        panel_polygon,
        bounds=bounds,
        width=width,
        height=height,
        margin_left=margin_left,
        margin_top=margin_top,
        plot_width=plot_width,
        plot_height=plot_height,
    )
    lines.append(
        f'<polyline points="{boundary_points}" fill="none" stroke="#1f3752" stroke-width="2.1"/>'
    )

    bar_x = width - 56
    bar_y = margin_top + 20
    bar_h = plot_height - 40
    steps = 64
    for idx in range(steps):
        t0 = idx / steps
        t1 = (idx + 1) / steps
        value = vmin + (vmax - vmin) * (1.0 - t0)
        color = _diverging_color(value, vmin=vmin, vmax=vmax)
        y0 = bar_y + bar_h * t0
        h = bar_h * (t1 - t0)
        lines.append(
            f'<rect x="{bar_x}" y="{y0:.3f}" width="16" height="{h:.3f}" fill="{color}" stroke="none"/>'
        )
    lines.append(
        f'<rect x="{bar_x}" y="{bar_y:.3f}" width="16" height="{bar_h:.3f}" fill="none" stroke="#5a6980" stroke-width="0.8"/>'
    )
    lines.append(
        f'<text x="{bar_x + 22}" y="{bar_y + 4:.3f}" font-size="12" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{vmax:.3e}</text>'
    )
    lines.append(
        f'<text x="{bar_x + 22}" y="{bar_y + bar_h + 4:.3f}" font-size="12" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{vmin:.3e}</text>'
    )

    lines.append(
        f'<text x="{width / 2:.3f}" y="32" text-anchor="middle" font-size="19" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}" font-weight="600">{escape(title)}</text>'
    )
    lines.append(
        f'<text x="{width / 2:.3f}" y="{height - 18:.3f}" text-anchor="middle" font-size="13" fill="{_TEXT_SECONDARY}" font-family="{_FONT_FAMILY}">resolution = {resolution}</text>'
    )
    lines.append("</svg>")
    return "\n".join(lines) + "\n"


def write_poisson_galerkin_figure_pack(
    snapshot: Any,
    *,
    solutions: Mapping[str, tuple[float, ...]],
    output_dir: Path,
    prefix: str = "poisson-galerkin",
) -> tuple[PoissonGalerkinFigureArtifact, ...]:
    """Write geometry/classification/solution SVG figure pack to ``output_dir``."""

    output_dir.mkdir(parents=True, exist_ok=True)

    artifacts: list[PoissonGalerkinFigureArtifact] = []

    geometry_path = output_dir / f"{prefix}-geometry.svg"
    geometry_path.write_text(
        render_trimmed_geometry_svg(snapshot, title="Trimmed Geometry and Grid"),
        encoding="utf-8",
    )
    artifacts.append(
        PoissonGalerkinFigureArtifact(kind="geometry", file_path=geometry_path)
    )

    cells_path = output_dir / f"{prefix}-cell-classification.svg"
    cells_path.write_text(
        render_cell_classification_svg(snapshot, title="Cell Classification"),
        encoding="utf-8",
    )
    artifacts.append(
        PoissonGalerkinFigureArtifact(kind="cell_classification", file_path=cells_path)
    )

    for label, solution in sorted(solutions.items()):
        solution_path = output_dir / f"{prefix}-solution-{label}.svg"
        solution_path.write_text(
            render_solution_field_svg(
                snapshot,
                solution=solution,
                title=f"Poisson Solution ({label})",
            ),
            encoding="utf-8",
        )
        artifacts.append(
            PoissonGalerkinFigureArtifact(
                kind=f"solution_{label}", file_path=solution_path
            )
        )

    return tuple(artifacts)
