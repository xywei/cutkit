"""Reusable SVG plotting helpers for deterministic diagnostics artifacts."""

from __future__ import annotations

from dataclasses import dataclass
from math import ceil, floor, log10
from xml.sax.saxutils import escape


_FONT_FAMILY = "'IBM Plex Sans','Avenir Next','Segoe UI',sans-serif"
_CANVAS_BACKGROUND_TOP = "#eef6ff"
_CANVAS_BACKGROUND_BOTTOM = "#f9f5ff"
_PLOT_BACKGROUND = "#ffffff"
_GRID_COLOR = "#dbe7f7"
_AXIS_COLOR = "#233044"
_TEXT_PRIMARY = "#142032"
_TEXT_SECONDARY = "#42556e"


@dataclass(frozen=True)
class SvgLineSeries:
    """One line series for an SVG chart."""

    label: str
    x_values: tuple[float, ...]
    y_values: tuple[float, ...]
    stroke: str = "#1f77b4"


@dataclass(frozen=True)
class SvgLogLogChart:
    """Configuration for rendering one log-log SVG line chart."""

    title: str
    x_label: str
    y_label: str
    series: tuple[SvgLineSeries, ...]
    width: int = 900
    height: int = 560


def _format_tick(value: float) -> str:
    exponent = int(round(log10(value)))
    if abs(value - 1.0) <= 1.0e-12:
        return "1"
    if exponent == 0:
        return f"{value:.2g}"
    return f"1e{exponent:+d}"


def _log_ticks(min_value: float, max_value: float) -> tuple[float, ...]:
    start = floor(log10(min_value))
    end = ceil(log10(max_value))
    ticks = tuple(10.0**exp for exp in range(start, end + 1))
    return tuple(tick for tick in ticks if min_value <= tick <= max_value)


def _validate_chart(chart: SvgLogLogChart) -> None:
    if chart.width < 320 or chart.height < 240:
        raise ValueError("chart dimensions must be at least 320x240")
    if not chart.series:
        raise ValueError("at least one series is required")

    for row in chart.series:
        if not row.x_values or not row.y_values:
            raise ValueError("series values must be non-empty")
        if len(row.x_values) != len(row.y_values):
            raise ValueError("series x and y values must have the same length")
        if any(x <= 0.0 for x in row.x_values):
            raise ValueError("log-log chart requires strictly positive x values")
        if any(y <= 0.0 for y in row.y_values):
            raise ValueError("log-log chart requires strictly positive y values")


