"""Near-field template experiments for folded 2D fan pieces."""

from __future__ import annotations

from dataclasses import dataclass
from math import atan2, cos, erf, exp, gamma, hypot, isfinite, log, pi, sin, sqrt
from typing import Callable

from cutkit.geometry import (
    CurveEdge2D,
    CurveLoop2D,
    CurveTrimmedPanel2D,
    PanelLoop2D,
    TrimmedPanel2D,
)
from cutkit.quadrature import folded_curve_quadrature_rule, gauss_legendre_01
from cutkit.topology import select_interior_anchor

Point2D = tuple[float, float]
TemplateDensity2D = Callable[[float, float], float]
_COINCIDENT_TOL = 1.0e-14
_EULER_GAMMA = 0.5772156649015329


def unit_template_density(_r: float, _t: float) -> float:
    """Return the constant template density used by default experiments."""

    return 1.0


def _sub(lhs: Point2D, rhs: Point2D) -> Point2D:
    return (lhs[0] - rhs[0], lhs[1] - rhs[1])


def _dot(lhs: Point2D, rhs: Point2D) -> float:
    return lhs[0] * rhs[0] + lhs[1] * rhs[1]


def _cross(lhs: Point2D, rhs: Point2D) -> float:
    return lhs[0] * rhs[1] - lhs[1] * rhs[0]


def _scale_point(point: Point2D, scale: float) -> Point2D:
    return (scale * point[0], scale * point[1])


@dataclass(frozen=True)
class FanTemplateMap2D:
    """Straight-edge folded fan chart ``T(r, t) = (1-r)V + r C(t)``."""

    vertex: Point2D
    edge_start: Point2D
    edge_end: Point2D

    def point(self, r: float, t: float) -> Point2D:
        """Map ``(r, t)`` in ``[0, 1]^2`` to physical space."""

        one_minus_t = 1.0 - t
        curve_x = one_minus_t * self.edge_start[0] + t * self.edge_end[0]
        curve_y = one_minus_t * self.edge_start[1] + t * self.edge_end[1]
        return (
            (1.0 - r) * self.vertex[0] + r * curve_x,
            (1.0 - r) * self.vertex[1] + r * curve_y,
        )

    @property
    def boundary_det(self) -> float:
        """Return ``det(C(t)-V, C'(t))``, constant for a straight edge."""

        return _cross(
            _sub(self.edge_start, self.vertex),
            _sub(self.edge_end, self.edge_start),
        )

    @property
    def signed_area(self) -> float:
        """Return the oriented physical area of the fan piece."""

        return 0.5 * self.boundary_det

    def signed_jacobian(self, r: float) -> float:
        """Return the signed Jacobian of the ``(r, t)`` fan chart."""

        return r * self.boundary_det

    def local_metric(
        self,
        r: float,
        t: float,
    ) -> tuple[tuple[float, float], tuple[float, float]]:
        """Return ``DT(r,t)^T DT(r,t)`` for the fan chart."""

        radial = _sub(self.point(1.0, t), self.vertex)
        tangent_base = _sub(self.edge_end, self.edge_start)
        tangent = (r * tangent_base[0], r * tangent_base[1])
        return (
            (_dot(radial, radial), _dot(radial, tangent)),
            (_dot(tangent, radial), _dot(tangent, tangent)),
        )

    def scaled(self, factor: float) -> FanTemplateMap2D:
        """Return the same template scaled about the origin."""

        return FanTemplateMap2D(
            vertex=_scale_point(self.vertex, factor),
            edge_start=_scale_point(self.edge_start, factor),
            edge_end=_scale_point(self.edge_end, factor),
        )


@dataclass(frozen=True)
class DiagonalRemainderSample:
    """One mapped-kernel singular split sample near the diagonal."""

    delta: float
    physical_distance: float
    model_distance: float
    laplace_kernel: float
    metric_model_kernel: float
    remainder: float


@dataclass(frozen=True)
class NearfieldTemplateExperiment:
    """Summary of one fan-chart point-target experiment."""

    fan: FanTemplateMap2D
    order: int
    near_point_target: Point2D
    point_target_reference: float
    point_target_low_order: float
    point_target_abs_error: float
    scaled_near_point_target: Point2D
    scaled_point_target_potential: float
    expected_scaled_point_target_potential: float
    scaled_abs_error: float
    signed_area: float
    density_mass: float
    scale_factor: float
    diagonal_remainders: tuple[DiagonalRemainderSample, ...]


@dataclass(frozen=True)
class DmkSplitSample:
    """One quadrature-convergence sample for the DMK-style log-kernel split."""

    fixture: str
    seed_mode: str
    seed: Point2D
    target_label: str
    target: Point2D
    sigma: float
    order: int
    full_value: float
    smooth_value: float
    local_value: float
    analytic_local_value: float
    reconstructed_value: float
    analytic_reconstructed_value: float
    full_reference: float
    smooth_reference: float
    local_reference: float
    full_abs_error: float
    smooth_abs_error: float
    local_abs_error: float
    analytic_local_abs_error: float
    reconstructed_abs_error: float
    analytic_reconstructed_abs_error: float
    local_to_full_ratio: float


@dataclass(frozen=True)
class SeedQualitySample:
    """Geometry quality summary for one folded-panel seed."""

    fixture: str
    seed_mode: str
    seed: Point2D
    min_abs_boundary_det: float
    max_abs_boundary_det: float
    max_to_min_abs_boundary_det: float
    min_edge_distance: float
    max_edge_distance: float
    max_to_min_edge_distance: float


@dataclass(frozen=True)
class DmkSplitExperimentReport:
    """Report payload for the DMK-style folded near-field split experiment."""

    reference_order: int
    orders: tuple[int, ...]
    sigmas: tuple[float, ...]
    seed_quality: tuple[SeedQualitySample, ...]
    samples: tuple[DmkSplitSample, ...]


@dataclass(frozen=True)
class CurvedBoundaryLocalModelSample:
    """Practical local-model check on one curved CAD-style cut cell."""

    sigma: float
    order: int
    reference_order: int
    target: Point2D
    folded_value: float
    reference_value: float
    curved_boundary_value: float
    half_plane_value: float
    full_plane_value: float
    folded_abs_error: float
    curved_boundary_abs_error: float
    half_plane_abs_error: float
    full_plane_abs_error: float
    curved_boundary_rel_error: float
    half_plane_rel_error: float
    full_plane_rel_error: float


@dataclass(frozen=True)
class CurvedBoundaryLocalModelReport:
    """Report for local residual models on an exact curved cut cell."""

    sigmas: tuple[float, ...]
    orders: tuple[int, ...]
    reference_order: int
    samples: tuple[CurvedBoundaryLocalModelSample, ...]


