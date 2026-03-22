from __future__ import annotations

from typing import cast

import pytest

from cutkit.geometry import Triangle3D
from cutkit.quadrature import signed_boundary_volume_3d
from cutkit.topology import orient_boundary_triangles_outward, triangle_area


def test_orient_boundary_triangles_outward_recovers_tetra_volume() -> None:
    v0 = (0.0, 0.0, 0.0)
    v1 = (1.0, 0.0, 0.0)
    v2 = (0.0, 1.0, 0.0)
    v3 = (0.0, 0.0, 1.0)

    mixed: tuple[Triangle3D, ...] = (
        (v0, v2, v1),
        (v0, v1, v3),
        (v0, v3, v2),
        (v1, v2, v3),
        (v1, v3, v2),
    )

    oriented = orient_boundary_triangles_outward(mixed)
    assert len(oriented) == 4
    assert all(triangle_area(triangle) > 0.0 for triangle in oriented)

    volume = signed_boundary_volume_3d(oriented, seed=(0.1, 0.1, 0.1))
    assert volume == pytest.approx(1.0 / 6.0, rel=1.0e-12, abs=1.0e-12)


def test_orient_boundary_triangles_outward_rejects_degenerate_input() -> None:
    degenerate = cast(
        Triangle3D,
        (
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
            (0.0, 0.0, 0.0),
        ),
    )
    triangles: tuple[Triangle3D, ...] = (degenerate,)
    with pytest.raises(ValueError):
        orient_boundary_triangles_outward(triangles)


def test_orient_boundary_triangles_outward_flips_each_disconnected_shell() -> None:
    a0 = (0.0, 0.0, 0.0)
    a1 = (2.0, 0.0, 0.0)
    a2 = (0.0, 2.0, 0.0)
    a3 = (0.0, 0.0, 2.0)

    b0 = (10.0, 0.0, 0.0)
    b1 = (11.0, 0.0, 0.0)
    b2 = (10.0, 1.0, 0.0)
    b3 = (10.0, 0.0, 1.0)

    outward_large: tuple[Triangle3D, ...] = (
        (a0, a2, a1),
        (a0, a1, a3),
        (a0, a3, a2),
        (a1, a2, a3),
    )
    inward_small: tuple[Triangle3D, ...] = (
        (b0, b1, b2),
        (b0, b3, b1),
        (b0, b2, b3),
        (b1, b3, b2),
    )

    oriented = orient_boundary_triangles_outward(outward_large + inward_small)

    shell_a = tuple(triangle for triangle in oriented if triangle[0][0] < 5.0)
    shell_b = tuple(triangle for triangle in oriented if triangle[0][0] > 5.0)

    assert len(shell_a) == 4
    assert len(shell_b) == 4
    assert signed_boundary_volume_3d(shell_a, seed=(0.25, 0.25, 0.25)) > 0.0
    assert signed_boundary_volume_3d(shell_b, seed=(10.25, 0.25, 0.25)) > 0.0
