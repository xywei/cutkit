"""Diagnostics for 3D folded boundary volume invariants."""

from __future__ import annotations

from dataclasses import dataclass

from cutkit.geometry import Point3D, Triangle3D
from cutkit.quadrature import signed_boundary_volume_3d


@dataclass(frozen=True)
class SeedInvariantVolumeReport:
    """Compare signed-volume reconstruction from two seeds."""

    seed_a: Point3D
    seed_b: Point3D
    volume_a: float
    volume_b: float
    abs_error: float


def seed_invariant_volume_report(
    boundary: tuple[Triangle3D, ...],
    *,
    seed_a: Point3D,
    seed_b: Point3D,
) -> SeedInvariantVolumeReport:
    """Return a seed-invariance diagnostic for one boundary triangulation."""

    volume_a = signed_boundary_volume_3d(boundary, seed=seed_a)
    volume_b = signed_boundary_volume_3d(boundary, seed=seed_b)
    return SeedInvariantVolumeReport(
        seed_a=seed_a,
        seed_b=seed_b,
        volume_a=volume_a,
        volume_b=volume_b,
        abs_error=abs(volume_a - volume_b),
    )
