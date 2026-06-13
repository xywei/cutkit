"""Near-field template experiments for folded 2D fan pieces."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, log, pi, sqrt
from typing import Callable

from cutkit.quadrature import gauss_legendre_01

Point2D = tuple[float, float]
TemplateDensity2D = Callable[[float, float], float]
_COINCIDENT_TOL = 1.0e-14


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


def laplace_log_kernel(target: Point2D, source: Point2D) -> float:
    """Return the 2D Laplace fundamental solution ``-log(|x-y|)/(2*pi)``."""

    distance = hypot(target[0] - source[0], target[1] - source[1])
    if distance <= 0.0:
        raise ValueError("Laplace log kernel is singular at coincident points")
    return -log(distance) / (2.0 * pi)


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