def render_loglog_chart_svg(chart: SvgLogLogChart) -> str:
    """Render a deterministic log-log SVG chart with axes, grid, and legend."""

    _validate_chart(chart)

    margin_left = 96.0
    margin_right = 28.0
    margin_top = 52.0
    margin_bottom = 88.0
    plot_width = chart.width - margin_left - margin_right
    plot_height = chart.height - margin_top - margin_bottom

    all_x = [value for row in chart.series for value in row.x_values]
    all_y = [value for row in chart.series for value in row.y_values]
    min_x = min(all_x)
    max_x = max(all_x)
    min_y = min(all_y)
    max_y = max(all_y)

    lx0 = log10(min_x)
    lx1 = log10(max_x)
    ly0 = log10(min_y)
    ly1 = log10(max_y)
    if abs(lx1 - lx0) <= 1.0e-15:
        lx0 -= 0.5
        lx1 += 0.5
    if abs(ly1 - ly0) <= 1.0e-15:
        ly0 -= 0.5
        ly1 += 0.5

    def map_x(value: float) -> float:
        return margin_left + (log10(value) - lx0) * plot_width / (lx1 - lx0)

    def map_y(value: float) -> float:
        return margin_top + (ly1 - log10(value)) * plot_height / (ly1 - ly0)

    x_ticks = _log_ticks(min_x, max_x)
    y_ticks = _log_ticks(min_y, max_y)
    if not x_ticks:
        x_ticks = (min_x, max_x)
    if not y_ticks:
        y_ticks = (min_y, max_y)

    lines: list[str] = []
    lines.append(
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{chart.width}" height="{chart.height}" viewBox="0 0 {chart.width} {chart.height}">'
    )
    lines.append(
        "<defs>"
        '<linearGradient id="chart-bg" x1="0" y1="0" x2="0" y2="1">'
        f'<stop offset="0%" stop-color="{_CANVAS_BACKGROUND_TOP}"/>'
        f'<stop offset="100%" stop-color="{_CANVAS_BACKGROUND_BOTTOM}"/>'
        "</linearGradient>"
        "</defs>"
    )
    lines.append(
        f'<rect x="0" y="0" width="{chart.width}" height="{chart.height}" fill="url(#chart-bg)"/>'
    )
    lines.append(
        f'<rect x="{margin_left - 6:.3f}" y="{margin_top - 6:.3f}" width="{plot_width + 12:.3f}" height="{plot_height + 12:.3f}" fill="{_PLOT_BACKGROUND}" stroke="#c7d7ee" stroke-width="1.0" rx="10"/>'
    )

    for value in x_ticks:
        px = map_x(value)
        lines.append(
            f'<line x1="{px:.3f}" y1="{margin_top:.3f}" x2="{px:.3f}" y2="{margin_top + plot_height:.3f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{px:.3f}" y="{margin_top + plot_height + 24:.3f}" text-anchor="middle" font-size="13" fill="{_TEXT_SECONDARY}" font-family="{_FONT_FAMILY}">{escape(_format_tick(value))}</text>'
        )

    for value in y_ticks:
        py = map_y(value)
        lines.append(
            f'<line x1="{margin_left:.3f}" y1="{py:.3f}" x2="{margin_left + plot_width:.3f}" y2="{py:.3f}" stroke="{_GRID_COLOR}" stroke-width="1"/>'
        )
        lines.append(
            f'<text x="{margin_left - 12:.3f}" y="{py + 4:.3f}" text-anchor="end" font-size="13" fill="{_TEXT_SECONDARY}" font-family="{_FONT_FAMILY}">{escape(_format_tick(value))}</text>'
        )

    lines.append(
        f'<line x1="{margin_left:.3f}" y1="{margin_top:.3f}" x2="{margin_left:.3f}" y2="{margin_top + plot_height:.3f}" stroke="{_AXIS_COLOR}" stroke-width="1.4"/>'
    )
    lines.append(
        f'<line x1="{margin_left:.3f}" y1="{margin_top + plot_height:.3f}" x2="{margin_left + plot_width:.3f}" y2="{margin_top + plot_height:.3f}" stroke="{_AXIS_COLOR}" stroke-width="1.4"/>'
    )

    for row in chart.series:
        pairs = sorted(zip(row.x_values, row.y_values, strict=True), key=lambda p: p[0])
        polyline_points = " ".join(f"{map_x(x):.3f},{map_y(y):.3f}" for x, y in pairs)
        lines.append(
            f'<polyline points="{polyline_points}" fill="none" stroke="{escape(row.stroke)}" stroke-width="2.8" stroke-linecap="round" stroke-linejoin="round"/>'
        )
        for x, y in pairs:
            lines.append(
                f'<circle cx="{map_x(x):.3f}" cy="{map_y(y):.3f}" r="3.6" fill="{escape(row.stroke)}" stroke="#ffffff" stroke-width="1.2"/>'
            )

    legend_x = margin_left + plot_width - 210.0
    legend_y = margin_top + 10.0
    legend_height = 24.0 * len(chart.series) + 14.0
    lines.append(
        f'<rect x="{legend_x:.3f}" y="{legend_y:.3f}" width="200" height="{legend_height:.3f}" fill="#ffffffdd" stroke="#c4d5ee" rx="8"/>'
    )
    for index, row in enumerate(chart.series):
        y = legend_y + 24.0 * index + 18.0
        lines.append(
            f'<line x1="{legend_x + 10:.3f}" y1="{y:.3f}" x2="{legend_x + 34:.3f}" y2="{y:.3f}" stroke="{escape(row.stroke)}" stroke-width="2.4"/>'
        )
        lines.append(
            f'<text x="{legend_x + 40:.3f}" y="{y + 4:.3f}" font-size="13" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{escape(row.label)}</text>'
        )

    lines.append(
        f'<text x="{chart.width / 2:.3f}" y="32" text-anchor="middle" font-size="19" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}" font-weight="600">{escape(chart.title)}</text>'
    )
    lines.append(
        f'<text x="{chart.width / 2:.3f}" y="{chart.height - 24:.3f}" text-anchor="middle" font-size="15" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{escape(chart.x_label)}</text>'
    )
    lines.append(
        f'<text x="26" y="{chart.height / 2:.3f}" text-anchor="middle" transform="rotate(-90 26 {chart.height / 2:.3f})" font-size="15" fill="{_TEXT_PRIMARY}" font-family="{_FONT_FAMILY}">{escape(chart.y_label)}</text>'
    )

    lines.append("</svg>")
    return "\n".join(lines) + "\n"
