from __future__ import annotations

import pytest

from cutkit.diagnostics import SvgLineSeries, SvgLogLogChart, render_loglog_chart_svg


def test_render_loglog_chart_svg_is_deterministic() -> None:
    chart = SvgLogLogChart(
        title="Convergence",
        x_label="Grid Resolution",
        y_label="Error",
        series=(
            SvgLineSeries(
                label="jplus",
                x_values=(8.0, 16.0, 32.0),
                y_values=(1.0e-3, 2.0e-4, 5.0e-5),
                stroke="#1f77b4",
            ),
            SvgLineSeries(
                label="folded",
                x_values=(8.0, 16.0, 32.0),
                y_values=(1.2e-3, 2.2e-4, 5.5e-5),
                stroke="#d62728",
            ),
        ),
    )

    first = render_loglog_chart_svg(chart)
    second = render_loglog_chart_svg(chart)

    assert first == second
    assert "<svg" in first
    assert "Convergence" in first
    assert "jplus" in first
    assert "folded" in first


def test_render_loglog_chart_rejects_non_positive_values() -> None:
    chart = SvgLogLogChart(
        title="Invalid",
        x_label="x",
        y_label="y",
        series=(
            SvgLineSeries(
                label="bad",
                x_values=(0.0, 1.0),
                y_values=(1.0, 1.0),
            ),
        ),
    )

    with pytest.raises(ValueError, match="strictly positive"):
        render_loglog_chart_svg(chart)
