"""Topology layer for loop orientation and connectivity operations."""

from cutkit.topology.loops2d import (
    LoopValidationDiagnostics,
    PanelValidationDiagnostics,
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
from cutkit.topology.boundary3d import (
    orient_boundary_triangles_outward,
    triangle_area,
)

__all__ = [
    "LoopValidationDiagnostics",
    "PanelValidationDiagnostics",
    "PanelValidationResult",
    "enforce_orientation",
    "normalize_panel_orientations",
    "orientation",
    "orient_boundary_triangles_outward",
    "point_in_loop",
    "point_in_panel",
    "polygon_centroid",
    "select_interior_anchor",
    "signed_area",
    "triangle_area",
    "validate_panel",
]
