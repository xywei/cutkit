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


def _norm(vector: Point3D) -> float:
    return (
        vector[0] * vector[0] + vector[1] * vector[1] + vector[2] * vector[2]
    ) ** 0.5


def _ray_intersects_triangle(
    origin: Point3D,
    direction: Point3D,
    triangle: Triangle3D,
    *,
    tol: float,
) -> bool:
    a, b, c = triangle
    edge1 = _sub(b, a)
    edge2 = _sub(c, a)
    pvec = _cross(direction, edge2)
    det = _dot(edge1, pvec)
    if abs(det) <= tol:
        return False

    inv_det = 1.0 / det
    tvec = _sub(origin, a)
    u = _dot(tvec, pvec) * inv_det
    if u < -tol or u > 1.0 + tol:
        return False

    qvec = _cross(tvec, edge1)
    v = _dot(direction, qvec) * inv_det
    if v < -tol or u + v > 1.0 + tol:
        return False

    distance = _dot(edge2, qvec) * inv_det
    return distance > tol


def _point_inside_component(
    point: Point3D,
    triangles: tuple[Triangle3D, ...],
    *,
    tol: float,
) -> bool:
    directions: tuple[Point3D, ...] = (
        (1.0, 0.1337, 0.3971),
        (0.2718, 1.0, 0.6180),
        (0.3892, 0.4571, 1.0),
    )
    inside_votes = 0
    for direction in directions:
        hits = 0
        for triangle in triangles:
            if _ray_intersects_triangle(point, direction, triangle, tol=tol):
                hits += 1
        if hits % 2 == 1:
            inside_votes += 1
    return inside_votes >= 2


def _component_probe_point(
    component: list[int],
    oriented: list[Triangle3D],
    *,
    tol: float,
) -> Point3D:
    vertices = [vertex for index in component for vertex in oriented[index]]
    xs = [vertex[0] for vertex in vertices]
    ys = [vertex[1] for vertex in vertices]
    zs = [vertex[2] for vertex in vertices]
    bbox_scale = max(
        max(xs) - min(xs),
        max(ys) - min(ys),
        max(zs) - min(zs),
        1.0,
    )

    a, b, c = oriented[component[0]]
    centroid = (
        (a[0] + b[0] + c[0]) / 3.0,
        (a[1] + b[1] + c[1]) / 3.0,
        (a[2] + b[2] + c[2]) / 3.0,
    )
    normal = _cross(_sub(b, a), _sub(c, a))
    length = _norm(normal)
    if length <= tol:
        return centroid

    step = max(1.0e-6 * bbox_scale, 10.0 * tol)
    return (
        centroid[0] - normal[0] * step / length,
        centroid[1] - normal[1] * step / length,
        centroid[2] - normal[2] * step / length,
    )


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
    triangles: tuple[Triangle3D, ...],
    *,
    tol: float = 1.0e-12,
    validate_closed: bool = True,
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
            if validate_closed:
                raise ValueError(
                    "boundary triangulation must be a closed 2-manifold "
                    "(each edge incident to exactly two triangles)"
                )
            continue

        (left_index, left_dir), (right_index, right_dir) = incidents
        parity = 1 if left_dir == right_dir else 0
        adjacency[left_index].append((right_index, parity))
        adjacency[right_index].append((left_index, parity))

    flip_state: list[int | None] = [None] * len(unique)
    components: list[list[int]] = []
    for seed_index in range(len(unique)):
        if flip_state[seed_index] is not None:
            continue

        flip_state[seed_index] = 0
        queue: deque[int] = deque([seed_index])
        component: list[int] = []
        while queue:
            index = queue.popleft()
            component.append(index)
            current = flip_state[index]
            if current is None:
                raise RuntimeError("internal orientation state error")

            for neighbor_index, parity in adjacency[index]:
                expected = current ^ parity
                seen_state = flip_state[neighbor_index]
                if seen_state is None:
                    flip_state[neighbor_index] = expected
                    queue.append(neighbor_index)

        components.append(component)

    oriented = [
        (a, c, b) if flip else (a, b, c)
        for (a, b, c), flip in zip(unique, flip_state, strict=True)
    ]

    for component in components:
        signed_volume = sum(
            _dot(oriented[index][0], _cross(oriented[index][1], oriented[index][2]))
            / 6.0
            for index in component
        )
        if signed_volume < 0.0:
            for index in component:
                a, b, c = oriented[index]
                oriented[index] = (a, c, b)

    component_triangles = [
        tuple(oriented[index] for index in component) for component in components
    ]
    probe_points = [
        _component_probe_point(component, oriented, tol=tol) for component in components
    ]
    for component_index, component in enumerate(components):
        nesting_depth = 0
        probe = probe_points[component_index]
        for other_index, other_triangles in enumerate(component_triangles):
            if other_index == component_index:
                continue
            if _point_inside_component(probe, other_triangles, tol=tol):
                nesting_depth += 1

        if nesting_depth % 2 == 1:
            for index in component:
                a, b, c = oriented[index]
                oriented[index] = (a, c, b)

    return tuple(oriented)
