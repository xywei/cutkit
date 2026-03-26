"""Reusable visualization helpers for immersed Poisson Galerkin benchmarks."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Literal, Mapping

from cutkit.diagnostics.svg_plot import (
    SvgLineSeries,
    SvgLogLogChart,
    render_loglog_chart_svg,
)

ErrorMetric = Literal["abs_error", "rel_error"]


@dataclass(frozen=True)
class PoissonGalerkinPlotArtifact:
    """Output metadata for one generated Poisson Galerkin plot."""

    metric: ErrorMetric
    file_path: Path


def _metric_label(metric: ErrorMetric) -> str:
    if metric == "abs_error":
        return "Absolute Error"
    return "Relative Error"


def _backend_color(label: str) -> str:
    colors = {
        "jplus": "#1f77b4",
        "folded": "#d62728",
    }
    return colors.get(label, "#2ca02c")


def _series_for_metric(
    name: str,
    benchmark: Any,
    *,
    metric: ErrorMetric,
) -> SvgLineSeries:
    x_values = tuple(float(getattr(row, "resolution")) for row in benchmark.rows)
    y_values = tuple(float(getattr(row, metric)) for row in benchmark.rows)
    return SvgLineSeries(
        label=name,
        x_values=x_values,
        y_values=y_values,
        stroke=_backend_color(name),
    )


def render_poisson_galerkin_error_plot_svg(
    benchmarks: Mapping[str, Any],
    *,
    metric: ErrorMetric,
    title: str,
) -> str:
    """Render one immersed Poisson Galerkin convergence plot as SVG text."""

    if not benchmarks:
        raise ValueError("at least one benchmark is required")

    series = tuple(
        _series_for_metric(name, benchmark, metric=metric)
        for name, benchmark in sorted(benchmarks.items())
    )
    chart = SvgLogLogChart(
        title=title,
        x_label="Grid Resolution",
        y_label=_metric_label(metric),
        series=series,
    )
    return render_loglog_chart_svg(chart)


def write_poisson_galerkin_error_plots(
    benchmarks: Mapping[str, Any],
    *,
    output_dir: Path,
    prefix: str = "poisson-galerkin",
) -> tuple[PoissonGalerkinPlotArtifact, ...]:
    """Generate absolute/relative immersed Galerkin convergence SVG plots."""

    output_dir.mkdir(parents=True, exist_ok=True)

    any_benchmark = next(iter(benchmarks.values()))
    profile_name = str(any_benchmark.profile)

    artifacts: list[PoissonGalerkinPlotArtifact] = []
    for metric in ("abs_error", "rel_error"):
        plot_title = (
            f"Immersed Poisson Galerkin ({profile_name}, {_metric_label(metric)})"
        )
        svg_text = render_poisson_galerkin_error_plot_svg(
            benchmarks,
            metric=metric,
            title=plot_title,
        )
        file_path = output_dir / f"{prefix}-{metric}.svg"
        file_path.write_text(svg_text, encoding="utf-8")
        artifacts.append(
            PoissonGalerkinPlotArtifact(metric=metric, file_path=file_path)
        )

    return tuple(artifacts)
