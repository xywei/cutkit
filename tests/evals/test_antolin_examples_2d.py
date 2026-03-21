from __future__ import annotations

import pytest

from cutkit.evals import (
    OPENCASCADE_CAD_AVAILABLE,
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment_cad,
    run_general_function_experiment,
    run_polynomial_experiment_cad,
    run_polynomial_experiment,
)
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D


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


def test_polynomial_experiment_defaults_to_panel_bbox_bounds() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=96)
    shifted = TrimmedPanel2D(
        outer=PanelLoop2D(tuple((x + 1.0, y) for x, y in panel.outer.points))
    )

    result = run_polynomial_experiment(
        shifted,
        label="6.1.1",
        degrees=(2,),
        orders=(2, 4),
        grid_resolution=4,
        reference_order=12,
        seed_grid_size=3,
    )
    assert result.degree_results[0].trimmed_cell_count > 0


def test_general_experiment_h_values_follow_bounds_span() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=96)
    result = run_general_function_experiment(
        panel,
        orders=(1,),
        grid_resolutions=(2,),
        reference_grid_resolution=4,
        reference_order=12,
        bounds=(0.0, 0.0, 2.0, 2.0),
    )

    assert result.order_results[0].h_values == pytest.approx((1.0,))


def test_cad_native_polynomial_protocol_or_unavailable_error() -> None:
    if not OPENCASCADE_CAD_AVAILABLE:
        with pytest.raises(RuntimeError):
            run_polynomial_experiment_cad(
                label="6.1.1",
                degrees=(2,),
                orders=(2, 3),
                grid_resolution=2,
                reference_order=4,
                seed_grid_size=2,
            )
        return

    result = run_polynomial_experiment_cad(
        label="6.1.1",
        degrees=(2,),
        orders=(2, 3),
        grid_resolution=2,
        reference_order=4,
        seed_grid_size=2,
    )
    degree_result = result.degree_results[0]
    assert degree_result.folded_abs_error[1] <= degree_result.folded_abs_error[0]
    assert degree_result.jplus_abs_error[1] <= degree_result.jplus_abs_error[0]


def test_cad_native_general_protocol_or_unavailable_error() -> None:
    if not OPENCASCADE_CAD_AVAILABLE:
        with pytest.raises(RuntimeError):
            run_general_function_experiment_cad(
                label="6.1.1",
                orders=(1,),
                grid_resolutions=(2,),
                reference_grid_resolution=2,
                reference_order=3,
            )
        return

    result = run_general_function_experiment_cad(
        label="6.1.1",
        orders=(1, 2),
        grid_resolutions=(2, 4),
        reference_grid_resolution=4,
        reference_order=4,
    )
    assert abs(result.reference_value) > 0.0
    low, high = result.order_results
    assert high.folded_abs_error[-1] <= low.folded_abs_error[-1]
    assert high.jplus_abs_error[-1] <= low.jplus_abs_error[-1]
