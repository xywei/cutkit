from __future__ import annotations

import pytest

from cutkit.evals.formdsl_benchmarks import (
    multipatch_stress_fixtures,
    run_formdsl_multipatch_stress_benchmark,
    run_formdsl_parity_benchmark,
)


def test_formdsl_parity_benchmark_runs() -> None:
    result = run_formdsl_parity_benchmark(resolutions=(8,))

    assert len(result.rows) == 1
    assert result.rows[0].iga_abs_error <= 2.0e-4
    assert result.shared_term_signature == (
        "diffusion:1",
        "source:1:callable:cutkit.evals.poisson_galerkin.default_poisson_source",
    )
    assert result.shared_boundary_signature == ("essential:all:0",)
    assert result.shared_metadata_signature == ("dg_flux=sipg",)
    assert result.dgsem_signature == (
        "diffusion:1",
        "source:1:callable:cutkit.evals.poisson_galerkin.default_poisson_source",
        "dirichlet:all:0",
    )
    assert result.dgsem_flux_signature == (
        "sipg:boundary_dirichlet:all:1:0:1",
        "sipg:interior:interior:1:none:1",
    )


def test_formdsl_parity_benchmark_requires_non_empty_resolutions() -> None:
    with pytest.raises(ValueError, match="non-empty"):
        run_formdsl_parity_benchmark(resolutions=())


def test_formdsl_multipatch_stress_fixtures_include_expected_shapes() -> None:
    fixtures = multipatch_stress_fixtures()

    assert len(fixtures) >= 4
    assert any("three_patch" in fixture.name for fixture in fixtures)
    assert any("nurbs" in fixture.name for fixture in fixtures)
    assert any("orientation_pair_aligned" == fixture.name for fixture in fixtures)
    assert any("orientation_pair_reversed" == fixture.name for fixture in fixtures)


def test_formdsl_multipatch_stress_benchmark_runs() -> None:
    result = run_formdsl_multipatch_stress_benchmark()

    assert len(result.rows) >= 4
    assert result.orientation_delta_max_abs > 0.0
    for row in result.rows:
        assert row.interface_count >= 1
        assert row.matrix_nnz > 0
        assert row.matrix_max_abs > 0.0
        assert row.repeat_matrix_max_abs_diff == 0.0
        assert row.repeat_rhs_max_abs_diff == 0.0
