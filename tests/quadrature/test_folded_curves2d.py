from __future__ import annotations

import pytest

from cutkit.geometry import CurveEdge2D, CurveLoop2D, CurveTrimmedPanel2D
from cutkit.quadrature import folded_curve_quadrature_rule


def _parabola_edge() -> CurveEdge2D:
    def eval_curve(t: float) -> tuple[float, float]:
        return (t, t * t)

    def deriv_curve(t: float) -> tuple[float, float]:
        return (1.0, 2.0 * t)

    return CurveEdge2D(evaluator=eval_curve, derivative=deriv_curve)


def test_folded_curve_quadrature_line_loop_area() -> None:
    panel = CurveTrimmedPanel2D(
        outer=CurveLoop2D(
            edges=(
                CurveEdge2D.line((0.0, 0.0), (1.0, 0.0)),
                CurveEdge2D.line((1.0, 0.0), (1.0, 1.0)),
                CurveEdge2D.line((1.0, 1.0), (0.0, 1.0)),
                CurveEdge2D.line((0.0, 1.0), (0.0, 0.0)),
            )
        )
    )

    folded = folded_curve_quadrature_rule(panel, order=4)
    assert sum(folded.rule.weights) == pytest.approx(1.0, abs=1.0e-12)


def test_folded_curve_quadrature_curved_loop_area() -> None:
    panel = CurveTrimmedPanel2D(
        outer=CurveLoop2D(
            edges=(
                _parabola_edge(),
                CurveEdge2D.line((1.0, 1.0), (0.0, 1.0)),
                CurveEdge2D.line((0.0, 1.0), (0.0, 0.0)),
            )
        )
    )

    folded = folded_curve_quadrature_rule(panel, order=8)
    assert sum(folded.rule.weights) == pytest.approx(2.0 / 3.0, abs=2.0e-10)


def test_folded_curve_anchor_must_be_inside_when_required() -> None:
    panel = CurveTrimmedPanel2D(
        outer=CurveLoop2D(
            edges=(
                _parabola_edge(),
                CurveEdge2D.line((1.0, 1.0), (0.0, 1.0)),
                CurveEdge2D.line((0.0, 1.0), (0.0, 0.0)),
            )
        )
    )

    with pytest.raises(ValueError):
        folded_curve_quadrature_rule(panel, order=6, anchor=(1.5, 0.5))


def test_curve_loop_rejects_discontinuous_edges() -> None:
    with pytest.raises(ValueError):
        CurveLoop2D(
            edges=(
                CurveEdge2D.line((0.0, 0.0), (1.0, 0.0)),
                CurveEdge2D.line((2.0, 0.0), (2.0, 1.0)),
                CurveEdge2D.line((2.0, 2.0), (1.0, 2.0)),
                CurveEdge2D.line((0.0, 2.0), (0.0, 1.0)),
            )
        )
