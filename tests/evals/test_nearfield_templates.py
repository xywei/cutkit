from __future__ import annotations

import pytest

from cutkit.evals import (
    FanTemplateMap2D,
    diagonal_remainder_sample,
    expected_scaled_laplace_self_interaction,
    point_target_laplace_potential,
    run_nearfield_template_experiment,
    self_interaction_laplace,
    template_density_mass,
)
from cutkit.quadrature import gauss_legendre_01


def test_fan_map_area_and_metric_are_consistent() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.25, 0.5),
    )

    assert fan.signed_area == pytest.approx(0.25)
    metric = fan.local_metric(0.5, 0.25)
    assert metric[0][0] > 0.0
    assert metric[1][1] > 0.0
    assert metric[0][1] == pytest.approx(metric[1][0])


def test_self_interaction_obeys_log_kernel_scale_law() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    scale_factor = 2.25
    value = self_interaction_laplace(fan, order=5, source_order=6)
    scaled = self_interaction_laplace(
        fan.scaled(scale_factor),
        order=5,
        source_order=6,
    )
    expected = expected_scaled_laplace_self_interaction(
        value,
        fan.signed_area,
        scale_factor,
    )

    assert scaled == pytest.approx(expected, abs=1.0e-13)


def test_self_interaction_rejects_overlapping_template_nodes() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )

    with pytest.raises(ValueError, match="must not overlap"):
        self_interaction_laplace(fan, order=3, source_order=5)


def test_scaled_self_interaction_uses_density_weighted_masses() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )

    def source_density(r: float, t: float) -> float:
        return 1.0 + r

    def target_density(r: float, t: float) -> float:
        return 1.0 - 0.25 * t

    scale_factor = 1.4
    value = self_interaction_laplace(
        fan,
        order=4,
        source_order=5,
        source_density=source_density,
        target_density=target_density,
    )
    scaled = self_interaction_laplace(
        fan.scaled(scale_factor),
        order=4,
        source_order=5,
        source_density=source_density,
        target_density=target_density,
    )
    expected = expected_scaled_laplace_self_interaction(
        value,
        template_density_mass(fan, order=4, density=source_density),
        scale_factor,
        target_mass=template_density_mass(fan, order=4, density=target_density),
    )

    assert scaled == pytest.approx(expected, abs=1.0e-13)


def test_metric_singular_remainder_shrinks_toward_diagonal() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    coarse = diagonal_remainder_sample(fan, r=0.43, t=0.37, delta=1.0e-2)
    fine = diagonal_remainder_sample(fan, r=0.43, t=0.37, delta=1.0e-4)

    assert abs(fine.remainder) < abs(coarse.remainder)
    assert fine.physical_distance == pytest.approx(fine.model_distance, rel=1.0e-3)


def test_point_target_path_converges_for_near_disjoint_target() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    target = (0.8, 0.7)

    def density(r: float, t: float) -> float:
        return 1.0 + r * t

    coarse = point_target_laplace_potential(
        fan,
        target,
        order=4,
        source_density=density,
    )
    fine = point_target_laplace_potential(
        fan,
        target,
        order=10,
        source_density=density,
    )
    reference = point_target_laplace_potential(
        fan,
        target,
        order=18,
        source_density=density,
    )

    assert abs(fine - reference) < abs(coarse - reference)


def test_point_target_path_rejects_coincident_source_node() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    nodes, _weights = gauss_legendre_01(3)
    target = fan.point(nodes[1], nodes[1])

    with pytest.raises(ValueError, match="coincides with a source quadrature node"):
        point_target_laplace_potential(fan, target, order=3)


def test_baseline_experiment_records_feasibility_checks() -> None:
    result = run_nearfield_template_experiment(order=5, scale_factor=1.5)

    assert result.scaled_abs_error < 1.0e-13
    assert result.point_target_abs_error > 0.0
    assert result.diagonal_remainders[-1].delta == pytest.approx(1.0e-3)
    assert abs(result.diagonal_remainders[-1].remainder) < abs(
        result.diagonal_remainders[0].remainder
    )
