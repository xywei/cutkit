"""Core 3D folded quadrature utilities."""

from __future__ import annotations

import importlib.util
from functools import lru_cache
from typing import Any, Callable, cast

from cutkit.geometry import FoldedBoundaryCell3D, Point3D, Triangle3D

from .folded2d import gauss_legendre_01
from .rule3d import QuadratureRule3D

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None


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


@lru_cache(maxsize=64)
def _duffy_nodes_3d(order: int) -> tuple[Any, Any, Any, Any]:
    if order < 1:
        raise ValueError("order must be positive")

    nodes, weights = gauss_legendre_01(order)

    if _np is not None:
        n = _np.asarray(nodes, dtype=float)
        w = _np.asarray(weights, dtype=float)
        rr, ss, tt = _np.meshgrid(n, n, n, indexing="ij")
        wr, ws, wt = _np.meshgrid(w, w, w, indexing="ij")

        one_minus_r = 1.0 - rr
        uu = rr
        vv = ss * one_minus_r
        ww = tt * one_minus_r * (1.0 - ss)
        jac = one_minus_r * one_minus_r * (1.0 - ss) * wr * ws * wt
        uu_arr = cast(Any, uu)
        vv_arr = cast(Any, vv)
        ww_arr = cast(Any, ww)
        jac_arr = cast(Any, jac)
        return (
            uu_arr.reshape(-1),
            vv_arr.reshape(-1),
            ww_arr.reshape(-1),
            jac_arr.reshape(-1),
        )

    uu_list: list[float] = []
    vv_list: list[float] = []
    ww_list: list[float] = []
    jac_list: list[float] = []
    for r, wr in zip(nodes, weights):
        one_minus_r = 1.0 - r
        for s, ws in zip(nodes, weights):
            one_minus_s = 1.0 - s
            for t, wt in zip(nodes, weights):
                uu_list.append(r)
                vv_list.append(s * one_minus_r)
                ww_list.append(t * one_minus_r * one_minus_s)
                jac_list.append(one_minus_r * one_minus_r * one_minus_s * wr * ws * wt)
    return tuple(uu_list), tuple(vv_list), tuple(ww_list), tuple(jac_list)


def _bernstein_all(p: int, t: float) -> tuple[float, ...]:
    if t <= 0.0:
        out = [0.0] * (p + 1)
        out[0] = 1.0
        return tuple(out)
    if t >= 1.0:
        out = [0.0] * (p + 1)
        out[p] = 1.0
        return tuple(out)

    omt = 1.0 - t
    ratio = t / omt
    out = [0.0] * (p + 1)
    value = omt**p
    out[0] = value
    for i in range(p):
        value = value * ratio * (p - i) / (i + 1)
        out[i + 1] = value
    return tuple(out)


def _bernstein_matrix_numpy(p: int, t_values: Any) -> Any:
    assert _np is not None
    t = _np.asarray(t_values, dtype=float)
    out = _np.zeros((t.size, p + 1), dtype=float)

    low = t <= 0.0
    high = t >= 1.0
    mid = ~(low | high)

    out[low, 0] = 1.0
    out[high, p] = 1.0

    if _np.any(mid):
        tm = t[mid]
        omt = 1.0 - tm
        ratio = tm / omt
        value = omt**p
        out_mid = out[mid]
        out_mid[:, 0] = value
        for i in range(p):
            value = value * ratio * (p - i) / (i + 1)
            out_mid[:, i + 1] = value
        out[mid] = out_mid

    return out


def seed_grid_3d(size: int) -> tuple[Point3D, ...]:
    """Return a deterministic Cartesian seed grid over ``[0, 1]^3``."""

    if size < 2:
        raise ValueError("seed grid size must be >= 2")

    seeds: list[Point3D] = []
    for i in range(size):
        x = i / (size - 1)
        for j in range(size):
            y = j / (size - 1)
            for k in range(size):
                z = k / (size - 1)
                seeds.append((x, y, z))
    return tuple(seeds)


def same_seed_3d(a: Point3D, b: Point3D, *, tol: float = 1.0e-12) -> bool:
    """Return whether two seeds are equal within tolerance."""

    return (
        abs(a[0] - b[0]) <= tol and abs(a[1] - b[1]) <= tol and abs(a[2] - b[2]) <= tol
    )


def folded_seeds_without_jplus_3d(
    seeds: tuple[Point3D, ...], *, jplus_seed: Point3D
) -> tuple[Point3D, ...]:
    """Exclude the jplus seed from folded seed sweeps."""

    filtered = tuple(seed for seed in seeds if not same_seed_3d(seed, jplus_seed))
    if not filtered:
        raise ValueError("seed grid must include at least one non-jplus folded seed")
    return filtered


def folded_boundary_cells_3d(
    boundary: tuple[Triangle3D, ...], *, seed: Point3D
) -> tuple[FoldedBoundaryCell3D, ...]:
    """Build one seed-anchored folded cell descriptor per boundary triangle."""

    return tuple(
        FoldedBoundaryCell3D(seed=seed, triangle=triangle) for triangle in boundary
    )


