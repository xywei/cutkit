from __future__ import annotations

import pytest

from cutkit.evals import run_poisson_benchmarks
from cutkit.evals import poisson_benchmarks as pb


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


def test_planar_benchmark_requires_all_orders_within_tolerance(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    profile = pb.PROFILES["quick"]

    def fake_integrate_planar(
        _panel: object,
        *,
        order: int,
        backend_mode: pb.BackendMode,
    ) -> float:
        if backend_mode == "jplus" and order == profile.reference_order:
            return 10.0
        if order == profile.planar_orders[-1]:
            return 10.05
        return 20.0

    monkeypatch.setattr(pb, "_integrate_planar", fake_integrate_planar)

    result = pb.run_planar_poisson_benchmark(profile=profile, backend_mode="folded")
    assert not result.passed
