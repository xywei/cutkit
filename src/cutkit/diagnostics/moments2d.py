"""Diagnostics for area and low-order moments on 2D folded rules."""

from __future__ import annotations

from dataclasses import dataclass

from cutkit.geometry import Point2D, TrimmedPanel2D
from cutkit.quadrature import QuadratureRule2D, SignedTriangle2D
from cutkit.topology import signed_area


MONOMIALS_DEGREE2: tuple[tuple[int, int], ...] = (
    (0, 0),
    (1, 0),
    (0, 1),
    (2, 0),
    (1, 1),
    (0, 2),
)


@dataclass(frozen=True)
class AreaConsistencyReport:
    panel_area: float
    triangle_area: float
    rule_area: float
    triangle_abs_error: float
    rule_abs_error: float


@dataclass(frozen=True)
class MomentError:
    powers: tuple[int, int]
    exact: float
    approximate: float
    abs_error: float


@dataclass(frozen=True)
class MomentReport:
    errors: tuple[MomentError, ...]

    @property
    def max_abs_error(self) -> float:
        if not self.errors:
            return 0.0
        return max(error.abs_error for error in self.errors)


def _triangle_vertex_tuples(
    triangle: SignedTriangle2D,
) -> tuple[Point2D, Point2D, Point2D]:
    return (triangle.anchor, triangle.p0, triangle.p1)


def _triangle_integral_degree2(
    triangle: SignedTriangle2D, powers: tuple[int, int]
) -> float:
    (x1, y1), (x2, y2), (x3, y3) = _triangle_vertex_tuples(triangle)
    area = triangle.signed_area
    px, py = powers

    if (px, py) == (0, 0):
        return area
    if (px, py) == (1, 0):
        return area * (x1 + x2 + x3) / 3.0
    if (px, py) == (0, 1):
        return area * (y1 + y2 + y3) / 3.0
    if (px, py) == (2, 0):
        return area * (x1 * x1 + x2 * x2 + x3 * x3 + x1 * x2 + x2 * x3 + x3 * x1) / 6.0
    if (px, py) == (0, 2):
        return area * (y1 * y1 + y2 * y2 + y3 * y3 + y1 * y2 + y2 * y3 + y3 * y1) / 6.0
    if (px, py) == (1, 1):
        return (
            area
            * (
                2.0 * (x1 * y1 + x2 * y2 + x3 * y3)
                + x1 * y2
                + x2 * y1
                + x2 * y3
                + x3 * y2
                + x3 * y1
                + x1 * y3
            )
            / 12.0
        )

    raise ValueError(f"unsupported powers for degree-2 diagnostics: {powers}")


def panel_area_from_loops(panel: TrimmedPanel2D) -> float:
    """Return signed panel area from normalized loop orientation conventions."""

    return signed_area(panel.outer) + sum(signed_area(hole) for hole in panel.holes)


def area_consistency(
    panel: TrimmedPanel2D,
    triangles: tuple[SignedTriangle2D, ...],
    rule: QuadratureRule2D,
) -> AreaConsistencyReport:
    """Return panel/triangle/rule area consistency diagnostics."""

    panel_area = panel_area_from_loops(panel)
    triangle_area = sum(triangle.signed_area for triangle in triangles)
    rule_area = sum(rule.weights)
    return AreaConsistencyReport(
        panel_area=panel_area,
        triangle_area=triangle_area,
        rule_area=rule_area,
        triangle_abs_error=abs(triangle_area - panel_area),
        rule_abs_error=abs(rule_area - panel_area),
    )


def exact_moments_degree2(
    triangles: tuple[SignedTriangle2D, ...],
    *,
    monomials: tuple[tuple[int, int], ...] = MONOMIALS_DEGREE2,
) -> dict[tuple[int, int], float]:
    """Return exact degree <=2 moments from signed triangle formulas."""

    exact: dict[tuple[int, int], float] = {}
    for powers in monomials:
        exact[powers] = sum(
            _triangle_integral_degree2(triangle, powers) for triangle in triangles
        )
    return exact


def approximate_moments(
    rule: QuadratureRule2D,
    *,
    monomials: tuple[tuple[int, int], ...] = MONOMIALS_DEGREE2,
) -> dict[tuple[int, int], float]:
    """Return moments approximated from quadrature nodes and weights."""

    approx: dict[tuple[int, int], float] = {}
    for px, py in monomials:
        accum = 0.0
        for (x, y), weight in zip(rule.points, rule.weights):
            accum += weight * (x**px) * (y**py)
        approx[(px, py)] = accum
    return approx


def moment_report(
    triangles: tuple[SignedTriangle2D, ...],
    rule: QuadratureRule2D,
    *,
    monomials: tuple[tuple[int, int], ...] = MONOMIALS_DEGREE2,
) -> MomentReport:
    """Return moment error report for selected monomials."""

    exact = exact_moments_degree2(triangles, monomials=monomials)
    approx = approximate_moments(rule, monomials=monomials)

    errors = tuple(
        MomentError(
            powers=powers,
            exact=exact[powers],
            approximate=approx[powers],
            abs_error=abs(approx[powers] - exact[powers]),
        )
        for powers in monomials
    )
    return MomentReport(errors=errors)