def signed_boundary_volume_3d(
    boundary: tuple[Triangle3D, ...], *, seed: Point3D
) -> float:
    """Return signed volume from a seed-anchored boundary tetra sum."""

    total = 0.0
    for a, b, c in boundary:
        av = _sub(a, seed)
        bv = _sub(b, seed)
        cv = _sub(c, seed)
        total += _dot(av, _cross(bv, cv)) / 6.0
    return total


def boundary_quadrature_rule_3d(
    boundary: tuple[Triangle3D, ...], *, seed: Point3D, order: int
) -> QuadratureRule3D:
    """Build a deterministic 3D quadrature rule over folded boundary cells."""

    u, v, w, jac = _duffy_nodes_3d(order)
    points: list[Point3D] = []
    weights: list[float] = []

    for a, b, c in boundary:
        av = _sub(a, seed)
        bv = _sub(b, seed)
        cv = _sub(c, seed)
        det = _dot(av, _cross(bv, cv))

        for q in range(len(u)):
            x = seed[0] + av[0] * u[q] + bv[0] * v[q] + cv[0] * w[q]
            y = seed[1] + av[1] * u[q] + bv[1] * v[q] + cv[1] * w[q]
            z = seed[2] + av[2] * u[q] + bv[2] * v[q] + cv[2] * w[q]
            points.append((x, y, z))
            weights.append(det * jac[q])

    return QuadratureRule3D(points=tuple(points), weights=tuple(weights))


def integrate_bernstein_over_boundary_3d(
    boundary: tuple[Triangle3D, ...],
    *,
    seed: Point3D,
    degree: int,
    order: int,
) -> tuple[float, ...]:
    """Integrate 3D Bernstein tensor basis over one folded boundary volume."""

    count = degree + 1
    out_size = count * count * count

    u, v, w, jac = _duffy_nodes_3d(order)

    if _np is not None:
        u = _np.asarray(u, dtype=float)
        v = _np.asarray(v, dtype=float)
        w = _np.asarray(w, dtype=float)
        jac = _np.asarray(jac, dtype=float)

        tris = _np.asarray(boundary, dtype=float)
        a = tris[:, 0, :]
        b = tris[:, 1, :]
        c = tris[:, 2, :]

        s = _np.asarray(seed, dtype=float)
        av = a - s
        bv = b - s
        cv = c - s
        det = _np.einsum("ij,ij->i", av, _np.cross(bv, cv))

        x = (
            s[0]
            + av[:, 0, None] * u[None, :]
            + bv[:, 0, None] * v[None, :]
            + cv[:, 0, None] * w[None, :]
        )
        y = (
            s[1]
            + av[:, 1, None] * u[None, :]
            + bv[:, 1, None] * v[None, :]
            + cv[:, 1, None] * w[None, :]
        )
        z = (
            s[2]
            + av[:, 2, None] * u[None, :]
            + bv[:, 2, None] * v[None, :]
            + cv[:, 2, None] * w[None, :]
        )
        wt = det[:, None] * jac[None, :]

        xf = x.reshape(-1)
        yf = y.reshape(-1)
        zf = z.reshape(-1)
        wf = wt.reshape(-1)

        bx = _bernstein_matrix_numpy(degree, xf)
        by = _bernstein_matrix_numpy(degree, yf)
        bz = _bernstein_matrix_numpy(degree, zf)
        values = _np.einsum("n,ni,nj,nk->ijk", wf, bx, by, bz, optimize=True)
        return tuple(values.reshape(out_size).tolist())

    totals = [0.0] * out_size
    for a, b, c in boundary:
        av = _sub(a, seed)
        bv = _sub(b, seed)
        cv = _sub(c, seed)
        det = _dot(av, _cross(bv, cv))

        for q in range(len(u)):
            x = seed[0] + av[0] * u[q] + bv[0] * v[q] + cv[0] * w[q]
            y = seed[1] + av[1] * u[q] + bv[1] * v[q] + cv[1] * w[q]
            z = seed[2] + av[2] * u[q] + bv[2] * v[q] + cv[2] * w[q]
            weight = det * jac[q]

            bx = _bernstein_all(degree, x)
            by = _bernstein_all(degree, y)
            bz = _bernstein_all(degree, z)
            for i in range(count):
                for j in range(count):
                    base = (i * count + j) * count
                    wij = weight * bx[i] * by[j]
                    for k in range(count):
                        totals[base + k] += wij * bz[k]

    return tuple(totals)