@dataclass(frozen=True)
class TaylorBoundaryModelSample:
    """One high-order Taylor boundary model sample for a smooth trim."""

    sigma: float
    boundary_order: int
    exact_value: float
    taylor_value: float
    abs_error: float
    rel_error: float


@dataclass(frozen=True)
class TaylorBoundaryModelReport:
    """Convergence report for high-order smooth-boundary Taylor models."""

    sigmas: tuple[float, ...]
    boundary_orders: tuple[int, ...]
    angular_order: int
    samples: tuple[TaylorBoundaryModelSample, ...]


@dataclass(frozen=True)
class GraphBoundaryModelSample:
    """One graph-strip smooth-boundary model sample."""

    sigma: float
    boundary_order: int
    strip_order: int
    exact_value: float
    graph_value: float
    abs_error: float
    rel_error: float


@dataclass(frozen=True)
class GraphBoundaryModelReport:
    """Convergence report for graph-strip boundary corrections."""

    sigmas: tuple[float, ...]
    boundary_orders: tuple[int, ...]
    strip_orders: tuple[int, ...]
    angular_order: int
    samples: tuple[GraphBoundaryModelSample, ...]


@dataclass(frozen=True)
class PrecomputedBoundaryTableSample:
    """One interpolated precomputed boundary-table sample."""

    sigma: float
    exact_value: float
    table_value: float
    abs_error: float
    rel_error: float


@dataclass(frozen=True)
class PrecomputedBoundaryTableReport:
    """Report for interpolation over precomputed smooth-boundary moments."""

    table_sigmas: tuple[float, ...]
    eval_sigmas: tuple[float, ...]
    boundary_order: int
    angular_order: int
    samples: tuple[PrecomputedBoundaryTableSample, ...]


def laplace_log_kernel(target: Point2D, source: Point2D) -> float:
    """Return the 2D Laplace fundamental solution ``-log(|x-y|)/(2*pi)``."""

    distance = hypot(target[0] - source[0], target[1] - source[1])
    if distance <= 0.0:
        raise ValueError("Laplace log kernel is singular at coincident points")
    return -log(distance) / (2.0 * pi)


def exponential_integral_e1(x: float, *, tol: float = 1.0e-15) -> float:
    """Return ``E1(x) = integral_x^inf exp(-t)/t dt`` for ``x > 0``.

    This small stdlib-only evaluator is intended for experiment-scale kernel
    splitting, not as a general special-functions package.
    """

    if x <= 0.0 or not isfinite(x):
        raise ValueError("x must be positive and finite")

    if x <= 4.0:
        term_power = 1.0
        factorial = 1.0
        series = 0.0
        for k in range(1, 256):
            term_power *= -x
            factorial *= k
            term = term_power / (k * factorial)
            series += term
            if abs(term) <= tol * max(1.0, abs(series)):
                break
        return -_EULER_GAMMA - log(x) - series

    term = 1.0
    series = 1.0
    previous_abs = abs(term)
    for k in range(1, 256):
        term *= -k / x
        current_abs = abs(term)
        if current_abs > previous_abs:
            break
        series += term
        if current_abs <= tol * max(1.0, abs(series)):
            break
        previous_abs = current_abs
    return exp(-x) * series / x


def ewald_log_local_kernel(target: Point2D, source: Point2D, *, sigma: float) -> float:
    """Return the localized 2D log Ewald residual ``E1(r^2/sigma^2)/(4*pi)``."""

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    distance = hypot(target[0] - source[0], target[1] - source[1])
    if distance <= 0.0:
        raise ValueError("local log kernel is singular at coincident points")
    return exponential_integral_e1((distance / sigma) ** 2) / (4.0 * pi)


def ewald_log_smooth_kernel(target: Point2D, source: Point2D, *, sigma: float) -> float:
    """Return the smooth complement of the localized 2D log Ewald residual."""

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    distance = hypot(target[0] - source[0], target[1] - source[1])
    if distance <= _COINCIDENT_TOL:
        return (_EULER_GAMMA - 2.0 * log(sigma)) / (4.0 * pi)
    return laplace_log_kernel(target, source) - ewald_log_local_kernel(
        target,
        source,
        sigma=sigma,
    )


def ewald_log_local_radial_moment_2d(*, sigma: float, monomial_degree: int) -> float:
    """Return ``int_0^inf K_sigma(r) r^(monomial_degree + 1) dr``.

    Here ``K_sigma(r) = E1(r^2/sigma^2)/(4*pi)`` is the localized 2D log
    residual. Multiplying this radial moment by the corresponding angular
    monomial moment gives sector moments for full-plane, half-plane, and wedge
    local models.
    """

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    if monomial_degree < 0:
        raise ValueError("monomial_degree must be nonnegative")

    half_degree = 0.5 * monomial_degree
    return (
        sigma ** (monomial_degree + 2)
        * gamma(half_degree + 1.0)
        / (8.0 * pi * (half_degree + 1.0))
    )


def ewald_log_local_sector_monomial_moment_2d(
    *,
    sigma: float,
    x_power: int,
    y_power: int,
    theta_start: float,
    theta_end: float,
    angular_order: int = 96,
) -> float:
    """Return a 2D local residual monomial moment over an angular sector.

    The sector has vertex at the target and angle range ``[theta_start,
    theta_end]``. This is the leading straight-feature model for full-plane,
    half-plane, and wedge residual corrections.
    """

    if x_power < 0 or y_power < 0:
        raise ValueError("monomial powers must be nonnegative")
    if angular_order < 1:
        raise ValueError("angular_order must be positive")
    if theta_end < theta_start:
        raise ValueError("theta_end must be at least theta_start")

    radial = ewald_log_local_radial_moment_2d(
        sigma=sigma,
        monomial_degree=x_power + y_power,
    )
    if theta_end == theta_start:
        return 0.0

    nodes, weights = gauss_legendre_01(angular_order)
    width = theta_end - theta_start
    angular = 0.0
    for node, weight in zip(nodes, weights, strict=True):
        theta = theta_start + width * node
        angular += weight * width * (cos(theta) ** x_power) * (sin(theta) ** y_power)
    return radial * angular


def metric_model_distance(
    fan: FanTemplateMap2D,
    *,
    r: float,
    t: float,
    delta_r: float,
    delta_t: float,
) -> float:
    """Return the local metric distance for a template-space displacement."""

    metric = fan.local_metric(r, t)
    distance_squared = (
        metric[0][0] * delta_r * delta_r
        + 2.0 * metric[0][1] * delta_r * delta_t
        + metric[1][1] * delta_t * delta_t
    )
    if distance_squared <= 0.0:
        raise ValueError("metric model distance must be positive")
    return sqrt(distance_squared)


