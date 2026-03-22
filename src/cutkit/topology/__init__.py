"""Topology layer for loop orientation and connectivity operations."""

from cutkit.topology.loops2d import (
    PanelValidationResult,
    enforce_orientation,
    normalize_panel_orientations,
    orientation,
    point_in_loop,
    point_in_panel,
    polygon_centroid,
    select_interior_anchor,
    signed_area,
    validate_panel,
)

__all__ = [
    "PanelValidationResult",
    "enforce_orientation",
    "normalize_panel_orientations",
    "orientation",
    "point_in_loop",
    "point_in_panel",
    "polygon_centroid",
    "select_interior_anchor",
    "signed_area",
    "validate_panel",
]
