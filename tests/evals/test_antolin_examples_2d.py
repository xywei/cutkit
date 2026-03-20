from __future__ import annotations

import pytest

from cutkit.evals import (
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment,
    run_polynomial_experiment,
)


def _nonincreasing(values: tuple[float, ...]) -> bool:
    for i in range(1, len(values)):
        if values[i] > values[i - 1]:
            return False
    return True


def test_section_6_1_eq18_protocol_and_relative_definition() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=128)
    result = run_polynomial_experiment(
        panel,
        label="6.1.1",
        degrees=(2,),
        orders=(2, 4),
        grid_resolution=8,
        reference_order=24,
        seed_grid_size=5,
    )

    degree_result = result.degree_results[0]
    assert degree_result.trimmed_cell_count > 0

    assert degree_result.folded_abs_error[1] < degree_result.folded_abs_error[0]
    assert degree_result.jplus_abs_error[1] < degree_result.jplus_abs_error[0]

    for i in range(len(degree_result.orders)):
        assert degree_result.folded_rel_error[i] == pytest.approx(
            degree_result.folded_abs_error[i] / degree_result.folded_reference_scale
        )
        assert degree_result.jplus_rel_error[i] == pytest.approx(
            degree_result.jplus_abs_error[i] / degree_result.jplus_reference_scale
        )


def test_section_6_1_2_protocol_high_order_regime() -> None:
    panel = build_section_6_1_2_rational_panel(sample_count=128)
    result = run_polynomial_experiment(
        panel,
        label="6.1.2",
        degrees=(4,),
        orders=(3, 5),
        grid_resolution=8,
        reference_order=24,
        seed_grid_size=5,
    )

    degree_result = result.degree_results[0]
    assert degree_result.folded_abs_error[1] < 1.0e-8
    assert degree_result.jplus_abs_error[1] < 1.0e-8
    assert degree_result.folded_abs_error[0] > 1.0e2 * degree_result.folded_abs_error[1]
    assert degree_result.jplus_abs_error[0] > 1.0e2 * degree_result.jplus_abs_error[1]


def test_section_6_2_elementwise_protocol_convergence() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=128)
    result = run_general_function_experiment(
        panel,
        orders=(1, 2),
        grid_resolutions=(2, 4, 8, 16),
        reference_grid_resolution=32,
        reference_order=32,
        folded_anchor_mode="cell-origin",
    )

    assert abs(result.reference_value) > 0.0

    for order_result in result.order_results:
        assert _nonincreasing(order_result.folded_abs_error)
        assert _nonincreasing(order_result.jplus_abs_error)

        for i in range(len(order_result.grid_resolutions)):
            assert order_result.folded_rel_error[i] == pytest.approx(
                order_result.folded_abs_error[i] / abs(result.reference_value)
            )
            assert order_result.jplus_rel_error[i] == pytest.approx(
                order_result.jplus_abs_error[i] / abs(result.reference_value)
            )

    first_order, second_order = result.order_results
    assert second_order.folded_abs_error[-1] < first_order.folded_abs_error[-1]
    assert second_order.jplus_abs_error[-1] < first_order.jplus_abs_error[-1]
