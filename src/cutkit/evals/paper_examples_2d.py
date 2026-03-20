"""Reproduction helpers for the 2D examples in Antolin-Wei-Buffa (2022).

This module focuses on Sections 6.1.1, 6.1.2, and 6.2 of
"Robust Numerical Integration on Curved Polyhedra Based on Folded
Decompositions" and adapts them to the current CUTKIT folded-panel API.
"""

from __future__ import annotations

from dataclasses import dataclass
from math import comb, cos, exp, sin, sqrt
from typing import Callable

from cutkit.geometry import PanelLoop2D, Point2D, TrimmedPanel2D
from cutkit.quadrature import folded_quadrature_rule


def _bspline_basis(i: int, degree: int, u: float, knots: tuple[float, ...]) -> float:
    if degree == 0:
        left = knots[i]
        right = knots[i + 1]
        if left <= u < right:
            return 1.0
        if u == knots[-1] and right == knots[-1]:
            return 1.0
        return 0.0

    value = 0.0
    denom_left = knots[i + degree] - knots[i]
    if denom_left > 0.0:
        value += ((u - knots[i]) / denom_left) * _bspline_basis(i, degree - 1, u, knots)

    denom_right = knots[i + degree + 1] - knots[i + 1]
    if denom_right > 0.0:
        value += ((knots[i + degree + 1] - u) / denom_right) * _bspline_basis(
            i + 1, degree - 1, u, knots
        )
    return value


def _eval_quadratic_bspline_curve(u: float) -> Point2D:
    knots = (0.0, 0.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 1.0)
    controls: tuple[Point2D, ...] = (
        (0.0, 0.25),
        (0.25, 0.0),
        (0.5, 0.5),
        (0.9, 0.25),
        (0.8, 0.125),
        (0.75, 0.0),
    )
    degree = 2

    x = 0.0
    y = 0.0
    for i, point in enumerate(controls):
        coeff = _bspline_basis(i, degree, u, knots)
        x += coeff * point[0]
        y += coeff * point[1]
    return (x, y)


def _eval_quarter_circle_rational_bezier(t: float) -> Point2D:
    # Quadratic rational Bezier for a quarter circle arc.
    p0 = (0.0, 0.5)
    p1 = (0.0, 0.0)
    p2 = (0.5, 0.0)
    w0 = 1.0
    w1 = 1.0 / sqrt(2.0)
    w2 = 1.0

    b0 = (1.0 - t) * (1.0 - t)
    b1 = 2.0 * t * (1.0 - t)
    b2 = t * t

    denominator = w0 * b0 + w1 * b1 + w2 * b2
    x = (w0 * b0 * p0[0] + w1 * b1 * p1[0] + w2 * b2 * p2[0]) / denominator
    y = (w0 * b0 * p0[1] + w1 * b1 * p1[1] + w2 * b2 * p2[1]) / denominator
    return (x, y)


def _sample_curve(
    evaluator: Callable[[float], tuple[float, float]],
    *,
    sample_count: int,
) -> tuple[Point2D, ...]:
    if sample_count < 2:
        raise ValueError("sample_count must be at least 2")
    points = []
    for i in range(sample_count + 1):
        t = i / sample_count
        points.append(evaluator(t))
    return tuple(points)


