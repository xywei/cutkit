from __future__ import annotations

from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.topology import (
    normalize_panel_orientations,
    orientation,
    point_in_panel,
    select_interior_anchor,
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
