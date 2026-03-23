"""Quadrature rule containers for 3D workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cutkit.geometry import Point3D


@dataclass(frozen=True)
class QuadratureRule3D:
    """Node and weight container for 3D quadrature rules."""

    points: tuple[Point3D, ...]
    weights: tuple[float, ...]

    def __post_init__(self) -> None:
        if len(self.points) != len(self.weights):
            raise ValueError("points and weights must have the same length")

    @property
    def size(self) -> int:
        return len(self.points)

    def integrate(self, func: Callable[[float, float, float], float]) -> float:
        """Integrate *func* over this rule."""

        total = 0.0
        for (x, y, z), weight in zip(self.points, self.weights):
            total += weight * float(func(x, y, z))
        return total


def concatenate_rules_3d(rules: tuple[QuadratureRule3D, ...]) -> QuadratureRule3D:
    """Return one quadrature rule containing all nodes from *rules*."""

    points: list[Point3D] = []
    weights: list[float] = []
    for rule in rules:
        points.extend(rule.points)
        weights.extend(rule.weights)
    return QuadratureRule3D(points=tuple(points), weights=tuple(weights))
