"""Adapters for external IO and format integration."""

from cutkit.io.opencascade2d import (
    OpenCascadeStatus,
    OpenCascadeUnavailableError,
    build_rectangle_face,
    build_section_6_1_1_face,
    build_section_6_1_2_face,
    face_to_curve_panel,
    intersect_face_with_rectangle,
    opencascade_available,
    opencascade_status,
)
from cutkit.io.opencascade3d import (
    OpenCascade3DStatus,
    OpenCascade3DUnavailableError,
    build_axis_aligned_box_solid,
    clip_solid_with_axis_aligned_box,
    clip_solid_with_axis_aligned_box_to_oriented_boundary,
    opencascade3d_available,
    opencascade3d_status,
    solid_to_boundary_triangulation,
    solid_to_boundary_triangles,
    solid_to_oriented_boundary_triangles,
)

__all__ = [
    "OpenCascadeStatus",
    "OpenCascadeUnavailableError",
    "build_rectangle_face",
    "build_section_6_1_1_face",
    "build_section_6_1_2_face",
    "face_to_curve_panel",
    "intersect_face_with_rectangle",
    "opencascade_available",
    "opencascade_status",
    "OpenCascade3DStatus",
    "OpenCascade3DUnavailableError",
    "build_axis_aligned_box_solid",
    "clip_solid_with_axis_aligned_box",
    "clip_solid_with_axis_aligned_box_to_oriented_boundary",
    "opencascade3d_available",
    "opencascade3d_status",
    "solid_to_boundary_triangulation",
    "solid_to_boundary_triangles",
    "solid_to_oriented_boundary_triangles",
]
