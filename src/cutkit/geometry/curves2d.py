"""CAD-native 2D curve-loop primitives for trimmed panels."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from math import cos, isfinite, pi
from typing import Callable

Point2D = tuple[float, float]


def _coerce_point(point: Point2D) -> Point2D:
    x = float(point[0])
    y = float(point[1])
    if not isfinite(x) or not isfinite(y):
        raise ValueError("point coordinates must be finite")
    return (x, y)


def _points_close(a: Point2D, b: Point2D, *, tol: float = 1.0e-9) -> bool:
    return abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol


def _gauss_legendre_01(order: int) -> tuple[tuple[float, ...], tuple[float, ...]]:
    if order < 1:
        raise ValueError("quadrature order must be positive")

    nodes_raw = [0.0] * order
    weights_raw = [0.0] * order
    midpoint = (order + 1) // 2
    eps = 1.0e-15

    for i in range(midpoint):
        z = cos(pi * (i + 0.75) / (order + 0.5))
        while True:
            p1 = 1.0
            p2 = 0.0
            for j in range(1, order + 1):
                p3 = p2
                p2 = p1
                p1 = ((2.0 * j - 1.0) * z * p2 - (j - 1.0) * p3) / j

            pp = order * (z * p1 - p2) / (z * z - 1.0)
            z_next = z - p1 / pp
            if abs(z_next - z) <= eps:
                z = z_next
                break
            z = z_next

        nodes_raw[i] = -z
        nodes_raw[order - 1 - i] = z
        weight = 2.0 / ((1.0 - z * z) * (pp * pp))
        weights_raw[i] = weight
        weights_raw[order - 1 - i] = weight

    nodes = tuple(0.5 * (value + 1.0) for value in nodes_raw)
    weights = tuple(0.5 * value for value in weights_raw)
    return nodes, weights


@dataclass(frozen=True)
class CurveEdge2D:
    """Parametric edge segment with first derivative."""

    evaluator: Callable[[float], Point2D]
    derivative: Callable[[float], Point2D]
    t_start: float = 0.0
    t_end: float = 1.0

    def __post_init__(self) -> None:
        t_start = float(self.t_start)
        t_end = float(self.t_end)
        if not isfinite(t_start) or not isfinite(t_end):
            raise ValueError("edge parameter bounds must be finite")
        if abs(t_end - t_start) <= 1.0e-15:
            raise ValueError("edge parameter interval must be non-zero")
        object.__setattr__(self, "t_start", t_start)
        object.__setattr__(self, "t_end", t_end)

    @staticmethod
    def line(p0: Point2D, p1: Point2D) -> CurveEdge2D:
        p0 = _coerce_point(p0)
        p1 = _coerce_point(p1)
        dx = p1[0] - p0[0]
        dy = p1[1] - p0[1]

        def eval_line(t: float) -> Point2D:
            return (p0[0] + float(t) * dx, p0[1] + float(t) * dy)

        def deriv_line(_t: float) -> Point2D:
            return (dx, dy)

        return CurveEdge2D(evaluator=eval_line, derivative=deriv_line)

    def point(self, s: float) -> Point2D:
        s_clamped = 0.0 if s <= 0.0 else (1.0 if s >= 1.0 else float(s))
        t = self.t_start + (self.t_end - self.t_start) * s_clamped
        return _coerce_point(self.evaluator(t))

    def tangent(self, s: float) -> Point2D:
        s_clamped = 0.0 if s <= 0.0 else (1.0 if s >= 1.0 else float(s))
        t = self.t_start + (self.t_end - self.t_start) * s_clamped
        dt_ds = self.t_end - self.t_start
        dx_dt, dy_dt = self.derivative(t)
        return (float(dx_dt) * dt_ds, float(dy_dt) * dt_ds)

    def reversed(self) -> CurveEdge2D:
        return CurveEdge2D(
            evaluator=self.evaluator,
            derivative=self.derivative,
            t_start=self.t_end,
            t_end=self.t_start,
        )

    def trimmed(self, s_start: float, s_end: float) -> CurveEdge2D:
        s0 = max(0.0, min(1.0, float(s_start)))
        s1 = max(0.0, min(1.0, float(s_end)))
        t0 = self.t_start + (self.t_end - self.t_start) * s0
        t1 = self.t_start + (self.t_end - self.t_start) * s1
        return CurveEdge2D(
            evaluator=self.evaluator,
            derivative=self.derivative,
            t_start=t0,
            t_end=t1,
        )

    def sample_points(self, *, count: int) -> tuple[Point2D, ...]:
        if count < 2:
            raise ValueError("count must be at least 2")
        return tuple(self.point(i / (count - 1)) for i in range(count))


@dataclass(frozen=True)
class CurveLoop2D:
    """Closed loop made of ordered curve edges."""

    edges: tuple[CurveEdge2D, ...]

    def __post_init__(self) -> None:
        edges = tuple(self.edges)
        if not edges:
            raise ValueError("a curve loop must contain at least one edge")

        edge_count = len(edges)
        for idx in range(edge_count):
            end = edges[idx].point(1.0)
            next_start = edges[(idx + 1) % edge_count].point(0.0)
            if not _points_close(end, next_start):
                raise ValueError("curve loop edges must form a continuous closed chain")

        object.__setattr__(self, "edges", edges)

    def reversed(self) -> CurveLoop2D:
        return CurveLoop2D(tuple(edge.reversed() for edge in reversed(self.edges)))

    def sample_points(self, *, points_per_edge: int) -> tuple[Point2D, ...]:
        if points_per_edge < 2:
            raise ValueError("points_per_edge must be at least 2")

        points: list[Point2D] = []
        for edge in self.edges:
            edge_points = edge.sample_points(count=points_per_edge)
            if points:
                points.extend(edge_points[1:])
            else:
                points.extend(edge_points)

        if points and points[0] == points[-1]:
            points.pop()
        return tuple(points)


@dataclass(frozen=True)
class CurveTrimmedPanel2D:
    """Trimmed panel with curve-loop outer boundary and optional holes."""

    outer: CurveLoop2D
    holes: tuple[CurveLoop2D, ...] = ()

    def __post_init__(self) -> None:
        holes = tuple(self.holes)
        object.__setattr__(self, "holes", holes)

    def loops(self) -> tuple[CurveLoop2D, ...]:
        return (self.outer, *self.holes)

    def sample_points(
        self, *, points_per_edge: int
    ) -> tuple[tuple[Point2D, ...], tuple[tuple[Point2D, ...], ...]]:
        outer = self.outer.sample_points(points_per_edge=points_per_edge)
        holes = tuple(
            hole.sample_points(points_per_edge=points_per_edge) for hole in self.holes
        )
        return outer, holes


@lru_cache(maxsize=256)
def curve_loop_signed_area(loop: CurveLoop2D, *, order: int = 16) -> float:
    """Approximate signed area by Green's theorem over exact curve edges."""

    nodes, weights = _gauss_legendre_01(order)
    integral = 0.0
    for edge in loop.edges:
        for t, wt in zip(nodes, weights):
            x, y = edge.point(t)
            dx, dy = edge.tangent(t)
            integral += (x * dy - y * dx) * wt
    return 0.5 * integral
