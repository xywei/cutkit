"""Folded decomposition and quadrature generation for 2D trimmed panels."""

from __future__ import annotations

from dataclasses import dataclass
from math import cos, pi

from cutkit.geometry import PanelLoop2D, Point2D, TrimmedPanel2D
from cutkit.topology import (
    normalize_panel_orientations,
    point_in_panel,
    select_interior_anchor,
)

from .rule2d import QuadratureRule2D, concatenate_rules


def _cross(u: Point2D, v: Point2D) -> float:
    return u[0] * v[1] - u[1] * v[0]


def _sub(u: Point2D, v: Point2D) -> Point2D:
    return (u[0] - v[0], u[1] - v[1])


def _add(u: Point2D, v: Point2D) -> Point2D:
    return (u[0] + v[0], u[1] + v[1])


def _scale(alpha: float, u: Point2D) -> Point2D:
    return (alpha * u[0], alpha * u[1])


@dataclass(frozen=True)
class SignedTriangle2D:
    """Oriented triangle used by folded decomposition."""

    anchor: Point2D
    p0: Point2D
    p1: Point2D
    loop_index: int
    edge_index: int

    @property
    def det_jacobian(self) -> float:
        return _cross(_sub(self.p0, self.anchor), _sub(self.p1, self.anchor))

    @property
    def signed_area(self) -> float:
        return 0.5 * self.det_jacobian


@dataclass(frozen=True)
class FoldedQuadratureResult:
    """Folded decomposition output and aggregated quadrature rule."""

    panel: TrimmedPanel2D
    anchor: Point2D
    triangles: tuple[SignedTriangle2D, ...]
    rule: QuadratureRule2D


def decompose_panel(
    panel: TrimmedPanel2D,
    *,
    anchor: Point2D | None = None,
) -> tuple[TrimmedPanel2D, Point2D, tuple[SignedTriangle2D, ...]]:
    """Return normalized panel, anchor, and folded signed triangles."""

    normalized = normalize_panel_orientations(panel)
    if anchor is None:
        selected_anchor = select_interior_anchor(normalized)
    else:
        selected_anchor = (float(anchor[0]), float(anchor[1]))
        if not point_in_panel(selected_anchor, normalized, include_boundary=False):
            raise ValueError("provided anchor must lie strictly inside panel")

    triangles: list[SignedTriangle2D] = []

    loops: tuple[PanelLoop2D, ...] = (normalized.outer, *normalized.holes)
    for loop_index, loop in enumerate(loops):
        for edge_index, (p0, p1) in enumerate(loop.edges()):
            triangles.append(
                SignedTriangle2D(
                    anchor=selected_anchor,
                    p0=p0,
                    p1=p1,
                    loop_index=loop_index,
                    edge_index=edge_index,
                )
            )

    return normalized, selected_anchor, tuple(triangles)


def gauss_legendre_01(order: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    """Gauss-Legendre nodes and weights mapped to ``[0, 1]``."""

    if order < 1:
        raise ValueError("quadrature order must be positive")

    nodes_raw = [0.0] * order
    weights_raw = [0.0] * order
    midpoint = (order + 1) // 2
    eps = 1.0e-15

    for i in range(midpoint):
        z = cos(pi * (i + 0.75) / (order + 0.5))
        while True:
            p1 = 1.0
            p2 = 0.0
            for j in range(1, order + 1):
                p3 = p2
                p2 = p1
                p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j

            pp = order * (z * p1 - p2) / (z * z - 1.0)
            z_next = z - p1 / pp
            if abs(z_next - z) <= eps:
                z = z_next
                break
            z = z_next

        nodes_raw[i] = -z
        nodes_raw[order - 1 - i] = z
        weight = 2.0 / ((1.0 - z * z) * (pp * pp))
        weights_raw[i] = weight
        weights_raw[order - 1 - i] = weight

    nodes = tuple(0.5 * (value + 1.0) for value in nodes_raw)
    weights = tuple(0.5 * value for value in weights_raw)
    return nodes, weights


def triangle_duffy_rule(triangle: SignedTriangle2D, *, order: int) -> QuadratureRule2D:
    """Build a Duffy-mapped quadrature rule on one oriented triangle."""

    r_nodes, r_weights = gauss_legendre_01(order)
    s_nodes, s_weights = gauss_legendre_01(order)

    a = triangle.anchor
    b = triangle.p0
    c = triangle.p1
    ab = _sub(b, a)
    ac = _sub(c, a)
    det_j = _cross(ab, ac)

    points: list[Point2D] = []
    weights: list[float] = []

    for r, wr in zip(r_nodes, r_weights):
        one_minus_r = 1.0 - r
        for s, ws in zip(s_nodes, s_weights):
            u = r
            v = s * one_minus_r
            point = _add(a, _add(_scale(u, ab), _scale(v, ac)))
            weight = det_j * one_minus_r * wr * ws
            points.append(point)
            weights.append(weight)

    return QuadratureRule2D(points=tuple(points), weights=tuple(weights))


def folded_quadrature_rule(
    panel: TrimmedPanel2D,
    *,
    order: int,
    anchor: Point2D | None = None,
) -> FoldedQuadratureResult:
    """Build folded decomposition and aggregate to one panel quadrature rule."""

    normalized, selected_anchor, triangles = decompose_panel(panel, anchor=anchor)
    triangle_rules = tuple(
        triangle_duffy_rule(triangle, order=order) for triangle in triangles
    )
    rule = concatenate_rules(triangle_rules)
    return FoldedQuadratureResult(
        panel=normalized,
        anchor=selected_anchor,
        triangles=triangles,
        rule=rule,
    )
