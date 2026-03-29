"""3D reproductions for Antolin-Wei-Buffa (2022, Section 6).

Source and credit:
- Pablo Antolin, Xiaodong Wei, Annalisa Buffa (2022)
- "Robust Numerical Integration on Curved Polyhedra Based on Folded Decompositions"
- Computer Methods in Applied Mechanics and Engineering
- DOI: 10.1016/j.cma.2022.114948
- arXiv: https://arxiv.org/abs/2109.03734

This module targets the 3D geometry from Section 6.1.3 (single parent cell)
and provides paper-parity polynomial and general-function experiments.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from functools import lru_cache
from math import cos, exp, sin
from typing import Any

from cutkit.quadrature import (
    folded_seeds_without_jplus_3d as _core_folded_seeds_without_jplus,
    gauss_legendre_01,
    integrate_general_over_cartesian_grid_xsurface_3d as _core_integrate_cartesian,
    seed_grid_3d as _core_seed_grid_3d,
)

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

Point3D = tuple[float, float, float]


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


def _lerp(a: Point3D, b: Point3D, t: float) -> Point3D:
    return (
        a[0] + (b[0] - a[0]) * t,
        a[1] + (b[1] - a[1]) * t,
        a[2] + (b[2] - a[2]) * t,
    )


def _bezier_basis_2(t: float) -> tuple[float, float, float]:
    omt = 1.0 - t
    return (omt * omt, 2.0 * t * omt, t * t)


def _bezier_basis_2_with_derivative(
    t: float,
) -> tuple[tuple[float, float, float], tuple[float, float, float]]:
    omt = 1.0 - t
    basis = (omt * omt, 2.0 * t * omt, t * t)
    deriv = (-2.0 * omt, 2.0 - 4.0 * t, 2.0 * t)
    return basis, deriv


_CONTROL_NET: tuple[tuple[Point3D, Point3D, Point3D], ...] = (
    ((1.0, 0.2, 0.0), (1.0, 0.8, 0.5), (1.0, 0.4, 1.0)),
    ((0.5, 0.5, 0.0), (0.5, 0.5, 0.5), (0.25, 0.25, 1.0)),
    ((0.2, 1.0, 0.0), (0.0, 1.0, 0.5), (0.3, 1.0, 1.0)),
)


def eval_section_6_1_3_bezier_surface(u: float, v: float) -> Point3D:
    """Evaluate the bi-quadratic Bezier surface from Section 6.1.3."""

    bu = _bezier_basis_2(u)
    bv = _bezier_basis_2(v)

    x = 0.0
    y = 0.0
    z = 0.0
    for i in range(3):
        for j in range(3):
            coeff = bu[i] * bv[j]
            px, py, pz = _CONTROL_NET[i][j]
            x += coeff * px
            y += coeff * py
            z += coeff * pz
    return (x, y, z)


def _eval_surface_with_yz_partials(
    u: float, v: float
) -> tuple[float, float, float, float, float, float, float]:
    """Return x,y,z and yz Jacobian components at (u,v)."""

    bu, dbu = _bezier_basis_2_with_derivative(u)
    bv, dbv = _bezier_basis_2_with_derivative(v)

    x = 0.0
    y = 0.0
    z = 0.0
    dy_du = 0.0
    dy_dv = 0.0
    dz_du = 0.0
    dz_dv = 0.0

    for i in range(3):
        for j in range(3):
            px, py, pz = _CONTROL_NET[i][j]
            b = bu[i] * bv[j]
            b_du = dbu[i] * bv[j]
            b_dv = bu[i] * dbv[j]

            x += b * px
            y += b * py
            z += b * pz
            dy_du += b_du * py
            dy_dv += b_dv * py
            dz_du += b_du * pz
            dz_dv += b_dv * pz

    return (x, y, z, dy_du, dy_dv, dz_du, dz_dv)


_Y_MIN = min(pt[1] for row in _CONTROL_NET for pt in row)
_Y_MAX = max(pt[1] for row in _CONTROL_NET for pt in row)
_Z_MIN = min(pt[2] for row in _CONTROL_NET for pt in row)
_Z_MAX = max(pt[2] for row in _CONTROL_NET for pt in row)

_PROJECTION_STRICT_TOL_SQ = (1.0e-12) ** 2
_PROJECTION_ACCEPT_TOL_SQ = (5.0e-8) ** 2


@lru_cache(maxsize=8)
def _projection_seed_samples(
    resolution: int = 17,
) -> tuple[tuple[float, float, float, float], ...]:
    samples: list[tuple[float, float, float, float]] = []
    for i in range(resolution):
        u = i / (resolution - 1)
        for j in range(resolution):
            v = j / (resolution - 1)
            x, y, z = eval_section_6_1_3_bezier_surface(u, v)
            samples.append((y, z, u, v))
    return tuple(samples)


def _newton_project_x_from_yz(
    y_target: float,
    z_target: float,
    *,
    u0: float,
    v0: float,
    max_iterations: int = 35,
) -> tuple[float, float]:
    """Return best x candidate and residual from one projected Newton solve."""

    u = u0
    v = v0
    best_x = 0.0
    best_res_sq = float("inf")

    for _ in range(max_iterations):
        x, y, z, dy_du, dy_dv, dz_du, dz_dv = _eval_surface_with_yz_partials(u, v)
        fy = y - y_target
        fz = z - z_target
        res_sq = fy * fy + fz * fz
        if res_sq < best_res_sq:
            best_res_sq = res_sq
            best_x = x

        if res_sq <= _PROJECTION_STRICT_TOL_SQ:
            break

        det = dy_du * dz_dv - dy_dv * dz_du
        if abs(det) <= 1.0e-14:
            break

        du = (fy * dz_dv - fz * dy_dv) / det
        dv = (-fy * dz_du + fz * dy_du) / det

        u -= du
        v -= dv
        if u < 0.0:
            u = 0.0
        elif u > 1.0:
            u = 1.0
        if v < 0.0:
            v = 0.0
        elif v > 1.0:
            v = 1.0

    return best_x, best_res_sq


def _x_surface_candidates_from_yz(
    y_target: float,
    z_target: float,
) -> tuple[float, ...]:
    """Return converged x candidates for one (y, z) projection sample."""

    seeds = _projection_seed_samples()
    nearest = sorted(
        seeds,
        key=lambda item: (item[0] - y_target) ** 2 + (item[1] - z_target) ** 2,
    )[:6]

    candidates: list[float] = []
    for _, _, u0, v0 in nearest:
        x, res_sq = _newton_project_x_from_yz(
            y_target,
            z_target,
            u0=u0,
            v0=v0,
        )
        if res_sq > _PROJECTION_ACCEPT_TOL_SQ:
            continue

        x_val = float(x)
        if any(abs(existing - x_val) <= 1.0e-8 for existing in candidates):
            continue
        candidates.append(x_val)

    return tuple(candidates)


@lru_cache(maxsize=200000)
def _x_surface_from_yz(y_target: float, z_target: float) -> float | None:
    """Solve for x_s(y,z) on the curved face; return None if outside projection."""

    if y_target < _Y_MIN - 1.0e-10 or y_target > _Y_MAX + 1.0e-10:
        return None
    if z_target < _Z_MIN - 1.0e-10 or z_target > _Z_MAX + 1.0e-10:
        return None

    candidates = _x_surface_candidates_from_yz(y_target, z_target)
    if not candidates:
        return None

    # Lower-envelope selection resolves folded multi-branch projections.
    return min(candidates)


def _x1_face_point(u: float, v: float) -> Point3D:
    sx, sy, sz = eval_section_6_1_3_bezier_surface(u, v)
    return (1.0, sy, sz)


@dataclass(frozen=True)
class Section613Boundary:
    """Section 6.1.3 boundary descriptor using direct parametric patches."""

    surface_resolution: int
    side_resolution: int


_BOUNDARY_PATCHES: tuple[str, ...] = ("curved", "x1", "z0", "z1", "y1")


def _patch_point(patch: str, s: float, t: float) -> Point3D:
    if patch == "curved":
        return eval_section_6_1_3_bezier_surface(s, t)
    if patch == "x1":
        return _x1_face_point(s, t)
    if patch == "z0":
        c0 = eval_section_6_1_3_bezier_surface(s, 0.0)
        return _lerp(c0, (1.0, c0[1], c0[2]), t)
    if patch == "z1":
        c1 = eval_section_6_1_3_bezier_surface(s, 1.0)
        return _lerp(c1, (1.0, c1[1], c1[2]), t)
    if patch == "y1":
        c = eval_section_6_1_3_bezier_surface(1.0, s)
        return _lerp(c, (1.0, c[1], c[2]), t)
    raise ValueError(f"unsupported boundary patch: {patch!r}")


def _finite_patch_derivative(
    patch: str,
    *,
    s: float,
    t: float,
    axis: str,
) -> Point3D:
    step = 1.0e-6
    if axis == "s":
        low = max(0.0, s - step)
        high = min(1.0, s + step)
        if high <= low:
            return (0.0, 0.0, 0.0)
        p0 = _patch_point(patch, low, t)
        p1 = _patch_point(patch, high, t)
        inv = 1.0 / (high - low)
        return (inv * (p1[0] - p0[0]), inv * (p1[1] - p0[1]), inv * (p1[2] - p0[2]))

    low = max(0.0, t - step)
    high = min(1.0, t + step)
    if high <= low:
        return (0.0, 0.0, 0.0)
    p0 = _patch_point(patch, s, low)
    p1 = _patch_point(patch, s, high)
    inv = 1.0 / (high - low)
    return (inv * (p1[0] - p0[0]), inv * (p1[1] - p0[1]), inv * (p1[2] - p0[2]))


def _interior_reference_point() -> Point3D:
    cx, cy, cz = eval_section_6_1_3_bezier_surface(0.5, 0.5)
    return ((1.0 + cx) * 0.5, cy, cz)


@lru_cache(maxsize=8)
def _patch_orientation_sign(patch: str) -> float:
    point = _patch_point(patch, 0.5, 0.5)
    ds = _finite_patch_derivative(patch, s=0.5, t=0.5, axis="s")
    dt = _finite_patch_derivative(patch, s=0.5, t=0.5, axis="t")
    normal = _cross(ds, dt)
    ref = _interior_reference_point()
    outward_test = _dot(normal, _sub(point, ref))
    return 1.0 if outward_test >= 0.0 else -1.0


@dataclass(frozen=True)
class _SurfaceRule:
    points: tuple[Point3D, ...]
    weighted_normals: tuple[Point3D, ...]


def _surface_rule(boundary: Section613Boundary, *, order: int) -> _SurfaceRule:
    _ = boundary
    if order < 1:
        raise ValueError("order must be positive")

    nodes, weights = gauss_legendre_01(order)
    points: list[Point3D] = []
    weighted_normals: list[Point3D] = []

    for patch in _BOUNDARY_PATCHES:
        sign = _patch_orientation_sign(patch)
        for s, ws in zip(nodes, weights, strict=True):
            for t, wt in zip(nodes, weights, strict=True):
                point = _patch_point(patch, float(s), float(t))
                ds = _finite_patch_derivative(patch, s=float(s), t=float(t), axis="s")
                dt = _finite_patch_derivative(patch, s=float(s), t=float(t), axis="t")
                normal = _cross(ds, dt)
                scale = sign * float(ws) * float(wt)
                weighted = (scale * normal[0], scale * normal[1], scale * normal[2])
                if abs(weighted[0]) + abs(weighted[1]) + abs(weighted[2]) <= 1.0e-20:
                    continue
                points.append(point)
                weighted_normals.append(weighted)

    if not points:
        raise ValueError("section 6.1.3 boundary produced no face quadrature samples")
    return _SurfaceRule(points=tuple(points), weighted_normals=tuple(weighted_normals))


def _folded_volume_rule(
    boundary: Section613Boundary,
    *,
    seed: Point3D,
    order: int,
) -> tuple[tuple[Point3D, ...], tuple[float, ...]]:
    if order < 1:
        raise ValueError("order must be positive")

    surface = _surface_rule(boundary, order=order)
    radial_nodes, radial_weights = gauss_legendre_01(order)

    points: list[Point3D] = []
    weights: list[float] = []
    for point, weighted_normal in zip(
        surface.points,
        surface.weighted_normals,
        strict=True,
    ):
        delta = _sub(point, seed)
        signed_measure = _dot(delta, weighted_normal)
        for r, wr in zip(radial_nodes, radial_weights, strict=True):
            radial = float(r)
            mapped = (
                seed[0] + radial * delta[0],
                seed[1] + radial * delta[1],
                seed[2] + radial * delta[2],
            )
            points.append(mapped)
            weights.append(signed_measure * radial * radial * float(wr))
    return tuple(points), tuple(weights)


def _bernstein_all(degree: int, t: float) -> tuple[float, ...]:
    if t <= 0.0:
        out = [0.0] * (degree + 1)
        out[0] = 1.0
        return tuple(out)
    if t >= 1.0:
        out = [0.0] * (degree + 1)
        out[degree] = 1.0
        return tuple(out)

    omt = 1.0 - t
    ratio = t / omt
    out = [0.0] * (degree + 1)
    value = omt**degree
    out[0] = value
    for idx in range(degree):
        value = value * ratio * (degree - idx) / (idx + 1)
        out[idx + 1] = value
    return tuple(out)


def build_section_6_1_3_boundary_triangles(
    *,
    surface_resolution: int = 12,
    side_resolution: int = 1,
) -> Section613Boundary:
    """Build Section 6.1.3 boundary patches (legacy function name kept)."""

    if surface_resolution < 2:
        raise ValueError("surface_resolution must be >= 2")
    if side_resolution < 1:
        raise ValueError("side_resolution must be >= 1")
    return Section613Boundary(
        surface_resolution=surface_resolution,
        side_resolution=side_resolution,
    )


def _seed_grid_3d(size: int) -> tuple[Point3D, ...]:
    return _core_seed_grid_3d(size)


def _same_seed(a: Point3D, b: Point3D, *, tol: float = 1.0e-12) -> bool:
    return (
        abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol
    )


def _folded_seeds_without_jplus(
    seeds: tuple[Point3D, ...],
    *,
    jplus_seed: Point3D,
) -> tuple[Point3D, ...]:
    return _core_folded_seeds_without_jplus(seeds, jplus_seed=jplus_seed)


def _tetra_volume_sum(boundary: Section613Boundary, seed: Point3D) -> float:
    _ = seed
    surface_order = max(8, boundary.surface_resolution)
    surface = _surface_rule(boundary, order=surface_order)
    total = 0.0
    for point, weighted_normal in zip(
        surface.points,
        surface.weighted_normals,
        strict=True,
    ):
        total += _dot(point, weighted_normal) / 3.0
    return total


def _integrate_bernstein_over_boundary(
    boundary: Section613Boundary,
    *,
    seed: Point3D,
    degree: int,
    order: int,
) -> tuple[float, ...]:
    points, weights = _folded_volume_rule(boundary, seed=seed, order=order)
    count = degree + 1
    out_size = count * count * count
    totals = [0.0] * out_size
    for point, weight in zip(points, weights, strict=True):
        bx = _bernstein_all(degree, point[0])
        by = _bernstein_all(degree, point[1])
        bz = _bernstein_all(degree, point[2])
        for i in range(count):
            for j in range(count):
                base = (i * count + j) * count
                wij = weight * bx[i] * by[j]
                for k in range(count):
                    totals[base + k] += wij * bz[k]
    return tuple(totals)


def section_6_2_integrand_3d(x: Any, y: Any, z: Any) -> Any:
    if _np is not None:
        return _np.exp(y) * _np.sin(x) * _np.cos(y) * _np.cos(z)
    return exp(y) * sin(x) * cos(y) * cos(z)


def _integrate_general_over_boundary(
    boundary: Section613Boundary,
    *,
    seed: Point3D,
    order: int,
) -> float:
    return integrate_general_over_section_6_1_3_boundary(
        boundary,
        seed=seed,
        order=order,
        integrand=section_6_2_integrand_3d,
    )


def integrate_general_over_section_6_1_3_boundary(
    boundary: Section613Boundary,
    *,
    seed: Point3D,
    order: int,
    integrand: Any,
) -> float:
    points, weights = _folded_volume_rule(boundary, seed=seed, order=order)
    total = 0.0
    for point, weight in zip(points, weights, strict=True):
        total += float(integrand(point[0], point[1], point[2])) * weight
    return total


def _max_abs(values: tuple[float, ...]) -> float:
    return max(abs(value) for value in values)


def _max_abs_diff(a: tuple[float, ...], b: tuple[float, ...]) -> float:
    return max(abs(x - y) for x, y in zip(a, b))


@dataclass(frozen=True)
class Polynomial3DDegreeResult:
    degree: int
    orders: tuple[int, ...]
    folded_worst_abs_error: tuple[float, ...]
    folded_best_abs_error: tuple[float, ...]
    jplus_abs_error: tuple[float, ...]


@dataclass(frozen=True)
class Polynomial3DExperimentResult:
    seed_grid_size: int
    surface_resolution: int
    reference_order: int
    jplus_seed: Point3D
    domain_volume: float
    degree_results: tuple[Polynomial3DDegreeResult, ...]


def run_polynomial_experiment_3d(
    *,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    reference_order: int = 16,
    seed_grid_size: int = 5,
    surface_resolution: int = 10,
    side_resolution: int = 1,
    jplus_seed: Point3D = (1.0, 1.0, 0.5),
) -> Polynomial3DExperimentResult:
    """Run Section 6.1.3-style 3D polynomial tests."""

    boundary = build_section_6_1_3_boundary_triangles(
        surface_resolution=surface_resolution,
        side_resolution=side_resolution,
    )
    domain_volume = _tetra_volume_sum(boundary, jplus_seed)

    seeds = _seed_grid_3d(seed_grid_size)
    folded_seeds = _folded_seeds_without_jplus(seeds, jplus_seed=jplus_seed)

    degree_results: list[Polynomial3DDegreeResult] = []
    for degree in degrees:
        jplus_ref = _integrate_bernstein_over_boundary(
            boundary,
            seed=jplus_seed,
            degree=degree,
            order=reference_order,
        )

        j_curve: list[float] = []
        f_worst_curve: list[float] = []
        f_best_curve: list[float] = []

        for order in orders:
            j_val = _integrate_bernstein_over_boundary(
                boundary,
                seed=jplus_seed,
                degree=degree,
                order=order,
            )
            j_curve.append(_max_abs_diff(j_val, jplus_ref))

            seed_errors: list[float] = []
            for seed in folded_seeds:
                f_val = _integrate_bernstein_over_boundary(
                    boundary,
                    seed=seed,
                    degree=degree,
                    order=order,
                )
                seed_errors.append(_max_abs_diff(f_val, jplus_ref))

            f_worst_curve.append(max(seed_errors))
            f_best_curve.append(min(seed_errors))

        degree_results.append(
            Polynomial3DDegreeResult(
                degree=degree,
                orders=orders,
                folded_worst_abs_error=tuple(f_worst_curve),
                folded_best_abs_error=tuple(f_best_curve),
                jplus_abs_error=tuple(j_curve),
            )
        )

    return Polynomial3DExperimentResult(
        seed_grid_size=seed_grid_size,
        surface_resolution=surface_resolution,
        reference_order=reference_order,
        jplus_seed=jplus_seed,
        domain_volume=domain_volume,
        degree_results=tuple(degree_results),
    )


@dataclass(frozen=True)
class General3DOrderResult:
    order: int
    folded_worst_abs_error: float
    folded_best_abs_error: float
    jplus_abs_error: float


@dataclass(frozen=True)
class General3DExperimentResult:
    reference_order: int
    seed_grid_size: int
    surface_resolution: int
    reference_value: float
    orders: tuple[General3DOrderResult, ...]


def run_general_function_experiment_3d(
    *,
    orders: tuple[int, ...],
    reference_order: int = 16,
    seed_grid_size: int = 5,
    surface_resolution: int = 10,
    side_resolution: int = 1,
    jplus_seed: Point3D = (1.0, 1.0, 0.5),
) -> General3DExperimentResult:
    """Run a 3D Section 6.2-style order sweep on the Section 6.1.3 geometry."""

    boundary = build_section_6_1_3_boundary_triangles(
        surface_resolution=surface_resolution,
        side_resolution=side_resolution,
    )
    seeds = _seed_grid_3d(seed_grid_size)
    folded_seeds = _folded_seeds_without_jplus(seeds, jplus_seed=jplus_seed)

    reference = _integrate_general_over_boundary(
        boundary,
        seed=jplus_seed,
        order=reference_order,
    )
    results: list[General3DOrderResult] = []
    for order in orders:
        j_val = _integrate_general_over_boundary(
            boundary,
            seed=jplus_seed,
            order=order,
        )
        j_err = abs(j_val - reference)

        seed_errors: list[float] = []
        for seed in folded_seeds:
            val = _integrate_general_over_boundary(
                boundary,
                seed=seed,
                order=order,
            )
            seed_errors.append(abs(val - reference))

        results.append(
            General3DOrderResult(
                order=order,
                folded_worst_abs_error=max(seed_errors),
                folded_best_abs_error=min(seed_errors),
                jplus_abs_error=j_err,
            )
        )

    return General3DExperimentResult(
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
        surface_resolution=surface_resolution,
        reference_value=reference,
        orders=tuple(results),
    )


def _integrate_general_over_cartesian_grid_3d(
    *,
    resolution: int,
    order: int,
) -> float:
    """Integrate the 3D Section 6.2 integrand over Cartesian cut-cells.

    Paper-parity protocol: the curved boundary is queried via the Section 6.1.3
    bi-quadratic surface projection ``x = x_s(y, z)`` and each Cartesian cell is
    integrated elementwise.
    """

    return _core_integrate_cartesian(
        resolution=resolution,
        order=order,
        x_surface_from_yz=_x_surface_from_yz,
        integrand=section_6_2_integrand_3d,
    )


@dataclass(frozen=True)
class General3DGridOrderResult:
    order: int
    grid_resolutions: tuple[int, ...]
    h_values: tuple[float, ...]
    folded_abs_error: tuple[float, ...]
    folded_rel_error: tuple[float, ...]
    monotone_nonincreasing: bool
    monotonicity_violation_indices: tuple[int, ...]


@dataclass(frozen=True)
class General3DGridExperimentResult:
    reference_grid_resolution: int
    reference_order: int
    reference_value: float
    order_results: tuple[General3DGridOrderResult, ...]


def _monotonicity_violations(values: tuple[float, ...]) -> tuple[int, ...]:
    violations: list[int] = []
    for index in range(len(values) - 1):
        if values[index + 1] > values[index]:
            violations.append(index)
    return tuple(violations)


def run_general_function_experiment_3d_grid(
    *,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...] = (2, 4, 8, 16, 32, 64),
    reference_grid_resolution: int = 128,
    reference_order: int = 48,
) -> General3DGridExperimentResult:
    """Run Section 6.2 3D Cartesian cut-cell refinement protocol."""

    if not orders:
        raise ValueError("orders must not be empty")
    if any(order < 1 for order in orders):
        raise ValueError("orders must contain positive integers")
    if not grid_resolutions:
        raise ValueError("grid_resolutions must not be empty")
    if any(resolution < 1 for resolution in grid_resolutions):
        raise ValueError("grid_resolutions must contain positive integers")
    if any(
        grid_resolutions[index + 1] <= grid_resolutions[index]
        for index in range(len(grid_resolutions) - 1)
    ):
        raise ValueError("grid_resolutions must be strictly increasing")
    if reference_grid_resolution <= grid_resolutions[-1]:
        raise ValueError("reference_grid_resolution must be > max(grid_resolutions)")
    if reference_order <= max(orders):
        raise ValueError("reference_order must be greater than all sweep orders")

    reference = _integrate_general_over_cartesian_grid_3d(
        resolution=reference_grid_resolution,
        order=reference_order,
    )
    scale = max(abs(reference), 1.0e-30)

    h_values = tuple(1.0 / resolution for resolution in grid_resolutions)
    order_results: list[General3DGridOrderResult] = []

    for order in orders:
        abs_errors: list[float] = []
        for resolution in grid_resolutions:
            value = _integrate_general_over_cartesian_grid_3d(
                resolution=resolution,
                order=order,
            )
            abs_errors.append(abs(value - reference))

        rel_errors = tuple(error / scale for error in abs_errors)
        violations = _monotonicity_violations(tuple(abs_errors))
        order_results.append(
            General3DGridOrderResult(
                order=order,
                grid_resolutions=grid_resolutions,
                h_values=h_values,
                folded_abs_error=tuple(abs_errors),
                folded_rel_error=rel_errors,
                monotone_nonincreasing=not violations,
                monotonicity_violation_indices=violations,
            )
        )

    return General3DGridExperimentResult(
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
        reference_value=reference,
        order_results=tuple(order_results),
    )
