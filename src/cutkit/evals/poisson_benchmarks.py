"""Poisson-oriented benchmark runners over trimmed planar and volume domains."""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from math import cos, pi, sin
from typing import Any, Literal

from cutkit.evals.antolin_wei_buffa_2022_3d import (
    build_section_6_1_3_boundary_triangles,
)
from cutkit.evals.antolin_wei_buffa_2022_2d import build_section_6_1_1_bspline_panel
from cutkit.quadrature import (
    folded_quadrature_rule,
    integrate_general_over_boundary_3d,
)

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

BackendMode = Literal["jplus", "folded"]
ProfileName = Literal["quick", "dense"]


@dataclass(frozen=True)
class PoissonBenchmarkProfile:
    name: ProfileName
    planar_orders: tuple[int, ...]
    volume_orders: tuple[int, ...]
    reference_order: int
    planar_sample_count: int
    volume_surface_resolution: int
    abs_tolerance: float
    rel_tolerance: float


@dataclass(frozen=True)
class PoissonOrderResult:
    order: int
    approximation: float
    abs_error: float
    rel_error: float


@dataclass(frozen=True)
class PlanarPoissonBenchmarkResult:
    backend_mode: BackendMode
    reference_value: float
    order_results: tuple[PoissonOrderResult, ...]
    abs_tolerance: float
    rel_tolerance: float
    passed: bool


@dataclass(frozen=True)
class VolumePoissonBenchmarkResult:
    backend_mode: BackendMode
    surface_resolution: int
    reference_value: float
    order_results: tuple[PoissonOrderResult, ...]
    abs_tolerance: float
    rel_tolerance: float
    passed: bool


@dataclass(frozen=True)
class PoissonBenchmarkResult:
    profile: ProfileName
    planar: PlanarPoissonBenchmarkResult
    volume: VolumePoissonBenchmarkResult
    passed: bool

    def to_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "profile": self.profile,
            "backend_mode": self.planar.backend_mode,
            "passed": self.passed,
            "planar": {
                "backend_mode": self.planar.backend_mode,
                "reference_value": self.planar.reference_value,
                "abs_tolerance": self.planar.abs_tolerance,
                "rel_tolerance": self.planar.rel_tolerance,
                "passed": self.planar.passed,
                "order_results": [
                    {
                        "order": row.order,
                        "approximation": row.approximation,
                        "abs_error": row.abs_error,
                        "rel_error": row.rel_error,
                    }
                    for row in self.planar.order_results
                ],
            },
            "volume": {
                "backend_mode": self.volume.backend_mode,
                "surface_resolution": self.volume.surface_resolution,
                "reference_value": self.volume.reference_value,
                "abs_tolerance": self.volume.abs_tolerance,
                "rel_tolerance": self.volume.rel_tolerance,
                "passed": self.volume.passed,
                "order_results": [
                    {
                        "order": row.order,
                        "approximation": row.approximation,
                        "abs_error": row.abs_error,
                        "rel_error": row.rel_error,
                    }
                    for row in self.volume.order_results
                ],
            },
        }


PROFILES: dict[ProfileName, PoissonBenchmarkProfile] = {
    "quick": PoissonBenchmarkProfile(
        name="quick",
        planar_orders=(2, 4, 6),
        volume_orders=(3, 5),
        reference_order=12,
        planar_sample_count=128,
        volume_surface_resolution=5,
        abs_tolerance=1.0e-3,
        rel_tolerance=1.0e-2,
    ),
    "dense": PoissonBenchmarkProfile(
        name="dense",
        planar_orders=(2, 4, 6, 8),
        volume_orders=(3, 5, 7),
        reference_order=16,
        planar_sample_count=160,
        volume_surface_resolution=8,
        abs_tolerance=5.0e-4,
        rel_tolerance=5.0e-3,
    ),
}


def _sin(value: Any) -> Any:
    if _np is not None:
        return _np.sin(value)
    return sin(float(value))


def _cos(value: Any) -> Any:
    if _np is not None:
        return _np.cos(value)
    return cos(float(value))


def planar_poisson_integrand(x: Any, y: Any) -> Any:
    """Energy-density-style planar Poisson benchmark integrand."""

    u = _sin(pi * x) * _sin(pi * y)
    f = 2.0 * pi * pi * u
    return u * u + f * f


def volume_poisson_integrand(x: Any, y: Any, z: Any) -> Any:
    """Energy-density-style volume Poisson benchmark integrand."""

    u = _sin(pi * x) * _sin(pi * y) * _sin(pi * z)
    f = 3.0 * pi * pi * u
    return u * u + f * f


