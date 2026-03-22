from __future__ import annotations

import pytest

from cutkit.evals import run_poisson_benchmarks


def test_run_poisson_benchmarks_rejects_unknown_profile() -> None:
    with pytest.raises(ValueError):
        run_poisson_benchmarks(profile_name="invalid", backend_mode="jplus")  # type: ignore[arg-type]


def test_run_poisson_benchmarks_rejects_unknown_backend_mode() -> None:
    with pytest.raises(ValueError):
        run_poisson_benchmarks(profile_name="quick", backend_mode="jplsu")  # type: ignore[arg-type]


def test_quick_profile_jplus_is_deterministic() -> None:
    first = run_poisson_benchmarks(profile_name="quick", backend_mode="jplus")
    second = run_poisson_benchmarks(profile_name="quick", backend_mode="jplus")

    assert first.to_manifest() == second.to_manifest()


def test_quick_profile_supports_folded_backend_mode() -> None:
    result = run_poisson_benchmarks(profile_name="quick", backend_mode="folded")
    assert result.planar.backend_mode == "folded"
    assert result.volume.backend_mode == "folded"
    assert result.planar.order_results
    assert result.volume.order_results
