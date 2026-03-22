"""3D geometry primitives for folded-volume workflows."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Sequence

Point3D = tuple[float, float, float]
Triangle3D = tuple[Point3D, Point3D, Point3D]


def _coerce_point(point: Sequence[float]) -> Point3D:
    if len(point) != 3:
        raise ValueError("points must have exactly three coordinates")

    x = float(point[0])
    y = float(point[1])
    z = float(point[2])
    if not isfinite(x) or not isfinite(y) or not isfinite(z):
        raise ValueError("point coordinates must be finite")

    return (x, y, z)


def _coerce_triangle(triangle: Sequence[Sequence[float]]) -> Triangle3D:
    if len(triangle) != 3:
        raise ValueError("triangles must have exactly three vertices")
    return (
        _coerce_point(triangle[0]),
        _coerce_point(triangle[1]),
        _coerce_point(triangle[2]),
    )


@dataclass(frozen=True)
class BoundaryTriangulation3D:
    """Closed boundary triangulation for one trimmed volume."""

    triangles: tuple[Triangle3D, ...]

    def __post_init__(self) -> None:
        triangles = tuple(_coerce_triangle(triangle) for triangle in self.triangles)
        if not triangles:
            raise ValueError(
                "boundary triangulation must contain at least one triangle"
            )
        object.__setattr__(self, "triangles", triangles)


@dataclass(frozen=True)
class FoldedBoundaryCell3D:
    """One seed-anchored signed contribution cell over one boundary triangle."""

    seed: Point3D
    triangle: Triangle3D

    def __post_init__(self) -> None:
        object.__setattr__(self, "seed", _coerce_point(self.seed))
        object.__setattr__(self, "triangle", _coerce_triangle(self.triangle))
