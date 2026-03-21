"""Folded quadrature over CAD-native 2D curve loops."""

from __future__ import annotations

from dataclasses import dataclass

from cutkit.geometry import (
    CurveEdge2D,
    CurveLoop2D,
    CurveTrimmedPanel2D,
    PanelLoop2D,
    Point2D,
    TrimmedPanel2D,
    curve_loop_signed_area,
)
from cutkit.topology import point_in_panel, select_interior_anchor

from .folded2d import gauss_legendre_01
from .rule2d import QuadratureRule2D, concatenate_rules


def _add(a: Point2D, b: Point2D) -> Point2D:
    return (a[0] + b[0], a[1] + b[1])


def _sub(a: Point2D, b: Point2D) -> Point2D:
    return (a[0] - b[0], a[1] - b[1])


def _scale(alpha: float, a: Point2D) -> Point2D:
    return (alpha * a[0], alpha * a[1])


def _cross(a: Point2D, b: Point2D) -> float:
    return a[0] * b[1] - a[1] * b[0]


def _reverse_loop(loop: CurveLoop2D) -> CurveLoop2D:
    return loop.reversed()


def _normalize_curve_panel_orientations(
    panel: CurveTrimmedPanel2D,
) -> CurveTrimmedPanel2D:
    outer = panel.outer
    if curve_loop_signed_area(outer) < 0.0:
        outer = _reverse_loop(outer)

    holes: list[CurveLoop2D] = []
    for hole in panel.holes:
        if curve_loop_signed_area(hole) > 0.0:
            holes.append(_reverse_loop(hole))
        else:
            holes.append(hole)
    return CurveTrimmedPanel2D(outer=outer, holes=tuple(holes))


def _sampled_trimmed_panel(
    panel: CurveTrimmedPanel2D, *, points_per_edge: int
) -> TrimmedPanel2D:
    outer_pts = panel.outer.sample_points(points_per_edge=points_per_edge)
    hole_pts = tuple(
        hole.sample_points(points_per_edge=points_per_edge) for hole in panel.holes
    )
    return TrimmedPanel2D(
        outer=PanelLoop2D(outer_pts),
        holes=tuple(PanelLoop2D(points) for points in hole_pts),
    )


def _sample_refinement_counts(base: int) -> tuple[int, ...]:
    start = max(16, int(base))
    counts: list[int] = []
    current = start
    for _ in range(4):
        counts.append(current)
        current *= 2
    return tuple(counts)


def _select_interior_anchor_adaptive(
    panel: CurveTrimmedPanel2D,
    *,
    base_points_per_edge: int,
) -> tuple[Point2D, TrimmedPanel2D]:
    last_error: ValueError | None = None

    for points_per_edge in _sample_refinement_counts(base_points_per_edge):
        sampled = _sampled_trimmed_panel(panel, points_per_edge=points_per_edge)
        for grid_size in (17, 33, 65, 129):
            try:
                anchor = select_interior_anchor(sampled, grid_size=grid_size)
                return anchor, sampled
            except ValueError as exc:
                last_error = exc

    if last_error is None:
        raise ValueError("unable to find interior anchor for panel")
    raise ValueError("unable to find interior anchor for panel") from last_error


def curve_sector_rule(
    edge: CurveEdge2D,
    *,
    anchor: Point2D,
    order: int,
) -> QuadratureRule2D:
    """Build a folded sector quadrature rule for one curve edge."""

    r_nodes, r_weights = gauss_legendre_01(order)
    t_nodes, t_weights = gauss_legendre_01(order)

    points: list[Point2D] = []
    weights: list[float] = []

    for t, wt in zip(t_nodes, t_weights):
        c = edge.point(t)
        dc = edge.tangent(t)
        c_rel = _sub(c, anchor)

        for r, wr in zip(r_nodes, r_weights):
            point = _add(anchor, _scale(r, c_rel))
            det_j = r * _cross(c_rel, dc)
            points.append(point)
            weights.append(det_j * wr * wt)

    return QuadratureRule2D(points=tuple(points), weights=tuple(weights))


@dataclass(frozen=True)
class FoldedCurveQuadratureResult:
    """Folded decomposition output for curve-loop trimmed panels."""

    panel: CurveTrimmedPanel2D
    anchor: Point2D
    rule: QuadratureRule2D


def folded_curve_quadrature_rule(
    panel: CurveTrimmedPanel2D,
    *,
    order: int,
    anchor: Point2D | None = None,
    require_interior_anchor: bool = True,
    anchor_sample_points: int = 48,
) -> FoldedCurveQuadratureResult:
    """Build folded quadrature on a CAD-native curve-loop panel.

    The rule uses a radial-folded map per boundary edge:

        x(r, t) = a + r * (c(t) - a),

    where ``a`` is the anchor and ``c`` is the oriented edge parameterization.
    """

    normalized = _normalize_curve_panel_orientations(panel)
    if anchor is None:
        if require_interior_anchor:
            selected_anchor, sampled = _select_interior_anchor_adaptive(
                normalized,
                base_points_per_edge=anchor_sample_points,
            )
        else:
            sampled = _sampled_trimmed_panel(
                normalized,
                points_per_edge=anchor_sample_points,
            )
            xmin, ymin, xmax, ymax = sampled.bbox()
            selected_anchor = ((xmin + xmax) * 0.5, (ymin + ymax) * 0.5)
    else:
        sampled = _sampled_trimmed_panel(
            normalized,
            points_per_edge=anchor_sample_points,
        )
        selected_anchor = (float(anchor[0]), float(anchor[1]))
        if require_interior_anchor and not point_in_panel(
            selected_anchor, sampled, include_boundary=False
        ):
            raise ValueError("provided anchor must lie strictly inside panel")

    rules: list[QuadratureRule2D] = []
    for loop in normalized.loops():
        for edge in loop.edges:
            rules.append(curve_sector_rule(edge, anchor=selected_anchor, order=order))

    rule = concatenate_rules(tuple(rules))
    return FoldedCurveQuadratureResult(
        panel=normalized,
        anchor=selected_anchor,
        rule=rule,
    )
