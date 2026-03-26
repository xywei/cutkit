from __future__ import annotations

import pytest

from cutkit.evals import build_section_6_1_1_bspline_panel
from cutkit.evals import poisson_galerkin as pg


def _tiny_profile() -> pg.PoissonGalerkinProfile:
    return pg.PoissonGalerkinProfile(
        name="quick",
        grid_resolutions=(4, 8),
        spline_degree=2,
        quadrature_order=3,
        reference_quadrature_order=5,
        abs_tolerance=2.0e-1,
        rel_tolerance=5.0e-1,
    )


def test_run_poisson_galerkin_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError):
        pg.run_poisson_galerkin_benchmark(profile_name="invalid", backend_mode="jplus")  # type: ignore[arg-type]


def test_run_poisson_galerkin_rejects_unknown_backend() -> None:
    with pytest.raises(ValueError):
        pg.run_poisson_galerkin_benchmark(profile_name="quick", backend_mode="bad")  # type: ignore[arg-type]


def test_poisson_galerkin_benchmark_is_deterministic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(pg.PROFILES, "quick", _tiny_profile())

    first = pg.run_poisson_galerkin_benchmark(
        profile_name="quick",
        backend_mode="jplus",
    )
    second = pg.run_poisson_galerkin_benchmark(
        profile_name="quick",
        backend_mode="jplus",
    )

    assert first.to_manifest() == second.to_manifest()


def test_poisson_galerkin_supports_folded_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setitem(pg.PROFILES, "quick", _tiny_profile())

    result = pg.run_poisson_galerkin_benchmark(
        profile_name="quick",
        backend_mode="folded",
    )

    assert result.backend_mode == "folded"
    assert result.rows
    assert all(row.free_dof_count > 0 for row in result.rows)


def test_solve_trimmed_poisson_galerkin_reports_small_residual() -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=96)
    solve = pg.solve_trimmed_poisson_galerkin(
        panel,
        resolution=6,
        spline_degree=2,
        quadrature_order=3,
        backend_mode="jplus",
        cg_tolerance=1.0e-11,
    )

    assert solve.free_dof_count > 0
    assert solve.active_dof_count > solve.free_dof_count
    assert solve.residual_norm < 1.0e-7
