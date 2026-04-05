from __future__ import annotations

import pytest

from cutkit.evals.formdsl_benchmarks import run_formdsl_parity_benchmark


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