def template_density_mass(
    fan: FanTemplateMap2D,
    *,
    order: int,
    density: TemplateDensity2D | None = None,
) -> float:
    """Return ``integral density(r,t) * J(r,t) dr dt`` on one fan chart."""

    if order < 1:
        raise ValueError("order must be positive")
    if density is None:
        density = unit_template_density

    nodes, weights = gauss_legendre_01(order)
    total = 0.0
    for r, wr in zip(nodes, weights, strict=True):
        jacobian = fan.signed_jacobian(r)
        for t, wt in zip(nodes, weights, strict=True):
            total += density(r, t) * jacobian * wr * wt
    return total


def point_target_laplace_potential(
    fan: FanTemplateMap2D,
    target: Point2D,
    *,
    order: int,
    source_density: TemplateDensity2D | None = None,
) -> float:
    """Approximate a folded-piece source integral at one point target."""

    if order < 1:
        raise ValueError("order must be positive")
    if source_density is None:
        source_density = unit_template_density

    nodes, weights = gauss_legendre_01(order)
    total = 0.0
    for r, wr in zip(nodes, weights, strict=True):
        jacobian = fan.signed_jacobian(r)
        for t, wt in zip(nodes, weights, strict=True):
            source = fan.point(r, t)
            if hypot(target[0] - source[0], target[1] - source[1]) <= _COINCIDENT_TOL:
                raise ValueError(
                    "point target coincides with a source quadrature node; "
                    "use a singular point-target reference rule"
                )
            total += (
                laplace_log_kernel(target, source)
                * source_density(r, t)
                * jacobian
                * wr
                * wt
            )
    return total


def point_target_smooth_ewald_potential(
    fan: FanTemplateMap2D,
    target: Point2D,
    *,
    order: int,
    sigma: float,
    source_density: TemplateDensity2D | None = None,
) -> float:
    """Approximate the smoothed 2D log-kernel source integral at one target."""

    if order < 1:
        raise ValueError("order must be positive")
    if source_density is None:
        source_density = unit_template_density

    nodes, weights = gauss_legendre_01(order)
    total = 0.0
    for r, wr in zip(nodes, weights, strict=True):
        jacobian = fan.signed_jacobian(r)
        for t, wt in zip(nodes, weights, strict=True):
            source = fan.point(r, t)
            total += (
                ewald_log_smooth_kernel(target, source, sigma=sigma)
                * source_density(r, t)
                * jacobian
                * wr
                * wt
            )
    return total


def _edge_distance(point: Point2D, start: Point2D, end: Point2D) -> float:
    edge = _sub(end, start)
    length_sq = _dot(edge, edge)
    if length_sq <= 0.0:
        return hypot(point[0] - start[0], point[1] - start[1])
    rel = _sub(point, start)
    tau = max(0.0, min(1.0, _dot(rel, edge) / length_sq))
    closest = (start[0] + tau * edge[0], start[1] + tau * edge[1])
    return hypot(point[0] - closest[0], point[1] - closest[1])


def _node_barycenter(nodes: tuple[Point2D, ...]) -> Point2D:
    scale = 1.0 / len(nodes)
    return (
        scale * sum(point[0] for point in nodes),
        scale * sum(point[1] for point in nodes),
    )


def _panel_fans(
    nodes: tuple[Point2D, ...], *, seed: Point2D
) -> tuple[FanTemplateMap2D, ...]:
    return tuple(
        FanTemplateMap2D(
            vertex=seed,
            edge_start=nodes[index],
            edge_end=nodes[(index + 1) % len(nodes)],
        )
        for index in range(len(nodes))
    )


def _panel_seed_quality(
    *,
    fixture: str,
    seed_mode: str,
    nodes: tuple[Point2D, ...],
    seed: Point2D,
) -> SeedQualitySample:
    fans = _panel_fans(nodes, seed=seed)
    dets = tuple(abs(fan.boundary_det) for fan in fans)
    distances = tuple(
        _edge_distance(seed, nodes[index], nodes[(index + 1) % len(nodes)])
        for index in range(len(nodes))
    )
    min_det = min(dets)
    min_distance = min(distances)
    max_det = max(dets)
    max_distance = max(distances)
    return SeedQualitySample(
        fixture=fixture,
        seed_mode=seed_mode,
        seed=seed,
        min_abs_boundary_det=min_det,
        max_abs_boundary_det=max_det,
        max_to_min_abs_boundary_det=max_det / min_det
        if min_det > 0.0
        else float("inf"),
        min_edge_distance=min_distance,
        max_edge_distance=max_distance,
        max_to_min_edge_distance=(
            max_distance / min_distance if min_distance > 0.0 else float("inf")
        ),
    )


def _physical_density(point: Point2D) -> float:
    return 1.0 + 0.25 * point[0] - 0.15 * point[1] + 0.1 * point[0] * point[1]


def _rational_quarter_circle_edge() -> CurveEdge2D:
    """Return the exact rational quadratic arc used as a curved cut trim."""

    p0 = (0.0, 0.5)
    p1 = (0.0, 0.0)
    p2 = (0.5, 0.0)
    w0 = 1.0
    w1 = 1.0 / sqrt(2.0)
    w2 = 1.0

    def basis(t: float) -> tuple[float, float, float]:
        one_minus_t = 1.0 - t
        return (one_minus_t * one_minus_t, 2.0 * one_minus_t * t, t * t)

    def basis_derivative(t: float) -> tuple[float, float, float]:
        return (-2.0 * (1.0 - t), 2.0 - 4.0 * t, 2.0 * t)

    def weighted_sum(t: float) -> tuple[float, float, float]:
        b0, b1, b2 = basis(t)
        denominator = w0 * b0 + w1 * b1 + w2 * b2
        numerator_x = w0 * b0 * p0[0] + w1 * b1 * p1[0] + w2 * b2 * p2[0]
        numerator_y = w0 * b0 * p0[1] + w1 * b1 * p1[1] + w2 * b2 * p2[1]
        return numerator_x, numerator_y, denominator

    def weighted_sum_derivative(t: float) -> tuple[float, float, float]:
        db0, db1, db2 = basis_derivative(t)
        denominator_derivative = w0 * db0 + w1 * db1 + w2 * db2
        numerator_x_derivative = w0 * db0 * p0[0] + w1 * db1 * p1[0] + w2 * db2 * p2[0]
        numerator_y_derivative = w0 * db0 * p0[1] + w1 * db1 * p1[1] + w2 * db2 * p2[1]
        return numerator_x_derivative, numerator_y_derivative, denominator_derivative

    def point(t: float) -> Point2D:
        numerator_x, numerator_y, denominator = weighted_sum(t)
        return (numerator_x / denominator, numerator_y / denominator)

    def tangent(t: float) -> Point2D:
        numerator_x, numerator_y, denominator = weighted_sum(t)
        dx_num, dy_num, denominator_derivative = weighted_sum_derivative(t)
        denominator_sq = denominator * denominator
        return (
            (dx_num * denominator - numerator_x * denominator_derivative)
            / denominator_sq,
            (dy_num * denominator - numerator_y * denominator_derivative)
            / denominator_sq,
        )

    return CurveEdge2D(evaluator=point, derivative=tangent)


