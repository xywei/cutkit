from __future__ import annotations

from math import cos, exp, log, pi, sin

import pytest

from cutkit.evals import (
    FanTemplateMap2D,
    diagonal_remainder_sample,
    ewald_log_local_kernel,
    ewald_log_local_radial_moment_2d,
    ewald_log_local_sector_monomial_moment_2d,
    ewald_log_smooth_kernel,
    expected_scaled_laplace_point_potential,
    point_target_laplace_potential,
    point_target_smooth_ewald_potential,
    run_curved_boundary_local_model_experiment,
    run_dmk_split_nearfield_experiment,
    run_graph_boundary_model_experiment,
    run_nearfield_template_experiment,
    run_precomputed_boundary_table_experiment,
    run_taylor_boundary_model_experiment,
    template_density_mass,
)
from cutkit.quadrature import gauss_legendre_01


def _polar_sector_local_moment_reference(
    *,
    sigma: float,
    x_power: int,
    y_power: int,
    theta_start: float,
    theta_end: float,
    radial_order: int = 220,
    angular_order: int = 96,
) -> float:
    log_radius_min = log(sigma) - 32.0
    log_radius_max = log(8.0 * sigma)
    radial_nodes, radial_weights = gauss_legendre_01(radial_order)
    angular_nodes, angular_weights = gauss_legendre_01(angular_order)
    log_radius_width = log_radius_max - log_radius_min
    theta_width = theta_end - theta_start
    total = 0.0
    for log_radius_node, log_radius_weight_base in zip(
        radial_nodes, radial_weights, strict=True
    ):
        log_radius = log_radius_min + log_radius_width * log_radius_node
        radius = exp(log_radius)
        # The polar area factor contributes one radius and dr = radius d(log r).
        radial_weight = log_radius_width * log_radius_weight_base * radius * radius
        for theta_node, theta_weight_base in zip(
            angular_nodes, angular_weights, strict=True
        ):
            theta = theta_start + theta_width * theta_node
            theta_weight = theta_width * theta_weight_base
            source = (radius * cos(theta), radius * sin(theta))
            total += (
                ewald_log_local_kernel((0.0, 0.0), source, sigma=sigma)
                * source[0] ** x_power
                * source[1] ** y_power
                * radial_weight
                * theta_weight
            )
    return total


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


def test_point_target_potential_obeys_log_kernel_scale_law() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    scale_factor = 2.25
    target = (0.8, 0.7)
    value = point_target_laplace_potential(fan, target, order=6)
    scaled = point_target_laplace_potential(
        fan.scaled(scale_factor),
        (scale_factor * target[0], scale_factor * target[1]),
        order=6,
    )
    expected = expected_scaled_laplace_point_potential(
        value,
        template_density_mass(fan, order=6),
        scale_factor,
    )

    assert scaled == pytest.approx(expected, abs=1.0e-13)