def build_section_6_1_1_bspline_panel(*, sample_count: int = 256) -> TrimmedPanel2D:
    """Build the Section 6.1.1 2D B-rep (quadratic B-spline edge)."""

    curved = _sample_curve(_eval_quadratic_bspline_curve, sample_count=sample_count)
    loop_points = (*curved, (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return TrimmedPanel2D(outer=PanelLoop2D(loop_points))


def build_section_6_1_2_rational_panel(*, sample_count: int = 256) -> TrimmedPanel2D:
    """Build the Section 6.1.2 2D B-rep variant with a quarter-circle edge."""

    curved = _sample_curve(
        _eval_quarter_circle_rational_bezier, sample_count=sample_count
    )
    loop_points = (*curved, (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
    return TrimmedPanel2D(outer=PanelLoop2D(loop_points))


def _bernstein_1d(p: int, i: int, t: float) -> float:
    return comb(p, i) * (t**i) * ((1.0 - t) ** (p - i))


def integrate_tensor_bernstein_basis(
    panel: TrimmedPanel2D,
    *,
    degree: int,
    order: int,
    anchor: Point2D | None,
    require_interior_anchor: bool,
) -> tuple[float, ...]:
    folded = folded_quadrature_rule(
        panel,
        order=order,
        anchor=anchor,
        require_interior_anchor=require_interior_anchor,
    )

    count = degree + 1
    values = [0.0] * (count * count)
    for (x, y), weight in zip(folded.rule.points, folded.rule.weights):
        bx = [_bernstein_1d(degree, i, x) for i in range(count)]
        by = [_bernstein_1d(degree, j, y) for j in range(count)]
        for i in range(count):
            base = i * count
            for j in range(count):
                values[base + j] += weight * bx[i] * by[j]
    return tuple(values)


def _seed_grid(panel: TrimmedPanel2D, *, grid_size: int) -> tuple[Point2D, ...]:
    if grid_size < 2:
        raise ValueError("grid_size must be at least 2")
    xmin, ymin, xmax, ymax = panel.bbox()
    xspan = xmax - xmin
    yspan = ymax - ymin

    seeds: list[Point2D] = []
    for i in range(grid_size):
        for j in range(grid_size):
            x = xmin + i * xspan / (grid_size - 1)
            y = ymin + j * yspan / (grid_size - 1)
            seeds.append((x, y))
    return tuple(seeds)


@dataclass(frozen=True)
class PolynomialDegreeResult:
    degree: int
    orders: tuple[int, ...]
    folded_worst_error: tuple[float, ...]
    jplus_error: tuple[float, ...]


@dataclass(frozen=True)
class PolynomialExperimentResult:
    label: str
    degree_results: tuple[PolynomialDegreeResult, ...]


def run_polynomial_experiment(
    panel: TrimmedPanel2D,
    *,
    label: str,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    reference_order: int = 32,
    seed_grid_size: int = 11,
) -> PolynomialExperimentResult:
    seeds = _seed_grid(panel, grid_size=seed_grid_size)

    degree_results: list[PolynomialDegreeResult] = []
    for degree in degrees:
        reference = integrate_tensor_bernstein_basis(
            panel,
            degree=degree,
            order=reference_order,
            anchor=None,
            require_interior_anchor=True,
        )

        folded_errors: list[float] = []
        jplus_errors: list[float] = []

        for order in orders:
            jplus_values = integrate_tensor_bernstein_basis(
                panel,
                degree=degree,
                order=order,
                anchor=None,
                require_interior_anchor=True,
            )
            jplus_errors.append(
                max(
                    abs(approx - exact)
                    for approx, exact in zip(jplus_values, reference)
                )
            )

            worst_error = 0.0
            for seed in seeds:
                folded_values = integrate_tensor_bernstein_basis(
                    panel,
                    degree=degree,
                    order=order,
                    anchor=seed,
                    require_interior_anchor=False,
                )
                candidate_error = max(
                    abs(approx - exact)
                    for approx, exact in zip(folded_values, reference)
                )
                if candidate_error > worst_error:
                    worst_error = candidate_error
            folded_errors.append(worst_error)

        degree_results.append(
            PolynomialDegreeResult(
                degree=degree,
                orders=orders,
                folded_worst_error=tuple(folded_errors),
                jplus_error=tuple(jplus_errors),
            )
        )

    return PolynomialExperimentResult(label=label, degree_results=tuple(degree_results))


def section_6_2_integrand(x: float, y: float) -> float:
    """2D non-polynomial integrand used in Section 6.2."""

    return exp(y) * sin(x) * cos(y)


@dataclass(frozen=True)
class GeneralFunctionResult:
    orders: tuple[int, ...]
    folded_worst_error: tuple[float, ...]
    jplus_error: tuple[float, ...]


def run_general_function_experiment(
    panel: TrimmedPanel2D,
    *,
    orders: tuple[int, ...],
    reference_order: int = 32,
    seed_grid_size: int = 11,
) -> GeneralFunctionResult:
    reference_rule = folded_quadrature_rule(panel, order=reference_order)
    reference = reference_rule.rule.integrate(section_6_2_integrand)

    seeds = _seed_grid(panel, grid_size=seed_grid_size)
    folded_errors: list[float] = []
    jplus_errors: list[float] = []

    for order in orders:
        jplus = folded_quadrature_rule(panel, order=order)
        jplus_errors.append(
            abs(jplus.rule.integrate(section_6_2_integrand) - reference)
        )

        worst_error = 0.0
        for seed in seeds:
            folded = folded_quadrature_rule(
                panel,
                order=order,
                anchor=seed,
                require_interior_anchor=False,
            )
            candidate_error = abs(
                folded.rule.integrate(section_6_2_integrand) - reference
            )
            if candidate_error > worst_error:
                worst_error = candidate_error
        folded_errors.append(worst_error)

    return GeneralFunctionResult(
        orders=orders,
        folded_worst_error=tuple(folded_errors),
        jplus_error=tuple(jplus_errors),
    )
