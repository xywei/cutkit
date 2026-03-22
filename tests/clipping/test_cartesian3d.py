from __future__ import annotations

import pytest

from cutkit.clipping import build_cartesian_grid_3d, classify_x_aligned_cell


def test_build_cartesian_grid_3d_returns_expected_cell_count() -> None:
    cells = build_cartesian_grid_3d(resolution=3)
    assert len(cells) == 27

    first = cells[0]
    assert first.ix == 0 and first.iy == 0 and first.iz == 0
    assert first.volume == pytest.approx((1.0 / 3.0) ** 3)


def test_classify_x_aligned_cell_states() -> None:
    cell = build_cartesian_grid_3d(resolution=1)[0]

    outside = classify_x_aligned_cell(
        cell,
        surface_min_x=None,
        surface_max_x=None,
    )
    assert outside.kind == "outside"

    inside = classify_x_aligned_cell(
        cell,
        surface_min_x=-0.5,
        surface_max_x=0.0,
    )
    assert inside.kind == "inside"

    trimmed = classify_x_aligned_cell(
        cell,
        surface_min_x=0.25,
        surface_max_x=0.75,
    )
    assert trimmed.kind == "trimmed"
