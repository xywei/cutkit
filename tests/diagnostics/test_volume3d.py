from __future__ import annotations

import pytest

from cutkit.diagnostics import seed_invariant_volume_report
from cutkit.topology import orient_boundary_triangles_outward


def test_seed_invariant_volume_report_matches_tetra_volume() -> None:
    v0 = (0.0, 0.0, 0.0)
    v1 = (1.0, 0.0, 0.0)
    v2 = (0.0, 1.0, 0.0)
    v3 = (0.0, 0.0, 1.0)
    boundary = orient_boundary_triangles_outward(
        (
            (v0, v2, v1),
            (v0, v1, v3),
            (v0, v3, v2),
            (v1, v2, v3),
        )
    )

    report = seed_invariant_volume_report(
        boundary,
        seed_a=(0.1, 0.1, 0.1),
        seed_b=(0.2, 0.1, 0.1),
    )

    assert report.volume_a == pytest.approx(1.0 / 6.0, rel=1.0e-12, abs=1.0e-12)
    assert report.volume_b == pytest.approx(1.0 / 6.0, rel=1.0e-12, abs=1.0e-12)
    assert report.abs_error < 1.0e-12
