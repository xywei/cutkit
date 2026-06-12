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


def _rules_share_nodes(
    lhs: tuple[float, ...],
    rhs: tuple[float, ...],
    *,
    atol: float = _COINCIDENT_TOL,
) -> bool:
    for left in lhs:
        for right in rhs:
            if abs(left - right) <= atol:
                return True
    return False


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
    """Summary of one fan-chart self-interaction experiment."""

    fan: FanTemplateMap2D
    order: int
    source_order: int
    near_point_target: Point2D
    point_target_reference: float
    point_target_low_order: float
    point_target_abs_error: float
    self_interaction: float
    signed_area: float
    scale_factor: float
    scaled_self_interaction: float
    expected_scaled_self_interaction: float
    scaled_abs_error: float
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


def self_interaction_laplace(
    fan: FanTemplateMap2D,
    *,
    order: int,
    source_order: int | None = None,
    source_density: TemplateDensity2D | None = None,
    target_density: TemplateDensity2D | None = None,
) -> float:
    """Approximate the mapped self interaction on one fan chart."""

    if order < 1:
        raise ValueError("order must be positive")
    if source_order is None:
        source_order = order + 1
    if source_order < 1:
        raise ValueError("source_order must be positive")
    if source_density is None:
        source_density = unit_template_density
    if target_density is None:
        target_density = unit_template_density

    target_nodes, target_weights = gauss_legendre_01(order)
    source_nodes, source_weights = gauss_legendre_01(source_order)
    if _rules_share_nodes(target_nodes, source_nodes):
        raise ValueError(
            "source_order quadrature nodes must not overlap target order nodes "
            "for direct self-interaction reference quadrature"
        )
    total = 0.0

    for target_r, target_wr in zip(target_nodes, target_weights, strict=True):
        target_j = fan.signed_jacobian(target_r)
        for target_t, target_wt in zip(target_nodes, target_weights, strict=True):
            target = fan.point(target_r, target_t)
            target_weight = (
                target_density(target_r, target_t) * target_j * target_wr * target_wt
            )
            for source_r, source_wr in zip(source_nodes, source_weights, strict=True):
                source_j = fan.signed_jacobian(source_r)
                for source_t, source_wt in zip(
                    source_nodes, source_weights, strict=True
                ):
                    source = fan.point(source_r, source_t)
                    source_weight = (
                        source_density(source_r, source_t)
                        * source_j
                        * source_wr
                        * source_wt
                    )
                    total += (
                        laplace_log_kernel(target, source)
                        * target_weight
                        * source_weight
                    )

    return total


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


def expected_scaled_laplace_self_interaction(
    base_interaction: float,
    source_mass: float,
    scale_factor: float,
    *,
    target_mass: float | None = None,
) -> float:
    """Return the exact 2D log-kernel scale law for a scaled fan piece."""

    if scale_factor <= 0.0:
        raise ValueError("scale_factor must be positive")
    if target_mass is None:
        target_mass = source_mass
    return scale_factor**4 * (
        base_interaction - log(scale_factor) * target_mass * source_mass / (2.0 * pi)
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
    source_order = order + 1
    self_value = self_interaction_laplace(
        fan,
        order=order,
        source_order=source_order,
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
    scaled_value = self_interaction_laplace(
        fan.scaled(scale_factor),
        order=order,
        source_order=source_order,
    )
    expected_scaled = expected_scaled_laplace_self_interaction(
        self_value,
        fan.signed_area,
        scale_factor,
    )
    remainders = tuple(
        diagonal_remainder_sample(fan, r=0.43, t=0.37, delta=delta)
        for delta in (1.0e-1, 1.0e-2, 1.0e-3)
    )
    return NearfieldTemplateExperiment(
        fan=fan,
        order=order,
        source_order=source_order,
        near_point_target=near_point_target,
        point_target_reference=point_reference,
        point_target_low_order=point_low_order,
        point_target_abs_error=abs(point_low_order - point_reference),
        self_interaction=self_value,
        signed_area=fan.signed_area,
        scale_factor=scale_factor,
        scaled_self_interaction=scaled_value,
        expected_scaled_self_interaction=expected_scaled,
        scaled_abs_error=abs(scaled_value - expected_scaled),
        diagonal_remainders=remainders,
    )
