from __future__ import annotations

import pytest

from cutkit.evals import (
    build_section_6_1_3_boundary_triangles,
    run_general_function_experiment_3d_grid,
    run_general_function_experiment_3d,
    run_polynomial_experiment_3d,
)
from cutkit.evals import antolin_wei_buffa_2022_3d as awb3d
from cutkit.evals.antolin_wei_buffa_2022_3d import _tetra_volume_sum


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


def test_section_6_1_3_boundary_volume_is_seed_invariant() -> None:
    boundary = build_section_6_1_3_boundary_triangles(surface_resolution=4)
    vol_a = _tetra_volume_sum(boundary, (1.0, 1.0, 0.5))
    vol_b = _tetra_volume_sum(boundary, (0.5, 0.5, 0.5))
    assert vol_a == pytest.approx(vol_b)


def test_section_6_2_3d_folded_errors_use_common_reference() -> None:
    result = run_general_function_experiment_3d(
        orders=(7,),
        seed_grid_size=2,
        surface_resolution=4,
        reference_order=7,
    )

    order_result = result.orders[0]
    assert order_result.jplus_abs_error == pytest.approx(0.0)
    assert order_result.folded_worst_abs_error >= order_result.folded_best_abs_error
    assert order_result.folded_worst_abs_error > 0.0


def test_polynomial_best_folded_excludes_jplus_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jplus_seed = (1.0, 1.0, 0.5)
    other_seed = (0.0, 0.0, 0.0)

    monkeypatch.setattr(
        awb3d,
        "build_section_6_1_3_boundary_triangles",
        lambda **_: (((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),),
    )
    monkeypatch.setattr(awb3d, "_tetra_volume_sum", lambda *_, **__: 0.1)
    monkeypatch.setattr(awb3d, "_seed_grid_3d", lambda size: (jplus_seed, other_seed))

    def fake_bernstein(
        boundary: object,
        *,
        seed: tuple[float, float, float],
        order: int,
        **unused_kwargs: object,
    ) -> tuple[float, ...]:
        _ = boundary, unused_kwargs
        if seed == jplus_seed:
            return (0.1 * order,)
        return (10.0 + order,)

    monkeypatch.setattr(awb3d, "_integrate_bernstein_over_boundary", fake_bernstein)

    result = awb3d.run_polynomial_experiment_3d(
        degrees=(2,),
        orders=(5,),
        reference_order=7,
        seed_grid_size=5,
        surface_resolution=4,
    )
    degree_result = result.degree_results[0]
    assert degree_result.folded_best_abs_error[0] > degree_result.jplus_abs_error[0]


def test_general_best_folded_excludes_jplus_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    jplus_seed = (1.0, 1.0, 0.5)
    other_seed = (0.0, 0.0, 0.0)

    monkeypatch.setattr(
        awb3d,
        "build_section_6_1_3_boundary_triangles",
        lambda **_: (((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),),
    )
    monkeypatch.setattr(awb3d, "_seed_grid_3d", lambda size: (jplus_seed, other_seed))

    def fake_general(
        boundary: object,
        *,
        seed: tuple[float, float, float],
        order: int,
        **unused_kwargs: object,
    ) -> float:
        _ = boundary, unused_kwargs
        if seed == jplus_seed:
            return 0.1 * order
        return 10.0 + order

    monkeypatch.setattr(awb3d, "_integrate_general_over_boundary", fake_general)

    result = awb3d.run_general_function_experiment_3d(
        orders=(5,),
        reference_order=7,
        seed_grid_size=5,
        surface_resolution=4,
    )
    order_result = result.orders[0]
    assert order_result.folded_best_abs_error > order_result.jplus_abs_error


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


@pytest.mark.parametrize("surface_resolution", [6, 9, 10, 12, 15, 18, 20, 21, 24])
def test_section_6_1_3_boundary_builder_supports_resolution(
    surface_resolution: int,
) -> None:
    boundary = build_section_6_1_3_boundary_triangles(
        surface_resolution=surface_resolution
    )
    vol_a = _tetra_volume_sum(boundary, (1.0, 1.0, 0.5))
    vol_b = _tetra_volume_sum(boundary, (0.5, 0.5, 0.5))
    assert vol_a > 0.0
    assert vol_a == pytest.approx(vol_b, rel=1.0e-10, abs=1.0e-10)
