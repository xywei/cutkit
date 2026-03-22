from __future__ import annotations

import pytest

from cutkit.quadrature import signed_boundary_volume_3d
from cutkit.topology import orient_boundary_triangles_outward, triangle_area


def test_orient_boundary_triangles_outward_recovers_tetra_volume() -> None:
    v0 = (0.0, 0.0, 0.0)
    v1 = (1.0, 0.0, 0.0)
    v2 = (0.0, 1.0, 0.0)
    v3 = (0.0, 0.0, 1.0)

    mixed = (
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
    with pytest.raises(ValueError):
        orient_boundary_triangles_outward((((0.0, 0.0, 0.0),) * 3,))
