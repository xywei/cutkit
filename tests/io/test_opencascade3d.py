from __future__ import annotations

import pytest

from cutkit.io import (
    build_axis_aligned_box_solid,
    clip_solid_with_axis_aligned_box_to_oriented_boundary,
    opencascade3d_available,
    opencascade3d_status,
    solid_to_boundary_triangulation,
    solid_to_oriented_boundary_triangles,
)
from cutkit.quadrature import signed_boundary_volume_3d


def test_opencascade3d_status_shape() -> None:
    status = opencascade3d_status()
    assert isinstance(status.available, bool)
    if status.available:
        assert status.reason is None
    else:
        assert status.reason


def test_opencascade3d_build_box_or_unavailable_error() -> None:
    if not opencascade3d_available():
        with pytest.raises(RuntimeError):
            build_axis_aligned_box_solid(
                x0=0.0,
                x1=1.0,
                y0=0.0,
                y1=1.0,
                z0=0.0,
                z1=1.0,
            )
        return

    solid = build_axis_aligned_box_solid(
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )
    boundary = solid_to_oriented_boundary_triangles(
        solid,
        linear_deflection=5.0e-2,
        angular_deflection=0.5,
    )
    assert boundary
    volume = signed_boundary_volume_3d(boundary, seed=(0.25, 0.25, 0.25))
    assert volume == pytest.approx(1.0, rel=1.0e-9, abs=1.0e-9)

    triangulation = solid_to_boundary_triangulation(
        solid,
        linear_deflection=5.0e-2,
        angular_deflection=0.5,
    )
    assert triangulation.triangles


def test_opencascade3d_clip_half_box_volume_or_unavailable_error() -> None:
    if not opencascade3d_available():
        with pytest.raises(RuntimeError):
            solid_to_oriented_boundary_triangles(
                object(),
                linear_deflection=5.0e-2,
                angular_deflection=0.5,
            )
        return

    solid = build_axis_aligned_box_solid(
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )
    clipped_boundary = clip_solid_with_axis_aligned_box_to_oriented_boundary(
        solid,
        x0=0.0,
        x1=0.5,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        linear_deflection=5.0e-2,
        angular_deflection=0.5,
    )
    assert clipped_boundary
    volume = signed_boundary_volume_3d(clipped_boundary, seed=(0.1, 0.1, 0.1))
    assert volume == pytest.approx(0.5, rel=1.0e-9, abs=1.0e-9)