def _rational_quarter_circle_cut_cell() -> CurveTrimmedPanel2D:
    """Return a curved CAD-style cut cell with one rational trim edge."""

    curved = _rational_quarter_circle_edge()
    p0 = curved.point(0.0)
    p1 = curved.point(1.0)
    cell_corner = (0.5, 0.5)
    loop = CurveLoop2D(
        (
            curved,
            CurveEdge2D.line(p1, cell_corner),
            CurveEdge2D.line(cell_corner, p0),
        )
    )
    return CurveTrimmedPanel2D(outer=loop)


def _curve_panel_local_residual(
    panel: CurveTrimmedPanel2D,
    target: Point2D,
    *,
    sigma: float,
    order: int,
) -> float:
    if order < 1:
        raise ValueError("order must be positive")
    if sigma <= 0.0:
        raise ValueError("sigma must be positive")

    folded = folded_curve_quadrature_rule(panel, order=order)
    total = 0.0
    for source, weight in zip(folded.rule.points, folded.rule.weights, strict=True):
        total += (
            ewald_log_local_kernel(target, source, sigma=sigma)
            * _physical_density(source)
            * weight
        )
    return total


def _quarter_circle_ray_exit_distance(target: Point2D, direction: Point2D) -> float:
    """Return ray exit length for the exact rational quarter-circle cut cell."""

    center = (0.5, 0.5)
    rel = _sub(target, center)
    circle_dot = _dot(rel, direction)
    if circle_dot >= 0.0:
        return 0.0

    exit_distance = -2.0 * circle_dot
    dx, dy = direction
    if dx > 0.0:
        exit_distance = min(exit_distance, (0.5 - target[0]) / dx)
    if dy > 0.0:
        exit_distance = min(exit_distance, (0.5 - target[1]) / dy)
    return max(0.0, exit_distance)


def _quarter_circle_exact_boundary_local_residual(
    target: Point2D,
    *,
    sigma: float,
    angular_order: int,
) -> float:
    """Integrate the local residual using exact target-centered ray clipping."""

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    if angular_order < 1:
        raise ValueError("angular_order must be positive")

    p0 = (0.0, 0.5)
    p1 = (0.5, 0.0)
    center = (0.5, 0.5)
    tangent_low = -0.25 * pi
    tangent_high = 0.75 * pi
    intervals = (
        (
            tangent_low,
            atan2(p1[1] - target[1], p1[0] - target[0]),
            "circle_start",
        ),
        (
            atan2(p1[1] - target[1], p1[0] - target[0]),
            atan2(center[1] - target[1], center[0] - target[0]),
            "right",
        ),
        (
            atan2(center[1] - target[1], center[0] - target[0]),
            atan2(p0[1] - target[1], p0[0] - target[0]),
            "top",
        ),
        (
            atan2(p0[1] - target[1], p0[0] - target[0]),
            tangent_high,
            "circle_end",
        ),
    )
    total = 0.0
    for theta_start, theta_end, exit_kind in intervals:

        def integrand(theta: float, *, kind: str = exit_kind) -> float:
            return _quarter_circle_ray_integrand(
                target,
                theta,
                sigma=sigma,
                exit_kind=kind,
            )

        total += _adaptive_simpson(
            integrand,
            theta_start,
            theta_end,
            abs_tol=1.0e-16,
            max_depth=max(20, angular_order),
        )
    return total


def _quarter_circle_ray_integrand(
    target: Point2D,
    theta: float,
    *,
    sigma: float,
    exit_kind: str,
) -> float:
    direction = (cos(theta), sin(theta))
    if exit_kind in ("circle_start", "circle_end"):
        exit_distance = _quarter_circle_ray_exit_distance(target, direction)
    elif exit_kind == "right":
        exit_distance = (0.5 - target[0]) / direction[0]
    else:
        exit_distance = (0.5 - target[1]) / direction[1]
    if exit_distance <= 0.0:
        return 0.0
    density_constant = _physical_density(target)
    density_linear = (
        0.25 * direction[0]
        - 0.15 * direction[1]
        + 0.1 * (target[0] * direction[1] + target[1] * direction[0])
    )
    density_quadratic = 0.1 * direction[0] * direction[1]
    return (
        density_constant
        * _ewald_log_local_finite_radial_moment_2d(
            sigma=sigma,
            monomial_degree=0,
            radius=exit_distance,
        )
        + density_linear
        * _ewald_log_local_finite_radial_moment_2d(
            sigma=sigma,
            monomial_degree=1,
            radius=exit_distance,
        )
        + density_quadratic
        * _ewald_log_local_finite_radial_moment_2d(
            sigma=sigma,
            monomial_degree=2,
            radius=exit_distance,
        )
    )


def _adaptive_simpson(
    function: Callable[[float], float],
    start: float,
    end: float,
    *,
    abs_tol: float,
    max_depth: int,
) -> float:
    midpoint = 0.5 * (start + end)
    f_start = function(start)
    f_mid = function(midpoint)
    f_end = function(end)
    whole = _simpson_estimate(start, end, f_start, f_mid, f_end)
    return _adaptive_simpson_recursive(
        function,
        start,
        midpoint,
        end,
        f_start,
        f_mid,
        f_end,
        whole,
        abs_tol,
        max_depth,
    )


def _simpson_estimate(
    start: float,
    end: float,
    f_start: float,
    f_mid: float,
    f_end: float,
) -> float:
    return (end - start) * (f_start + 4.0 * f_mid + f_end) / 6.0


def _adaptive_simpson_recursive(
    function: Callable[[float], float],
    start: float,
    midpoint: float,
    end: float,
    f_start: float,
    f_mid: float,
    f_end: float,
    whole: float,
    abs_tol: float,
    depth_remaining: int,
) -> float:
    left_mid = 0.5 * (start + midpoint)
    right_mid = 0.5 * (midpoint + end)
    f_left_mid = function(left_mid)
    f_right_mid = function(right_mid)
    left = _simpson_estimate(start, midpoint, f_start, f_left_mid, f_mid)
    right = _simpson_estimate(midpoint, end, f_mid, f_right_mid, f_end)
    delta = left + right - whole
    if depth_remaining <= 0 or abs(delta) <= 15.0 * abs_tol:
        return left + right + delta / 15.0
    return _adaptive_simpson_recursive(
        function,
        start,
        left_mid,
        midpoint,
        f_start,
        f_left_mid,
        f_mid,
        left,
        0.5 * abs_tol,
        depth_remaining - 1,
    ) + _adaptive_simpson_recursive(
        function,
        midpoint,
        right_mid,
        end,
        f_mid,
        f_right_mid,
        f_end,
        right,
        0.5 * abs_tol,
        depth_remaining - 1,
    )


