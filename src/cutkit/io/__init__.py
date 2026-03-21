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
]
