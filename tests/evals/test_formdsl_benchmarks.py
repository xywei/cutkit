from __future__ import annotations

from cutkit.evals.formdsl_benchmarks import run_formdsl_parity_benchmark


def test_formdsl_parity_benchmark_runs() -> None:
    result = run_formdsl_parity_benchmark(resolutions=(8,))
    assert len(result.rows) == 1
    assert result.rows[0].iga_abs_error <= 2.0e-4
    assert any(entry.startswith("diffusion:") for entry in result.dgsem_signature)
