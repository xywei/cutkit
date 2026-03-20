"""2D panel geometry primitives for trimmed-domain workflows."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Iterable, Sequence

Point2D = tuple[float, float]


def _coerce_point(point: Sequence[float]) -> Point2D:
    if len(point) != 2:
        raise ValueError("points must have exactly two coordinates")

    x = float(point[0])
    y = float(point[1])
    if not isfinite(x) or not isfinite(y):
        raise ValueError("point coordinates must be finite")

    return (x, y)


def _normalize_points(points: Iterable[Sequence[float]]) -> tuple[Point2D, ...]:
    normalized = tuple(_coerce_point(point) for point in points)
    if len(normalized) < 3:
        raise ValueError("a loop must contain at least three points")

    if normalized[0] == normalized[-1]:
        normalized = normalized[:-1]

    if len(normalized) < 3:
        raise ValueError("a loop must contain at least three distinct points")

    return normalized


@dataclass(frozen=True)
class PanelLoop2D:
    """One polygonal loop for a trimmed panel."""

    points: tuple[Point2D, ...]

    def __post_init__(self) -> None:
        object.__setattr__(self, "points", _normalize_points(self.points))

    def edges(self) -> tuple[tuple[Point2D, Point2D], ...]:
        points = self.points
        return tuple(
            (points[i], points[(i + 1) % len(points)]) for i in range(len(points))
        )

    def bbox(self) -> tuple[float, float, float, float]:
        xs = tuple(point[0] for point in self.points)
        ys = tuple(point[1] for point in self.points)
        return (min(xs), min(ys), max(xs), max(ys))


@dataclass(frozen=True)
class TrimmedPanel2D:
    """Trimmed panel made of one outer loop and zero or more holes."""

    outer: PanelLoop2D
    holes: tuple[PanelLoop2D, ...] = ()

    def __post_init__(self) -> None:
        outer = self.outer
        if not isinstance(outer, PanelLoop2D):
            outer = PanelLoop2D(tuple(outer))

        holes: list[PanelLoop2D] = []
        for hole in self.holes:
            if isinstance(hole, PanelLoop2D):
                holes.append(hole)
            else:
                holes.append(PanelLoop2D(tuple(hole)))

        object.__setattr__(self, "outer", outer)
        object.__setattr__(self, "holes", tuple(holes))

    def loops(self) -> tuple[PanelLoop2D, ...]:
        return (self.outer, *self.holes)

    def bbox(self) -> tuple[float, float, float, float]:
        loop_boxes = tuple(loop.bbox() for loop in self.loops())
        return (
            min(box[0] for box in loop_boxes),
            min(box[1] for box in loop_boxes),
            max(box[2] for box in loop_boxes),
            max(box[3] for box in loop_boxes),
        )