def _ewald_log_local_finite_radial_moment_2d(
    *,
    sigma: float,
    monomial_degree: int,
    radius: float,
) -> float:
    """Return ``int_0^radius K_sigma(r) r^(monomial_degree + 1) dr``."""

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    if radius <= 0.0:
        return 0.0
    if monomial_degree not in (0, 1, 2):
        raise ValueError("finite radial moment supports degrees 0, 1, and 2")

    upper = (radius / sigma) ** 2
    sqrt_upper = sqrt(upper)
    exp_upper = exp(-upper) if upper < 745.0 else 0.0
    e1_upper = exponential_integral_e1(upper)
    if monomial_degree == 0:
        lower_gamma = 1.0 - exp_upper
        q_plus_one = 1.0
    elif monomial_degree == 1:
        lower_gamma = 0.5 * sqrt(pi) * erf(sqrt_upper) - sqrt_upper * exp_upper
        q_plus_one = 1.5
    else:
        lower_gamma = 1.0 - exp_upper * (1.0 + upper)
        q_plus_one = 2.0

    integral_u = (upper**q_plus_one * e1_upper + lower_gamma) / q_plus_one
    return sigma ** (monomial_degree + 2) * integral_u / (8.0 * pi)


def _quarter_circle_boundary_frame() -> tuple[Point2D, Point2D, Point2D, float]:
    panel = _rational_quarter_circle_cut_cell()
    target = panel.outer.edges[0].point(0.5)
    inv_sqrt2 = 1.0 / sqrt(2.0)
    tangent = (inv_sqrt2, -inv_sqrt2)
    inward_normal = (inv_sqrt2, inv_sqrt2)
    return target, tangent, inward_normal, 0.5


