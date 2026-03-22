"""Boundary-orientation topology utilities for 3D folded workflows."""

from __future__ import annotations

from collections import defaultdict, deque

from cutkit.geometry import Point3D, Triangle3D


def _sub(a: Point3D, b: Point3D) -> Point3D:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _cross(a: Point3D, b: Point3D) -> Point3D:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _dot(a: Point3D, b: Point3D) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def triangle_area(triangle: Triangle3D) -> float:
    """Return Euclidean area of one triangle."""

    a, b, c = triangle
    normal = _cross(_sub(b, a), _sub(c, a))
    return (
        0.5
        * (normal[0] * normal[0] + normal[1] * normal[1] + normal[2] * normal[2]) ** 0.5
    )


def _vertex_key(point: Point3D, *, tol: float = 1.0e-12) -> tuple[int, int, int]:
    return (
        int(round(point[0] / tol)),
        int(round(point[1] / tol)),
        int(round(point[2] / tol)),
    )


def orient_boundary_triangles_outward(
    triangles: tuple[Triangle3D, ...], *, tol: float = 1.0e-12
) -> tuple[Triangle3D, ...]:
    """Return a deduplicated boundary set with consistent outward orientation."""

    filtered = [triangle for triangle in triangles if triangle_area(triangle) > tol]
    if not filtered:
        raise ValueError("boundary triangulation contains no non-degenerate triangles")

    unique: list[Triangle3D] = []
    seen: set[
        tuple[tuple[int, int, int], tuple[int, int, int], tuple[int, int, int]]
    ] = set()
    for triangle in filtered:
        sorted_keys = sorted(_vertex_key(vertex, tol=tol) for vertex in triangle)
        triangle_key = (sorted_keys[0], sorted_keys[1], sorted_keys[2])
        if triangle_key in seen:
            continue
        seen.add(triangle_key)
        unique.append(triangle)

    if not unique:
        raise ValueError("boundary triangulation contains no unique triangles")

    edge_incidents: dict[
        tuple[tuple[int, int, int], tuple[int, int, int]],
        list[tuple[int, int]],
    ] = defaultdict(list)

    for triangle_index, (a, b, c) in enumerate(unique):
        for start, end in ((a, b), (b, c), (c, a)):
            start_key = _vertex_key(start, tol=tol)
            end_key = _vertex_key(end, tol=tol)
            if start_key <= end_key:
                edge = (start_key, end_key)
                direction = 1
            else:
                edge = (end_key, start_key)
                direction = -1
            edge_incidents[edge].append((triangle_index, direction))

    adjacency: dict[int, list[tuple[int, int]]] = defaultdict(list)
    for incidents in edge_incidents.values():
        if len(incidents) != 2:
            continue

        (left_index, left_dir), (right_index, right_dir) = incidents
        parity = 1 if left_dir == right_dir else 0
        adjacency[left_index].append((right_index, parity))
        adjacency[right_index].append((left_index, parity))

    flip_state: list[int | None] = [None] * len(unique)
    for seed_index in range(len(unique)):
        if flip_state[seed_index] is not None:
            continue

        flip_state[seed_index] = 0
        queue: deque[int] = deque([seed_index])
        while queue:
            index = queue.popleft()
            current = flip_state[index]
            if current is None:
                raise RuntimeError("internal orientation state error")

            for neighbor_index, parity in adjacency[index]:
                expected = current ^ parity
                seen_state = flip_state[neighbor_index]
                if seen_state is None:
                    flip_state[neighbor_index] = expected
                    queue.append(neighbor_index)

    oriented = [
        (a, c, b) if flip else (a, b, c)
        for (a, b, c), flip in zip(unique, flip_state, strict=True)
    ]

    signed_volume = sum(_dot(a, _cross(b, c)) / 6.0 for a, b, c in oriented)
    if signed_volume < 0.0:
        oriented = [(a, c, b) for a, b, c in oriented]

    return tuple(oriented)