def integrate_general_over_boundary_3d(
    boundary: tuple[Triangle3D, ...],
    *,
    seed: Point3D,
    order: int,
    integrand: Callable[[Any, Any, Any], Any],
) -> float:
    """Integrate a general integrand over one folded boundary volume."""

    u, v, w, jac = _duffy_nodes_3d(order)

    if _np is not None:
        u = _np.asarray(u, dtype=float)
        v = _np.asarray(v, dtype=float)
        w = _np.asarray(w, dtype=float)
        jac = _np.asarray(jac, dtype=float)

        tris = _np.asarray(boundary, dtype=float)
        a = tris[:, 0, :]
        b = tris[:, 1, :]
        c = tris[:, 2, :]
        s = _np.asarray(seed, dtype=float)

        av = a - s
        bv = b - s
        cv = c - s
        det = _np.einsum("ij,ij->i", av, _np.cross(bv, cv))

        x = (
            s[0]
            + av[:, 0, None] * u[None, :]
            + bv[:, 0, None] * v[None, :]
            + cv[:, 0, None] * w[None, :]
        )
        y = (
            s[1]
            + av[:, 1, None] * u[None, :]
            + bv[:, 1, None] * v[None, :]
            + cv[:, 1, None] * w[None, :]
        )
        z = (
            s[2]
            + av[:, 2, None] * u[None, :]
            + bv[:, 2, None] * v[None, :]
            + cv[:, 2, None] * w[None, :]
        )
        wt = det[:, None] * jac[None, :]

        try:
            values = integrand(x, y, z)
            return float(_np.sum(values * wt))
        except TypeError:
            total = 0.0
            for tri_index in range(x.shape[0]):
                for quad_index in range(x.shape[1]):
                    total += float(
                        integrand(
                            float(x[tri_index, quad_index]),
                            float(y[tri_index, quad_index]),
                            float(z[tri_index, quad_index]),
                        )
                    ) * float(wt[tri_index, quad_index])
            return total

    total = 0.0
    for a, b, c in boundary:
        av = _sub(a, seed)
        bv = _sub(b, seed)
        cv = _sub(c, seed)
        det = _dot(av, _cross(bv, cv))

        for q in range(len(u)):
            x = seed[0] + av[0] * u[q] + bv[0] * v[q] + cv[0] * w[q]
            y = seed[1] + av[1] * u[q] + bv[1] * v[q] + cv[1] * w[q]
            z = seed[2] + av[2] * u[q] + bv[2] * v[q] + cv[2] * w[q]
            total += float(integrand(x, y, z)) * det * jac[q]
    return total


def integrate_general_over_cartesian_grid_xsurface_3d(
    *,
    resolution: int,
    order: int,
    x_surface_from_yz: Callable[[float, float], float | None],
    integrand: Callable[[Any, Any, Any], Any],
) -> float:
    """Integrate over Cartesian cut-cells induced by ``x = x_s(y, z)``."""

    if resolution < 1:
        raise ValueError("resolution must be positive")

    nodes, weights = gauss_legendre_01(order)
    h = 1.0 / resolution

    if _np is not None:
        nodes_arr = _np.asarray(nodes, dtype=float)
        weights_arr = _np.asarray(weights, dtype=float)
    else:
        nodes_arr = nodes
        weights_arr = weights

    total = 0.0
    for iy in range(resolution):
        y0 = iy * h
        y_nodes = tuple(y0 + float(node) * h for node in nodes_arr)
        y_weights = tuple(float(weight) * h for weight in weights_arr)

        for iz in range(resolution):
            z0 = iz * h
            z_nodes = tuple(z0 + float(node) * h for node in nodes_arr)
            z_weights = tuple(float(weight) * h for weight in weights_arr)

            for jy, y in enumerate(y_nodes):
                wy = y_weights[jy]
                for jz, z in enumerate(z_nodes):
                    wz = z_weights[jz]
                    yz_weight = wy * wz

                    x_surface = x_surface_from_yz(y, z)
                    if x_surface is None or x_surface >= 1.0:
                        continue

                    start_ix = int(x_surface / h)
                    if start_ix < 0:
                        start_ix = 0
                    if start_ix >= resolution:
                        continue

                    if _np is not None:
                        nodes_np = cast(Any, nodes_arr)
                        weights_np = cast(Any, weights_arr)
                        x0s = _np.arange(start_ix, resolution, dtype=float) * h
                        left = _np.maximum(x0s, x_surface)
                        right = x0s + h
                        widths = right - left
                        valid = widths > 0.0
                        if not _np.any(valid):
                            continue

                        left = left[valid]
                        widths = widths[valid]
                        left_np = cast(Any, left)
                        widths_np = cast(Any, widths)
                        x_samples = (
                            left_np[None, :] + nodes_np[:, None] * widths_np[None, :]
                        )
                        try:
                            vals = integrand(x_samples, y, z)
                            x_integrals = _np.sum(
                                vals * (weights_np[:, None] * widths_np[None, :]),
                                axis=0,
                            )
                            total += yz_weight * float(_np.sum(x_integrals))
                        except TypeError:
                            for interval in range(x_samples.shape[1]):
                                width = float(widths_np[interval])
                                for qx, node in enumerate(nodes_np):
                                    x_value = float(left_np[interval] + node * width)
                                    wx = float(weights_np[qx]) * width
                                    total += (
                                        yz_weight * wx * float(integrand(x_value, y, z))
                                    )
                    else:
                        for ix in range(start_ix, resolution):
                            x0 = ix * h
                            x1 = x0 + h
                            left = x0 if x0 >= x_surface else x_surface
                            if left >= x1:
                                continue
                            width = x1 - left
                            for qx, node in enumerate(nodes_arr):
                                x = left + float(node) * width
                                wx = float(weights_arr[qx]) * width
                                total += yz_weight * wx * float(integrand(x, y, z))

    return total