def _quarter_circle_taylor_graph_coefficients(
    *, radius: float, boundary_order: int
) -> tuple[float, ...]:
    if boundary_order < 2 or boundary_order % 2 != 0:
        raise ValueError("boundary_order must be a positive even order at least 2")

    coefficients: list[float] = []
    binomial = 1.0
    for power in range(1, boundary_order // 2 + 1):
        binomial *= (1.5 - float(power)) / float(power)
        coefficient = -binomial * ((-1.0) ** power) / (radius ** (2 * power - 1))
        coefficients.append(coefficient)
    return tuple(coefficients)


def _quarter_circle_taylor_graph_value(
    s_coord: float,
    *,
    coefficients: tuple[float, ...],
) -> float:
    value = 0.0
    s_squared = s_coord * s_coord
    power = s_squared
    for coefficient in coefficients:
        value += coefficient * power
        power *= s_squared
    return value


def _taylor_graph_exit_distance(
    theta: float,
    *,
    coefficients: tuple[float, ...],
    sigma: float,
) -> float | None:
    cos_theta = cos(theta)
    sin_theta = sin(theta)
    if sin_theta <= 0.0:
        return 0.0
    if abs(cos_theta) <= 1.0e-14:
        return None

    def boundary_residual(radius: float) -> float:
        return radius * sin_theta - _quarter_circle_taylor_graph_value(
            radius * cos_theta,
            coefficients=coefficients,
        )

    low = 0.0
    high = max(sigma, 1.0e-3)
    while boundary_residual(high) > 0.0:
        high *= 2.0
        if high > 8.0:
            return None

    for _ in range(96):
        mid = 0.5 * (low + high)
        if boundary_residual(mid) > 0.0:
            low = mid
        else:
            high = mid
    return high


def _local_boundary_ray_integral(
    target: Point2D,
    direction: Point2D,
    *,
    sigma: float,
    exit_distance: float | None,
) -> float:
    density_constant = _physical_density(target)
    density_linear = (
        0.25 * direction[0]
        - 0.15 * direction[1]
        + 0.1 * (target[0] * direction[1] + target[1] * direction[0])
    )
    density_quadratic = 0.1 * direction[0] * direction[1]

    def radial_moment(degree: int) -> float:
        if exit_distance is None:
            return ewald_log_local_radial_moment_2d(
                sigma=sigma,
                monomial_degree=degree,
            )
        return _ewald_log_local_finite_radial_moment_2d(
            sigma=sigma,
            monomial_degree=degree,
            radius=exit_distance,
        )

    return (
        density_constant * radial_moment(0)
        + density_linear * radial_moment(1)
        + density_quadratic * radial_moment(2)
    )


def _quarter_circle_exact_local_boundary_model(
    *, sigma: float, angular_order: int
) -> float:
    target, tangent, inward_normal, radius = _quarter_circle_boundary_frame()
    if angular_order < 1:
        raise ValueError("angular_order must be positive")

    def integrand(theta: float) -> float:
        direction = (
            cos(theta) * tangent[0] + sin(theta) * inward_normal[0],
            cos(theta) * tangent[1] + sin(theta) * inward_normal[1],
        )
        exit_distance = 2.0 * radius * sin(theta)
        return _local_boundary_ray_integral(
            target,
            direction,
            sigma=sigma,
            exit_distance=exit_distance,
        )

    return _adaptive_simpson(
        integrand,
        0.0,
        pi,
        abs_tol=1.0e-16,
        max_depth=max(20, angular_order),
    )


def _quarter_circle_taylor_boundary_model(
    *, sigma: float, boundary_order: int, angular_order: int
) -> float:
    target, tangent, inward_normal, radius = _quarter_circle_boundary_frame()
    coefficients = _quarter_circle_taylor_graph_coefficients(
        radius=radius,
        boundary_order=boundary_order,
    )

    def integrand(theta: float) -> float:
        direction = (
            cos(theta) * tangent[0] + sin(theta) * inward_normal[0],
            cos(theta) * tangent[1] + sin(theta) * inward_normal[1],
        )
        exit_distance = _taylor_graph_exit_distance(
            theta,
            coefficients=coefficients,
            sigma=sigma,
        )
        return _local_boundary_ray_integral(
            target,
            direction,
            sigma=sigma,
            exit_distance=exit_distance,
        )

    return _adaptive_simpson(
        integrand,
        0.0,
        pi,
        abs_tol=1.0e-16,
        max_depth=max(20, angular_order),
    )


def run_taylor_boundary_model_experiment(
    *,
    sigmas: tuple[float, ...] = (0.01, 0.02),
    boundary_orders: tuple[int, ...] = (2, 4, 6, 8, 10, 12),
    angular_order: int = 32,
) -> TaylorBoundaryModelReport:
    """Compare high-order local boundary Taylor models to exact circular geometry."""

    samples: list[TaylorBoundaryModelSample] = []
    for sigma in sigmas:
        exact_value = _quarter_circle_exact_local_boundary_model(
            sigma=sigma,
            angular_order=angular_order,
        )
        denominator = max(abs(exact_value), 1.0e-300)
        for boundary_order in boundary_orders:
            taylor_value = _quarter_circle_taylor_boundary_model(
                sigma=sigma,
                boundary_order=boundary_order,
                angular_order=angular_order,
            )
            abs_error = abs(taylor_value - exact_value)
            samples.append(
                TaylorBoundaryModelSample(
                    sigma=sigma,
                    boundary_order=boundary_order,
                    exact_value=exact_value,
                    taylor_value=taylor_value,
                    abs_error=abs_error,
                    rel_error=abs_error / denominator,
                )
            )
    return TaylorBoundaryModelReport(
        sigmas=sigmas,
        boundary_orders=boundary_orders,
        angular_order=angular_order,
        samples=tuple(samples),
    )


def _local_half_plane_boundary_model(*, sigma: float, angular_order: int) -> float:
    target, tangent, inward_normal, _radius = _quarter_circle_boundary_frame()

    def integrand(theta: float) -> float:
        direction = (
            cos(theta) * tangent[0] + sin(theta) * inward_normal[0],
            cos(theta) * tangent[1] + sin(theta) * inward_normal[1],
        )
        return _local_boundary_ray_integral(
            target,
            direction,
            sigma=sigma,
            exit_distance=None,
        )

    return _adaptive_simpson(
        integrand,
        0.0,
        pi,
        abs_tol=1.0e-16,
        max_depth=max(20, angular_order),
    )


def _graph_strip_correction(
    *,
    sigma: float,
    boundary_order: int,
    strip_order: int,
) -> float:
    target, tangent, inward_normal, radius = _quarter_circle_boundary_frame()
    coefficients = _quarter_circle_taylor_graph_coefficients(
        radius=radius,
        boundary_order=boundary_order,
    )
    nodes, weights = gauss_legendre_01(strip_order)
    total = 0.0
    for s_node, s_weight in zip(nodes, weights, strict=True):
        s_coord = radius * (2.0 * s_node - 1.0)
        ds_weight = 2.0 * radius * s_weight
        graph_height = _quarter_circle_taylor_graph_value(
            s_coord,
            coefficients=coefficients,
        )
        if graph_height <= 0.0:
            continue
        for n_node, n_weight in zip(nodes, weights, strict=True):
            n_coord = graph_height * n_node
            source = (
                target[0] + s_coord * tangent[0] + n_coord * inward_normal[0],
                target[1] + s_coord * tangent[1] + n_coord * inward_normal[1],
            )
            if hypot(source[0] - target[0], source[1] - target[1]) <= _COINCIDENT_TOL:
                continue
            total += (
                ewald_log_local_kernel(target, source, sigma=sigma)
                * _physical_density(source)
                * ds_weight
                * graph_height
                * n_weight
            )
    return total


def _quarter_circle_graph_boundary_model(
    *,
    sigma: float,
    boundary_order: int,
    strip_order: int,
    angular_order: int,
) -> float:
    return _local_half_plane_boundary_model(
        sigma=sigma,
        angular_order=angular_order,
    ) - _graph_strip_correction(
        sigma=sigma,
        boundary_order=boundary_order,
        strip_order=strip_order,
    )


def run_graph_boundary_model_experiment(
    *,
    sigmas: tuple[float, ...] = (0.005, 0.01, 0.02),
    boundary_orders: tuple[int, ...] = (4, 6, 8),
    strip_orders: tuple[int, ...] = (32, 64, 96),
    angular_order: int = 32,
) -> GraphBoundaryModelReport:
    """Compare graph-strip boundary corrections against exact circular geometry."""

    samples: list[GraphBoundaryModelSample] = []
    for sigma in sigmas:
        exact_value = _quarter_circle_exact_local_boundary_model(
            sigma=sigma,
            angular_order=angular_order,
        )
        denominator = max(abs(exact_value), 1.0e-300)
        for boundary_order in boundary_orders:
            for strip_order in strip_orders:
                graph_value = _quarter_circle_graph_boundary_model(
                    sigma=sigma,
                    boundary_order=boundary_order,
                    strip_order=strip_order,
                    angular_order=angular_order,
                )
                abs_error = abs(graph_value - exact_value)
                samples.append(
                    GraphBoundaryModelSample(
                        sigma=sigma,
                        boundary_order=boundary_order,
                        strip_order=strip_order,
                        exact_value=exact_value,
                        graph_value=graph_value,
                        abs_error=abs_error,
                        rel_error=abs_error / denominator,
                    )
                )
    return GraphBoundaryModelReport(
        sigmas=sigmas,
        boundary_orders=boundary_orders,
        strip_orders=strip_orders,
        angular_order=angular_order,
        samples=tuple(samples),
    )


def _lagrange_interpolate(
    nodes: tuple[float, ...], values: tuple[float, ...], point: float
) -> float:
    if len(nodes) != len(values):
        raise ValueError("nodes and values must have the same length")
    total = 0.0
    for i, node_i in enumerate(nodes):
        basis = 1.0
        for j, node_j in enumerate(nodes):
            if i == j:
                continue
            basis *= (point - node_j) / (node_i - node_j)
        total += values[i] * basis
    return total


def run_precomputed_boundary_table_experiment(
    *,
    table_sigmas: tuple[float, ...] = (
        0.004,
        0.008,
        0.012,
        0.016,
        0.020,
        0.024,
        0.028,
    ),
    eval_sigmas: tuple[float, ...] = (0.010, 0.018, 0.026),
    boundary_order: int = 8,
    angular_order: int = 32,
) -> PrecomputedBoundaryTableReport:
    """Interpolate precomputed high-order smooth-boundary moment values."""

    table_values = tuple(
        _quarter_circle_taylor_boundary_model(
            sigma=sigma,
            boundary_order=boundary_order,
            angular_order=angular_order,
        )
        for sigma in table_sigmas
    )
    samples: list[PrecomputedBoundaryTableSample] = []
    for sigma in eval_sigmas:
        exact_value = _quarter_circle_taylor_boundary_model(
            sigma=sigma,
            boundary_order=boundary_order,
            angular_order=angular_order,
        )
        table_value = _lagrange_interpolate(table_sigmas, table_values, sigma)
        abs_error = abs(table_value - exact_value)
        samples.append(
            PrecomputedBoundaryTableSample(
                sigma=sigma,
                exact_value=exact_value,
                table_value=table_value,
                abs_error=abs_error,
                rel_error=abs_error / max(abs(exact_value), 1.0e-300),
            )
        )
    return PrecomputedBoundaryTableReport(
        table_sigmas=table_sigmas,
        eval_sigmas=eval_sigmas,
        boundary_order=boundary_order,
        angular_order=angular_order,
        samples=tuple(samples),
    )


def run_curved_boundary_local_model_experiment(
    *,
    sigmas: tuple[float, ...] = (0.02, 0.04, 0.08),
    orders: tuple[int, ...] = (12, 20, 32),
    reference_order: int = 96,
) -> CurvedBoundaryLocalModelReport:
    """Test local residual models on an exact curved rational cut cell."""

    panel = _rational_quarter_circle_cut_cell()
    trim = panel.outer.edges[0]
    target = trim.point(0.5)

    samples: list[CurvedBoundaryLocalModelSample] = []
    for sigma in sigmas:
        reference = _curve_panel_local_residual(
            panel,
            target,
            sigma=sigma,
            order=reference_order,
        )
        curved_boundary = _quarter_circle_exact_boundary_local_residual(
            target,
            sigma=sigma,
            angular_order=reference_order,
        )
        density_at_target = _physical_density(target)
        half_plane = (
            ewald_log_local_sector_monomial_moment_2d(
                sigma=sigma,
                x_power=0,
                y_power=0,
                theta_start=0.0,
                theta_end=pi,
            )
            * density_at_target
        )
        full_plane = (
            ewald_log_local_sector_monomial_moment_2d(
                sigma=sigma,
                x_power=0,
                y_power=0,
                theta_start=0.0,
                theta_end=2.0 * pi,
            )
            * density_at_target
        )
        denominator = max(abs(reference), 1.0e-300)
        for order in orders:
            folded_value = _curve_panel_local_residual(
                panel,
                target,
                sigma=sigma,
                order=order,
            )
            folded_error = abs(folded_value - reference)
            curved_error = abs(curved_boundary - reference)
            half_error = abs(half_plane - reference)
            full_error = abs(full_plane - reference)
            samples.append(
                CurvedBoundaryLocalModelSample(
                    sigma=sigma,
                    order=order,
                    reference_order=reference_order,
                    target=target,
                    folded_value=folded_value,
                    reference_value=reference,
                    curved_boundary_value=curved_boundary,
                    half_plane_value=half_plane,
                    full_plane_value=full_plane,
                    folded_abs_error=folded_error,
                    curved_boundary_abs_error=curved_error,
                    half_plane_abs_error=half_error,
                    full_plane_abs_error=full_error,
                    curved_boundary_rel_error=curved_error / denominator,
                    half_plane_rel_error=half_error / denominator,
                    full_plane_rel_error=full_error / denominator,
                )
            )

    return CurvedBoundaryLocalModelReport(
        sigmas=sigmas,
        orders=orders,
        reference_order=reference_order,
        samples=tuple(samples),
    )


def _analytic_full_space_local_residual(target: Point2D, *, sigma: float) -> float:
    """Return the leading full-space Taylor moment for the 2D local residual.

    For ``G_local = E1(r^2/sigma^2)/(4*pi)``, the zeroth full-space moment is
    ``sigma^2/4``. The current experiment density has zero Laplacian, so the
    second-order isotropic Taylor correction vanishes.
    """

    if sigma <= 0.0:
        raise ValueError("sigma must be positive")
    return (sigma * sigma / 4.0) * _physical_density(target)


def _panel_potential(
    fans: tuple[FanTemplateMap2D, ...],
    target: Point2D,
    *,
    order: int,
    sigma: float | None,
    smooth_only: bool,
    local_only: bool = False,
) -> float:
    if smooth_only and local_only:
        raise ValueError("smooth_only and local_only are mutually exclusive")

    total = 0.0
    nodes, weights = gauss_legendre_01(order)
    for fan in fans:
        for r, wr in zip(nodes, weights, strict=True):
            jacobian = fan.signed_jacobian(r)
            for t, wt in zip(nodes, weights, strict=True):
                source = fan.point(r, t)
                if smooth_only:
                    if sigma is None:
                        raise ValueError("sigma is required for smooth split")
                    kernel = ewald_log_smooth_kernel(target, source, sigma=sigma)
                elif local_only:
                    if sigma is None:
                        raise ValueError("sigma is required for local split")
                    kernel = ewald_log_local_kernel(target, source, sigma=sigma)
                else:
                    if (
                        hypot(target[0] - source[0], target[1] - source[1])
                        <= _COINCIDENT_TOL
                    ):
                        raise ValueError(
                            "target coincides with a source quadrature node"
                        )
                    kernel = laplace_log_kernel(target, source)
                total += kernel * _physical_density(source) * jacobian * wr * wt
    return total


def run_dmk_split_nearfield_experiment(
    *,
    orders: tuple[int, ...] = (4, 6, 8, 10, 14, 18),
    sigmas: tuple[float, ...] = (0.08, 0.16, 0.32),
    reference_order: int = 96,
) -> DmkSplitExperimentReport:
    """Run the DMK-style smooth/local split experiment on straight fan panels."""

    fixtures: tuple[
        tuple[str, tuple[Point2D, ...], tuple[tuple[str, Point2D], ...]], ...
    ] = (
        (
            "convex_quad",
            ((0.0, 0.0), (1.0, 0.0), (0.95, 0.42), (0.18, 0.86)),
            (
                ("interior", (0.55, 0.32)),
                ("boundary_near_inside", (0.54, 0.025)),
                ("boundary_near_outside", (0.54, -0.025)),
                ("vertex_near_inside", (0.05, 0.045)),
            ),
        ),
        (
            "skew_quad",
            ((0.0, 0.0), (1.15, 0.02), (0.72, 0.78), (0.08, 0.62)),
            (
                ("interior", (0.50, 0.34)),
                ("boundary_near_inside", (0.56, 0.045)),
                ("boundary_near_outside", (0.56, -0.025)),
                ("vertex_near_inside", (0.06, 0.05)),
            ),
        ),
    )

    seed_quality: list[SeedQualitySample] = []
    samples: list[DmkSplitSample] = []
    for fixture_name, nodes, targets in fixtures:
        panel = TrimmedPanel2D(outer=PanelLoop2D(nodes))
        seed_options = (
            ("interior_anchor", select_interior_anchor(panel)),
            ("node_barycenter", _node_barycenter(nodes)),
        )
        for seed_mode, seed in seed_options:
            seed_quality.append(
                _panel_seed_quality(
                    fixture=fixture_name,
                    seed_mode=seed_mode,
                    nodes=nodes,
                    seed=seed,
                )
            )
            fans = _panel_fans(nodes, seed=seed)
            full_references = {
                target_label: _panel_potential(
                    fans,
                    target,
                    order=reference_order,
                    sigma=None,
                    smooth_only=False,
                )
                for target_label, target in targets
            }
            for sigma in sigmas:
                smooth_references = {
                    target_label: _panel_potential(
                        fans,
                        target,
                        order=reference_order,
                        sigma=sigma,
                        smooth_only=True,
                    )
                    for target_label, target in targets
                }
                local_references = {
                    target_label: _panel_potential(
                        fans,
                        target,
                        order=reference_order,
                        sigma=sigma,
                        smooth_only=False,
                        local_only=True,
                    )
                    for target_label, target in targets
                }
                for target_label, target in targets:
                    full_reference = full_references[target_label]
                    smooth_reference = smooth_references[target_label]
                    local_reference = local_references[target_label]
                    ratio_denominator = max(abs(full_reference), 1.0e-300)
                    for order in orders:
                        full_value = _panel_potential(
                            fans,
                            target,
                            order=order,
                            sigma=None,
                            smooth_only=False,
                        )
                        smooth_value = _panel_potential(
                            fans,
                            target,
                            order=order,
                            sigma=sigma,
                            smooth_only=True,
                        )
                        local_value = _panel_potential(
                            fans,
                            target,
                            order=order,
                            sigma=sigma,
                            smooth_only=False,
                            local_only=True,
                        )
                        analytic_local_value = _analytic_full_space_local_residual(
                            target,
                            sigma=sigma,
                        )
                        reconstructed_value = smooth_value + local_value
                        analytic_reconstructed_value = (
                            smooth_value + analytic_local_value
                        )
                        samples.append(
                            DmkSplitSample(
                                fixture=fixture_name,
                                seed_mode=seed_mode,
                                seed=seed,
                                target_label=target_label,
                                target=target,
                                sigma=sigma,
                                order=order,
                                full_value=full_value,
                                smooth_value=smooth_value,
                                local_value=local_value,
                                analytic_local_value=analytic_local_value,
                                reconstructed_value=reconstructed_value,
                                analytic_reconstructed_value=analytic_reconstructed_value,
                                full_reference=full_reference,
                                smooth_reference=smooth_reference,
                                local_reference=local_reference,
                                full_abs_error=abs(full_value - full_reference),
                                smooth_abs_error=abs(smooth_value - smooth_reference),
                                local_abs_error=abs(local_value - local_reference),
                                analytic_local_abs_error=abs(
                                    analytic_local_value - local_reference
                                ),
                                reconstructed_abs_error=abs(
                                    reconstructed_value - full_reference
                                ),
                                analytic_reconstructed_abs_error=abs(
                                    analytic_reconstructed_value - full_reference
                                ),
                                local_to_full_ratio=abs(local_reference)
                                / ratio_denominator,
                            )
                        )

    return DmkSplitExperimentReport(
        reference_order=reference_order,
        orders=orders,
        sigmas=sigmas,
        seed_quality=tuple(seed_quality),
        samples=tuple(samples),
    )


def expected_scaled_laplace_point_potential(
    base_potential: float,
    source_mass: float,
    scale_factor: float,
) -> float:
    """Return the exact 2D log-kernel scale law for a scaled source and target."""

    if scale_factor <= 0.0:
        raise ValueError("scale_factor must be positive")
    return scale_factor**2 * (
        base_potential - log(scale_factor) * source_mass / (2.0 * pi)
    )


def diagonal_remainder_sample(
    fan: FanTemplateMap2D,
    *,
    r: float,
    t: float,
    delta: float,
    direction: tuple[float, float] = (1.0, 0.5),
) -> DiagonalRemainderSample:
    """Compare the full mapped kernel with the local metric singular model."""

    if delta <= 0.0:
        raise ValueError("delta must be positive")
    delta_r = delta * direction[0]
    delta_t = delta * direction[1]
    source = fan.point(r, t)
    target = fan.point(r + delta_r, t + delta_t)
    physical_distance = hypot(target[0] - source[0], target[1] - source[1])
    model_distance = metric_model_distance(
        fan,
        r=r,
        t=t,
        delta_r=delta_r,
        delta_t=delta_t,
    )
    laplace_kernel = -log(physical_distance) / (2.0 * pi)
    metric_model_kernel = -log(model_distance) / (2.0 * pi)
    return DiagonalRemainderSample(
        delta=delta,
        physical_distance=physical_distance,
        model_distance=model_distance,
        laplace_kernel=laplace_kernel,
        metric_model_kernel=metric_model_kernel,
        remainder=laplace_kernel - metric_model_kernel,
    )


def run_nearfield_template_experiment(
    *,
    order: int = 12,
    scale_factor: float = 1.75,
) -> NearfieldTemplateExperiment:
    """Run the baseline analytic fan near-field template experiment."""

    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    near_point_target = (0.47, 0.42)

    def point_density(r: float, t: float) -> float:
        return 1.0 + r - 0.5 * t

    point_reference = point_target_laplace_potential(
        fan,
        near_point_target,
        order=max(order + 8, 16),
        source_density=point_density,
    )
    point_low_order = point_target_laplace_potential(
        fan,
        near_point_target,
        order=max(order // 2, 2),
        source_density=point_density,
    )
    scaled_target = _scale_point(near_point_target, scale_factor)
    scaled_value = point_target_laplace_potential(
        fan.scaled(scale_factor),
        scaled_target,
        order=max(order + 8, 16),
        source_density=point_density,
    )
    density_mass = template_density_mass(
        fan,
        order=max(order + 8, 16),
        density=point_density,
    )
    expected_scaled = expected_scaled_laplace_point_potential(
        point_reference,
        density_mass,
        scale_factor,
    )
    remainders = tuple(
        diagonal_remainder_sample(fan, r=0.43, t=0.37, delta=delta)
        for delta in (1.0e-1, 1.0e-2, 1.0e-3)
    )
    return NearfieldTemplateExperiment(
        fan=fan,
        order=order,
        near_point_target=near_point_target,
        point_target_reference=point_reference,
        point_target_low_order=point_low_order,
        point_target_abs_error=abs(point_low_order - point_reference),
        scaled_near_point_target=scaled_target,
        scaled_point_target_potential=scaled_value,
        expected_scaled_point_target_potential=expected_scaled,
        scaled_abs_error=abs(scaled_value - expected_scaled),
        signed_area=fan.signed_area,
        density_mass=density_mass,
        scale_factor=scale_factor,
        diagonal_remainders=remainders,
    )
