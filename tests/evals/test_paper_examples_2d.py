from __future__ import annotations

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


def test_section_6_1_1_polynomial_reproduction() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=128)
    result = run_polynomial_experiment(
        panel,
        label="6.1.1",
        degrees=(1, 2, 3),
        orders=(2, 4, 6, 8),
        reference_order=24,
        seed_grid_size=5,
    )

    for degree_result in result.degree_results:
        assert degree_result.folded_worst_error[-1] < 1.0e-12
        assert degree_result.jplus_error[-1] < 1.0e-10

        ratio = degree_result.folded_worst_error[-1] / max(
            degree_result.jplus_error[-1], 1.0e-16
        )
        assert ratio < 1.0e3

        if degree_result.degree >= 2:
            assert (
                degree_result.folded_worst_error[0]
                > 1.0e3 * degree_result.folded_worst_error[-1]
            )
            assert degree_result.jplus_error[0] > 1.0e3 * degree_result.jplus_error[-1]


def test_section_6_1_2_polynomial_reproduction() -> None:
    panel = build_section_6_1_2_rational_panel(sample_count=128)
    result = run_polynomial_experiment(
        panel,
        label="6.1.2",
        degrees=(2, 4),
        orders=(3, 5, 7, 9),
        reference_order=24,
        seed_grid_size=5,
    )

    for degree_result in result.degree_results:
        assert degree_result.folded_worst_error[-1] < 1.0e-12
        assert degree_result.jplus_error[-1] < 1.0e-10

        if degree_result.degree >= 4:
            assert (
                degree_result.folded_worst_error[0]
                > 1.0e3 * degree_result.folded_worst_error[-1]
            )
            assert degree_result.jplus_error[0] > 1.0e3 * degree_result.jplus_error[-1]


def test_section_6_2_general_function_reproduction() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=128)
    result = run_general_function_experiment(
        panel,
        orders=(1, 2, 3, 4),
        reference_order=28,
        seed_grid_size=5,
    )

    assert _nonincreasing(result.folded_worst_error)
    assert _nonincreasing(result.jplus_error)
    assert result.folded_worst_error[-1] < 1.0e-6
    assert result.jplus_error[-1] < 1.0e-7
