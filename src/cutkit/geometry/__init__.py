"""Geometry layer for trimmed patch parameterizations and evaluators."""

from cutkit.geometry.curves2d import (
    CurveEdge2D,
    CurveLoop2D,
    CurveTrimmedPanel2D,
    curve_loop_signed_area,
)
from cutkit.geometry.panel2d import PanelLoop2D, Point2D, TrimmedPanel2D
from cutkit.geometry.volume3d import (
    BoundaryTriangulation3D,
    FoldedBoundaryCell3D,
    Point3D,
    Triangle3D,
)

__all__ = [
    "CurveEdge2D",
    "CurveLoop2D",
    "CurveTrimmedPanel2D",
    "BoundaryTriangulation3D",
    "FoldedBoundaryCell3D",
    "PanelLoop2D",
    "Point2D",
    "Point3D",
    "Triangle3D",
    "TrimmedPanel2D",
    "curve_loop_signed_area",
]
