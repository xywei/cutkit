"""3D reproductions for Antolin-Wei-Buffa (2022, Section 6).

Source and credit:
- Pablo Antolin, Xiaodong Wei, Annalisa Buffa (2022)
- "Robust Numerical Integration on Curved Polyhedra Based on Folded Decompositions"
- Computer Methods in Applied Mechanics and Engineering
- DOI: 10.1016/j.cma.2022.114948
- arXiv: https://arxiv.org/abs/2109.03734

This module targets the 3D geometry from Section 6.1.3 (single parent cell)
and provides CUTKIT-adapted polynomial and general-function experiments.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from functools import lru_cache
from math import cos, exp, sin
from typing import Any

from cutkit.quadrature import (
    folded_seeds_without_jplus_3d as _core_folded_seeds_without_jplus,
    integrate_bernstein_over_boundary_3d as _core_integrate_bernstein_over_boundary,
    integrate_general_over_boundary_3d as _core_integrate_general_over_boundary,
    integrate_general_over_cartesian_grid_xsurface_3d as _core_integrate_cartesian,
    seed_grid_3d as _core_seed_grid_3d,
    signed_boundary_volume_3d as _core_signed_boundary_volume,
)
from cutkit.topology import orient_boundary_triangles_outward as _core_orient_outward

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

Point3D = tuple[float, float, float]
Triangle3D = tuple[Point3D, Point3D, Point3D]


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


@lru_cache(maxsize=200000)
def _x_surface_from_yz(y_target: float, z_target: float) -> float | None:
    """Solve for x_s(y,z) on the curved face; return None if outside projection."""

    if y_target < _Y_MIN - 1.0e-10 or y_target > _Y_MAX + 1.0e-10:
        return None
    if z_target < _Z_MIN - 1.0e-10 or z_target > _Z_MAX + 1.0e-10:
        return None

    seeds = _projection_seed_samples()
    nearest = sorted(
        seeds,
        key=lambda item: (item[0] - y_target) ** 2 + (item[1] - z_target) ** 2,
    )[:6]

    best_x: float | None = None
    best_res_sq = float("inf")

    for _, _, u0, v0 in nearest:
        u = u0
        v = v0
        for _ in range(30):
            x, y, z, dy_du, dy_dv, dz_du, dz_dv = _eval_surface_with_yz_partials(u, v)
            fy = y - y_target
            fz = z - z_target
            res_sq = fy * fy + fz * fz
            if res_sq < best_res_sq:
                best_res_sq = res_sq
                best_x = x

            if res_sq <= (1.0e-12) ** 2:
                return x

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

    if best_x is not None and best_res_sq <= (5.0e-8) ** 2:
        return best_x
    return None


def _x1_face_point(u: float, v: float) -> Point3D:
    sx, sy, sz = eval_section_6_1_3_bezier_surface(u, v)
    return (1.0, sy, sz)


def _grid_points(
    evaluator: Any,
    *,
    nu: int,
    nv: int,
) -> list[list[Point3D]]:
    grid: list[list[Point3D]] = []
    for i in range(nu + 1):
        u = i / nu
        row: list[Point3D] = []
        for j in range(nv + 1):
            v = j / nv
            row.append(evaluator(u, v))
        grid.append(row)
    return grid


def _triangulate_grid(points: list[list[Point3D]]) -> list[Triangle3D]:
    nu = len(points) - 1
    nv = len(points[0]) - 1
    tris: list[Triangle3D] = []
    for i in range(nu):
        for j in range(nv):
            p00 = points[i][j]
            p10 = points[i + 1][j]
            p01 = points[i][j + 1]
            p11 = points[i + 1][j + 1]
            tris.append((p00, p10, p11))
            tris.append((p00, p11, p01))
    return tris


def _orient_outward(
    tris: list[Triangle3D], *, tol: float = 1.0e-12
) -> tuple[Triangle3D, ...]:
    return _core_orient_outward(tuple(tris), tol=tol, validate_closed=False)


def build_section_6_1_3_boundary_triangles(
    *,
    surface_resolution: int = 12,
    side_resolution: int = 1,
) -> tuple[Triangle3D, ...]:
    """Build an oriented boundary triangulation for the Section 6.1.3 volume."""

    if surface_resolution < 2:
        raise ValueError("surface_resolution must be >= 2")
    if side_resolution < 1:
        raise ValueError("side_resolution must be >= 1")
    if side_resolution != 1:
        raise ValueError(
            "side_resolution must be 1; higher values create non-conforming "
            "side-face refinements"
        )

    # Curved face (r=0) and opposite planar face (x=1)
    curved = _triangulate_grid(
        _grid_points(
            eval_section_6_1_3_bezier_surface,
            nu=surface_resolution,
            nv=surface_resolution,
        )
    )
    x1 = _triangulate_grid(
        _grid_points(_x1_face_point, nu=surface_resolution, nv=surface_resolution)
    )

    # z=0 face (v=0 boundary extruded to x=1)
    def z0_face(u: float, r: float) -> Point3D:
        c0 = eval_section_6_1_3_bezier_surface(u, 0.0)
        return _lerp(c0, (1.0, c0[1], c0[2]), r)

    # z=1 face (v=1 boundary extruded to x=1)
    def z1_face(u: float, r: float) -> Point3D:
        c1 = eval_section_6_1_3_bezier_surface(u, 1.0)
        return _lerp(c1, (1.0, c1[1], c1[2]), r)

    # y=1 face (u=1 boundary extruded to x=1)
    def y1_face(v: float, r: float) -> Point3D:
        c = eval_section_6_1_3_bezier_surface(1.0, v)
        return _lerp(c, (1.0, c[1], c[2]), r)

    z0 = _triangulate_grid(
        _grid_points(z0_face, nu=surface_resolution, nv=side_resolution)
    )
    z1 = _triangulate_grid(
        _grid_points(z1_face, nu=surface_resolution, nv=side_resolution)
    )
    y1 = _triangulate_grid(
        _grid_points(y1_face, nu=surface_resolution, nv=side_resolution)
    )

    all_tris = [*curved, *x1, *z0, *z1, *y1]
    return _orient_outward(all_tris)


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


def _tetra_volume_sum(boundary: tuple[Triangle3D, ...], seed: Point3D) -> float:
    return _core_signed_boundary_volume(boundary, seed=seed)


def _integrate_bernstein_over_boundary(
    boundary: tuple[Triangle3D, ...],
    *,
    seed: Point3D,
    degree: int,
    order: int,
) -> tuple[float, ...]:
    return _core_integrate_bernstein_over_boundary(
        boundary,
        seed=seed,
        degree=degree,
        order=order,
    )


def section_6_2_integrand_3d(x: Any, y: Any, z: Any) -> Any:
    if _np is not None:
        return _np.exp(y) * _np.sin(x) * _np.cos(y) * _np.cos(z)
    return exp(y) * sin(x) * cos(y) * cos(z)


def _integrate_general_over_boundary(
    boundary: tuple[Triangle3D, ...],
    *,
    seed: Point3D,
    order: int,
) -> float:
    return _core_integrate_general_over_boundary(
        boundary,
        seed=seed,
        order=order,
        integrand=section_6_2_integrand_3d,
    )


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

    CUTKIT-adapted protocol: the curved boundary is queried via the Section 6.1.3
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
