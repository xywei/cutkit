from __future__ import annotations

from cutkit.evals import (
    run_general_function_experiment_3d_grid,
    run_general_function_experiment_3d,
    run_polynomial_experiment_3d,
)


def test_section_6_1_3_domain_volume_is_positive() -> None:
    result = run_polynomial_experiment_3d(
        degrees=(3,),
        orders=(3,),
        seed_grid_size=2,
        surface_resolution=4,
        reference_order=7,
    )
    assert result.domain_volume > 0.0
    assert result.domain_volume < 1.0


def test_section_6_1_3_polynomial_errors_reduce_with_order() -> None:
    result = run_polynomial_experiment_3d(
        degrees=(3,),
        orders=(3, 5),
        seed_grid_size=2,
        surface_resolution=4,
        reference_order=7,
    )

    degree_result = result.degree_results[0]
    assert (
        degree_result.folded_worst_abs_error[1]
        < degree_result.folded_worst_abs_error[0]
    )
    assert degree_result.jplus_abs_error[1] < degree_result.jplus_abs_error[0]
    assert (
        degree_result.folded_worst_abs_error[0]
        >= degree_result.folded_best_abs_error[0]
    )
    assert (
        degree_result.folded_worst_abs_error[1]
        >= degree_result.folded_best_abs_error[1]
    )


def test_section_6_2_3d_general_function_errors_reduce_with_order() -> None:
    result = run_general_function_experiment_3d(
        orders=(2, 3),
        seed_grid_size=2,
        surface_resolution=4,
        reference_order=7,
    )

    order_2, order_3 = result.orders
    assert order_3.folded_worst_abs_error < order_2.folded_worst_abs_error
    assert order_3.jplus_abs_error < order_2.jplus_abs_error
    assert order_2.folded_worst_abs_error >= order_2.folded_best_abs_error
    assert order_3.folded_worst_abs_error >= order_3.folded_best_abs_error


def test_section_6_2_3d_grid_protocol_errors_reduce() -> None:
    result = run_general_function_experiment_3d_grid(
        orders=(1, 2),
        grid_resolutions=(2, 4),
        reference_grid_resolution=8,
        reference_order=8,
    )

    order_1, order_2 = result.order_results
    assert order_1.folded_abs_error[1] < order_1.folded_abs_error[0]
    assert order_2.folded_abs_error[1] < order_2.folded_abs_error[0]
    assert order_2.folded_abs_error[1] < order_1.folded_abs_error[1]