def test_scaled_point_target_potential_uses_density_weighted_mass() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )

    def source_density(r: float, t: float) -> float:
        return 1.0 + r

    scale_factor = 1.4
    target = (0.8, 0.7)
    value = point_target_laplace_potential(
        fan,
        target,
        order=4,
        source_density=source_density,
    )
    scaled = point_target_laplace_potential(
        fan.scaled(scale_factor),
        (scale_factor * target[0], scale_factor * target[1]),
        order=4,
        source_density=source_density,
    )
    expected = expected_scaled_laplace_point_potential(
        value,
        template_density_mass(fan, order=4, density=source_density),
        scale_factor,
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


def test_ewald_log_split_reconstructs_log_kernel() -> None:
    target = (0.3, 0.4)
    source = (0.9, -0.2)
    sigma = 0.25

    split = ewald_log_smooth_kernel(
        target, source, sigma=sigma
    ) + ewald_log_local_kernel(
        target,
        source,
        sigma=sigma,
    )

    from cutkit.evals import laplace_log_kernel

    assert split == pytest.approx(laplace_log_kernel(target, source), abs=1.0e-13)


def test_ewald_local_full_plane_moments_match_known_values() -> None:
    sigma = 0.17

    mass = ewald_log_local_sector_monomial_moment_2d(
        sigma=sigma,
        x_power=0,
        y_power=0,
        theta_start=0.0,
        theta_end=2.0 * pi,
    )
    xx_moment = ewald_log_local_sector_monomial_moment_2d(
        sigma=sigma,
        x_power=2,
        y_power=0,
        theta_start=0.0,
        theta_end=2.0 * pi,
    )
    xy_moment = ewald_log_local_sector_monomial_moment_2d(
        sigma=sigma,
        x_power=1,
        y_power=1,
        theta_start=0.0,
        theta_end=2.0 * pi,
    )

    assert mass == pytest.approx(sigma * sigma / 4.0, rel=1.0e-13)
    assert xx_moment == pytest.approx(sigma**4 / 16.0, rel=1.0e-13)
    assert xy_moment == pytest.approx(0.0, abs=1.0e-19)


def test_ewald_local_half_plane_moments_match_polar_reference() -> None:
    sigma = 0.13
    theta_start = 0.0
    theta_end = pi

    for x_power, y_power in ((0, 0), (1, 0), (0, 1), (2, 0), (0, 2)):
        analytic = ewald_log_local_sector_monomial_moment_2d(
            sigma=sigma,
            x_power=x_power,
            y_power=y_power,
            theta_start=theta_start,
            theta_end=theta_end,
        )
        reference = _polar_sector_local_moment_reference(
            sigma=sigma,
            x_power=x_power,
            y_power=y_power,
            theta_start=theta_start,
            theta_end=theta_end,
        )
        assert analytic == pytest.approx(reference, rel=5.0e-4, abs=1.0e-12)

    mass = ewald_log_local_sector_monomial_moment_2d(
        sigma=sigma,
        x_power=0,
        y_power=0,
        theta_start=theta_start,
        theta_end=theta_end,
    )
    assert mass == pytest.approx(sigma * sigma / 8.0, rel=1.0e-13)


def test_ewald_local_wedge_moments_match_polar_reference() -> None:
    sigma = 0.11
    theta_start = -0.2
    theta_end = 0.85 * pi

    for x_power, y_power in ((0, 0), (1, 0), (0, 1), (2, 0), (1, 1)):
        analytic = ewald_log_local_sector_monomial_moment_2d(
            sigma=sigma,
            x_power=x_power,
            y_power=y_power,
            theta_start=theta_start,
            theta_end=theta_end,
        )
        reference = _polar_sector_local_moment_reference(
            sigma=sigma,
            x_power=x_power,
            y_power=y_power,
            theta_start=theta_start,
            theta_end=theta_end,
        )
        assert analytic == pytest.approx(reference, rel=5.0e-4, abs=1.0e-12)

    mass = ewald_log_local_sector_monomial_moment_2d(
        sigma=sigma,
        x_power=0,
        y_power=0,
        theta_start=theta_start,
        theta_end=theta_end,
    )
    opening_angle = theta_end - theta_start
    assert mass == pytest.approx(opening_angle * sigma * sigma / (8.0 * pi))


def test_ewald_local_radial_moment_rejects_invalid_inputs() -> None:
    with pytest.raises(ValueError, match="sigma must be positive"):
        ewald_log_local_radial_moment_2d(sigma=0.0, monomial_degree=0)
    with pytest.raises(ValueError, match="monomial_degree must be nonnegative"):
        ewald_log_local_radial_moment_2d(sigma=0.1, monomial_degree=-1)


def test_curved_boundary_local_model_beats_full_plane_on_cad_style_cell() -> None:
    report = run_curved_boundary_local_model_experiment(
        sigmas=(0.02, 0.04),
        orders=(16, 32),
        reference_order=80,
    )

    finest_by_sigma = {
        sample.sigma: sample for sample in report.samples if sample.order == 32
    }

    assert len(finest_by_sigma) == 2
    for sample in finest_by_sigma.values():
        assert sample.reference_value > 0.0
        assert sample.half_plane_abs_error < sample.full_plane_abs_error
        assert sample.half_plane_rel_error < 0.03
        assert sample.full_plane_rel_error > 1.0


def test_curved_boundary_exact_model_reaches_machine_precision() -> None:
    coarse = run_curved_boundary_local_model_experiment(
        sigmas=(0.02, 0.04),
        orders=(16,),
        reference_order=24,
    )
    fine = run_curved_boundary_local_model_experiment(
        sigmas=(0.02, 0.04),
        orders=(16,),
        reference_order=32,
    )

    coarse_by_sigma = {sample.sigma: sample for sample in coarse.samples}
    fine_by_sigma = {sample.sigma: sample for sample in fine.samples}

    for sigma, fine_sample in fine_by_sigma.items():
        coarse_value = coarse_by_sigma[sigma].curved_boundary_value
        assert fine_sample.curved_boundary_value == pytest.approx(
            coarse_value,
            rel=1.0e-10,
            abs=1.0e-14,
        )


def test_high_order_taylor_boundary_model_reaches_machine_precision() -> None:
    report = run_taylor_boundary_model_experiment(
        sigmas=(0.02,),
        boundary_orders=(2, 4, 6, 8),
        angular_order=32,
    )
    errors = {sample.boundary_order: sample.rel_error for sample in report.samples}

    assert errors[4] < errors[2]
    assert errors[6] < errors[4]
    assert errors[8] < 1.0e-10


def test_high_order_taylor_boundary_model_handles_smaller_windows() -> None:
    report = run_taylor_boundary_model_experiment(
        sigmas=(0.005, 0.01),
        boundary_orders=(4, 6),
        angular_order=32,
    )

    finest_errors = {
        sample.sigma: sample.rel_error
        for sample in report.samples
        if sample.boundary_order == 6
    }

    assert finest_errors[0.005] < 1.0e-10
    assert finest_errors[0.01] < 1.0e-10


def test_precomputed_boundary_table_interpolates_to_machine_precision() -> None:
    report = run_precomputed_boundary_table_experiment(
        table_sigmas=(0.004, 0.008, 0.012, 0.016, 0.020, 0.024, 0.028),
        eval_sigmas=(0.010, 0.018, 0.026),
        boundary_order=8,
        angular_order=32,
    )

    assert max(sample.rel_error for sample in report.samples) < 1.0e-10


def test_direct_graph_strip_quadrature_is_not_enough_for_machine_precision() -> None:
    report = run_graph_boundary_model_experiment(
        sigmas=(0.02,),
        boundary_orders=(8,),
        strip_orders=(64, 128),
        angular_order=32,
    )

    errors = {sample.strip_order: sample.rel_error for sample in report.samples}

    assert errors[128] < errors[64]
    assert errors[128] > 1.0e-10


def test_curved_boundary_folded_reference_converges_with_order() -> None:
    report = run_curved_boundary_local_model_experiment(
        sigmas=(0.04,),
        orders=(10, 16, 32),
        reference_order=80,
    )

    errors = {sample.order: sample.folded_abs_error for sample in report.samples}

    assert errors[32] < errors[16]
    assert errors[16] < errors[10]


def test_smoothed_ewald_potential_allows_coincident_quadrature_node() -> None:
    fan = FanTemplateMap2D(
        vertex=(0.0, 0.0),
        edge_start=(1.0, 0.0),
        edge_end=(0.35, 0.9),
    )
    nodes, _weights = gauss_legendre_01(3)
    target = fan.point(nodes[1], nodes[1])

    value = point_target_smooth_ewald_potential(
        fan,
        target,
        order=3,
        sigma=0.2,
    )

    assert value == pytest.approx(value)


def test_dmk_split_experiment_records_local_residual_reconstruction() -> None:
    report = run_dmk_split_nearfield_experiment(
        orders=(4,),
        sigmas=(0.16,),
        reference_order=8,
    )

    sample = report.samples[0]
    assert sample.reconstructed_value == pytest.approx(
        sample.smooth_value + sample.local_value
    )
    assert sample.analytic_reconstructed_value == pytest.approx(
        sample.smooth_value + sample.analytic_local_value
    )
    assert sample.local_reference == pytest.approx(
        sample.full_reference - sample.smooth_reference,
        abs=1.0e-12,
    )
    assert sample.reconstructed_abs_error >= 0.0
    assert sample.analytic_local_abs_error >= 0.0
    assert sample.analytic_reconstructed_abs_error >= 0.0


def test_baseline_experiment_records_feasibility_checks() -> None:
    result = run_nearfield_template_experiment(order=5, scale_factor=1.5)

    assert result.scaled_abs_error < 1.0e-13
    assert result.point_target_abs_error > 0.0
    assert result.scaled_point_target_potential == pytest.approx(
        result.expected_scaled_point_target_potential,
        abs=1.0e-13,
    )
    assert result.diagonal_remainders[-1].delta == pytest.approx(1.0e-3)
    assert abs(result.diagonal_remainders[-1].remainder) < abs(
        result.diagonal_remainders[0].remainder
    )
