from __future__ import annotations

from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.topology import (
    normalize_panel_orientations,
    orientation,
    point_in_panel,
    select_interior_anchor,
    validate_panel,
)


def test_normalize_panel_orientations() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))),
        holes=(PanelLoop2D(((0.25, 0.25), (0.25, 0.75), (0.75, 0.75), (0.75, 0.25))),),
    )

    normalized = normalize_panel_orientations(panel)
    assert orientation(normalized.outer) == "ccw"
    assert all(orientation(hole) == "cw" for hole in normalized.holes)


def test_anchor_selection_inside_panel_with_hole() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0))),
        holes=(PanelLoop2D(((0.9, 0.4), (1.1, 0.4), (1.1, 0.6), (0.9, 0.6))),),
    )

    normalized = normalize_panel_orientations(panel)
    anchor = select_interior_anchor(normalized)
    assert point_in_panel(anchor, normalized, include_boundary=False)


def test_hole_boundary_panel_membership_semantics() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(PanelLoop2D(((0.25, 0.75), (0.75, 0.75), (0.75, 0.25), (0.25, 0.25))),),
    )

    point = (0.25, 0.5)
    assert point_in_panel(point, panel, include_boundary=True)
    assert not point_in_panel(point, panel, include_boundary=False)


def test_anchor_selection_handles_thin_frame_panel() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(PanelLoop2D(((0.02, 0.98), (0.98, 0.98), (0.98, 0.02), (0.02, 0.02))),),
    )

    normalized = normalize_panel_orientations(panel)
    anchor = select_interior_anchor(normalized)
    assert point_in_panel(anchor, normalized, include_boundary=False)


def test_anchor_selection_handles_ultra_thin_frame_panel() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(
            PanelLoop2D(
                ((0.003, 0.997), (0.997, 0.997), (0.997, 0.003), (0.003, 0.003))
            ),
        ),
    )

    normalized = normalize_panel_orientations(panel)
    anchor = select_interior_anchor(normalized)
    assert point_in_panel(anchor, normalized, include_boundary=False)


def test_validate_panel_reports_degenerate_and_orientation_issues() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (0.0, 1.0), (1.0, 1.0), (1.0, 0.0))),
        holes=(PanelLoop2D(((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8))),),
    )
    report = validate_panel(panel)
    assert "outer loop orientation must be ccw" in report.errors
    assert "hole 0 orientation must be cw" in report.errors

    degenerate = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (2.0, 0.0))),
    )
    degenerate_report = validate_panel(degenerate)
    assert "outer loop must be non-degenerate" in degenerate_report.errors


def test_validate_panel_rejects_hole_outside_outer() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(PanelLoop2D(((2.0, 2.0), (2.0, 2.2), (2.2, 2.2), (2.2, 2.0))),),
    )

    report = validate_panel(panel)
    assert "hole 0 must lie strictly inside outer loop" in report.errors


def test_validate_panel_rejects_overlapping_holes() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(
            PanelLoop2D(((0.2, 0.7), (0.7, 0.7), (0.7, 0.2), (0.2, 0.2))),
            PanelLoop2D(((0.5, 1.0), (1.0, 1.0), (1.0, 0.5), (0.5, 0.5))),
        ),
    )

    report = validate_panel(panel)
    assert "holes 0 and 1 overlap or touch" in report.errors


def test_validate_panel_rejects_self_intersecting_loops() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(
            PanelLoop2D(((0.9, 0.9), (0.5, 0.3), (0.1, 0.9), (0.9, 0.1), (0.1, 0.1))),
        ),
    )

    report = validate_panel(panel)
    assert "hole 0 must be simple (non-self-intersecting)" in report.errors


def test_panel_loop_strips_repeated_closure_vertices() -> None:
    loop = PanelLoop2D(
        ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0), (0.0, 0.0), (0.0, 0.0))
    )
    assert loop.points == ((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))
