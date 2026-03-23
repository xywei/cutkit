from __future__ import annotations

import pytest

from cutkit.clipping import (
    build_cartesian_grid_3d,
    classify_axis_aligned_cell,
    classify_x_aligned_cell,
    classify_y_aligned_cell,
    classify_z_aligned_cell,
)


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


@pytest.mark.parametrize(
    ("axis", "surface_min", "surface_max", "expected"),
    (
        ("x", None, None, "outside"),
        ("y", -0.5, 0.0, "inside"),
        ("z", 0.25, 0.75, "trimmed"),
    ),
)
def test_classify_axis_aligned_cell_states(
    axis: str,
    surface_min: float | None,
    surface_max: float | None,
    expected: str,
) -> None:
    cell = build_cartesian_grid_3d(resolution=1)[0]
    clip = classify_axis_aligned_cell(
        cell,
        axis=axis,  # type: ignore[arg-type]
        surface_min=surface_min,
        surface_max=surface_max,
    )
    assert clip.kind == expected


def test_classify_axis_aligned_cell_rejects_unknown_axis() -> None:
    cell = build_cartesian_grid_3d(resolution=1)[0]
    with pytest.raises(ValueError):
        classify_axis_aligned_cell(
            cell,
            axis="w",  # type: ignore[arg-type]
            surface_min=0.0,
            surface_max=1.0,
        )


def test_classify_y_and_z_wrappers_match_axis_generic() -> None:
    cell = build_cartesian_grid_3d(resolution=1)[0]

    clip_y = classify_y_aligned_cell(
        cell,
        surface_min_y=0.3,
        surface_max_y=0.7,
    )
    generic_y = classify_axis_aligned_cell(
        cell,
        axis="y",
        surface_min=0.3,
        surface_max=0.7,
    )
    assert clip_y.kind == generic_y.kind == "trimmed"

    clip_z = classify_z_aligned_cell(
        cell,
        surface_min_z=-0.1,
        surface_max_z=0.0,
    )
    generic_z = classify_axis_aligned_cell(
        cell,
        axis="z",
        surface_min=-0.1,
        surface_max=0.0,
    )
    assert clip_z.kind == generic_z.kind == "inside"