def _planar_anchor_for_mode(
    panel: Any, backend_mode: BackendMode
) -> tuple[float, float] | None:
    if backend_mode == "jplus":
        return None
    xmin, ymin, _xmax, _ymax = panel.bbox()
    return (xmin, ymin)


def _integrate_planar(panel: Any, *, order: int, backend_mode: BackendMode) -> float:
    anchor = _planar_anchor_for_mode(panel, backend_mode)
    rule = folded_quadrature_rule(
        panel,
        order=order,
        anchor=anchor,
        require_interior_anchor=anchor is None,
    ).rule
    total = 0.0
    for (x, y), weight in zip(rule.points, rule.weights):
        total += float(planar_poisson_integrand(x, y)) * weight
    return total


def run_planar_poisson_benchmark(
    *,
    profile: PoissonBenchmarkProfile,
    backend_mode: BackendMode,
) -> PlanarPoissonBenchmarkResult:
    panel = build_section_6_1_1_bspline_panel(sample_count=profile.planar_sample_count)
    reference = _integrate_planar(
        panel, order=profile.reference_order, backend_mode="jplus"
    )
    scale = max(abs(reference), 1.0e-30)

    rows: list[PoissonOrderResult] = []
    for order in profile.planar_orders:
        value = _integrate_planar(panel, order=order, backend_mode=backend_mode)
        abs_error = abs(value - reference)
        rows.append(
            PoissonOrderResult(
                order=order,
                approximation=value,
                abs_error=abs_error,
                rel_error=abs_error / scale,
            )
        )

    final_error = rows[-1].abs_error
    threshold = max(profile.abs_tolerance, profile.rel_tolerance * scale)
    return PlanarPoissonBenchmarkResult(
        backend_mode=backend_mode,
        reference_value=reference,
        order_results=tuple(rows),
        abs_tolerance=profile.abs_tolerance,
        rel_tolerance=profile.rel_tolerance,
        passed=final_error <= threshold,
    )


def _volume_seed(backend_mode: BackendMode) -> tuple[float, float, float]:
    if backend_mode == "jplus":
        return (1.0, 1.0, 0.5)
    return (0.0, 0.0, 0.0)


def run_volume_poisson_benchmark(
    *,
    profile: PoissonBenchmarkProfile,
    backend_mode: BackendMode,
) -> VolumePoissonBenchmarkResult:
    boundary = build_section_6_1_3_boundary_triangles(
        surface_resolution=profile.volume_surface_resolution
    )
    reference_seed = _volume_seed("jplus")
    reference = integrate_general_over_boundary_3d(
        boundary,
        seed=reference_seed,
        order=profile.reference_order,
        integrand=volume_poisson_integrand,
    )
    scale = max(abs(reference), 1.0e-30)

    rows: list[PoissonOrderResult] = []
    seed = _volume_seed(backend_mode)
    for order in profile.volume_orders:
        value = integrate_general_over_boundary_3d(
            boundary,
            seed=seed,
            order=order,
            integrand=volume_poisson_integrand,
        )
        abs_error = abs(value - reference)
        rows.append(
            PoissonOrderResult(
                order=order,
                approximation=value,
                abs_error=abs_error,
                rel_error=abs_error / scale,
            )
        )

    final_error = rows[-1].abs_error
    threshold = max(profile.abs_tolerance, profile.rel_tolerance * scale)
    return VolumePoissonBenchmarkResult(
        backend_mode=backend_mode,
        surface_resolution=profile.volume_surface_resolution,
        reference_value=reference,
        order_results=tuple(rows),
        abs_tolerance=profile.abs_tolerance,
        rel_tolerance=profile.rel_tolerance,
        passed=final_error <= threshold,
    )


def run_poisson_benchmarks(
    *,
    profile_name: ProfileName = "quick",
    backend_mode: BackendMode = "jplus",
) -> PoissonBenchmarkResult:
    """Run planar and volume Poisson-oriented benchmark sweeps."""

    if profile_name not in PROFILES:
        raise ValueError(f"unknown benchmark profile: {profile_name!r}")
    if backend_mode not in {"jplus", "folded"}:
        raise ValueError(f"unknown benchmark backend mode: {backend_mode!r}")

    profile = PROFILES[profile_name]
    planar = run_planar_poisson_benchmark(profile=profile, backend_mode=backend_mode)
    volume = run_volume_poisson_benchmark(profile=profile, backend_mode=backend_mode)
    return PoissonBenchmarkResult(
        profile=profile_name,
        planar=planar,
        volume=volume,
        passed=planar.passed and volume.passed,
    )
