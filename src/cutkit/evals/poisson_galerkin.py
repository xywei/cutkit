"""Immersed Poisson Galerkin/IGA solver and solver-level validation workflows."""

from __future__ import annotations

from dataclasses import dataclass
from math import pi, sin, sqrt
from typing import Any, Callable, Literal

from cutkit.geometry import TrimmedPanel2D
from cutkit.quadrature import gauss_legendre_01

from . import antolin_wei_buffa_2022_2d as awb2d

BackendMode = Literal["jplus", "folded"]
ProfileName = Literal["quick", "dense"]


@dataclass(frozen=True)
class PoissonGalerkinProfile:
    """Profile configuration for immersed Poisson Galerkin validation runs."""

    name: ProfileName
    grid_resolutions: tuple[int, ...]
    spline_degree: int
    quadrature_order: int
    reference_quadrature_order: int
    abs_tolerance: float
    rel_tolerance: float


@dataclass(frozen=True)
class PoissonGalerkinSolveResult:
    """One immersed Poisson solve over a trimmed domain and spline background."""

    resolution: int
    spline_degree: int
    quadrature_order: int
    backend_mode: BackendMode
    dof_count: int
    active_dof_count: int
    free_dof_count: int
    cg_iterations: int
    residual_norm: float
    coefficients: tuple[float, ...]
    solution: tuple[float, ...]


@dataclass(frozen=True)
class PoissonGalerkinGeometrySnapshot:
    """Geometry and clipped-cell snapshot for figure generation."""

    resolution: int
    bounds: tuple[float, float, float, float]
    panel_polygon: tuple[tuple[float, float], ...]
    clipped_cells: tuple[awb2d.CellClipResult, ...]
    inside_cell_count: int
    trimmed_cell_count: int


@dataclass(frozen=True)
class PoissonGalerkinResolutionResult:
    """Error and solver diagnostics for one grid-resolution row."""

    resolution: int
    spline_degree: int
    quadrature_order: int
    abs_error: float
    rel_error: float
    reference_scale: float
    threshold: float
    residual_norm: float
    cg_iterations: int
    free_dof_count: int


@dataclass(frozen=True)
class PoissonGalerkinBenchmarkResult:
    """Profile-level immersed Poisson Galerkin benchmark output."""

    profile: ProfileName
    backend_mode: BackendMode
    spline_degree: int
    reference_quadrature_order: int
    rows: tuple[PoissonGalerkinResolutionResult, ...]
    passed: bool

    def to_manifest(self) -> dict[str, Any]:
        return {
            "schema_version": 1,
            "profile": self.profile,
            "backend_mode": self.backend_mode,
            "spline_degree": self.spline_degree,
            "reference_quadrature_order": self.reference_quadrature_order,
            "passed": self.passed,
            "rows": [
                {
                    "resolution": row.resolution,
                    "spline_degree": row.spline_degree,
                    "quadrature_order": row.quadrature_order,
                    "abs_error": row.abs_error,
                    "rel_error": row.rel_error,
                    "reference_scale": row.reference_scale,
                    "threshold": row.threshold,
                    "residual_norm": row.residual_norm,
                    "cg_iterations": row.cg_iterations,
                    "free_dof_count": row.free_dof_count,
                }
                for row in self.rows
            ],
        }


PROFILES: dict[ProfileName, PoissonGalerkinProfile] = {
    "quick": PoissonGalerkinProfile(
        name="quick",
        grid_resolutions=(8, 16),
        spline_degree=2,
        quadrature_order=4,
        reference_quadrature_order=6,
        abs_tolerance=2.0e-4,
        rel_tolerance=2.0e-3,
    ),
    "dense": PoissonGalerkinProfile(
        name="dense",
        grid_resolutions=(8, 16, 32),
        spline_degree=2,
        quadrature_order=5,
        reference_quadrature_order=8,
        abs_tolerance=1.0e-4,
        rel_tolerance=1.0e-3,
    ),
}


def default_poisson_source(x: float, y: float) -> float:
    """Manufactured forcing used for immersed Poisson Galerkin validation."""

    return 2.0 * pi * pi * sin(pi * x) * sin(pi * y)


def _node_index(ix: int, iy: int, *, resolution: int) -> int:
    return iy * (resolution + 1) + ix


def _normalize(value: float, *, vmin: float, vmax: float) -> float:
    if vmax <= vmin:
        raise ValueError("invalid bounds for normalization")
    normalized = (value - vmin) / (vmax - vmin)
    if normalized < 0.0:
        return 0.0
    if normalized > 1.0:
        return 1.0
    return normalized


def _open_uniform_knots(*, num_elements: int, degree: int) -> tuple[float, ...]:
    if num_elements < 1:
        raise ValueError("num_elements must be positive")
    if degree < 1:
        raise ValueError("degree must be positive")

    knots = [0.0] * (degree + 1)
    for interior in range(1, num_elements):
        knots.append(interior / num_elements)
    knots.extend([1.0] * (degree + 1))
    return tuple(knots)


def _span_from_param(t: float, *, resolution: int, degree: int) -> int:
    element = int(t * resolution)
    if element < 0:
        element = 0
    elif element >= resolution:
        element = resolution - 1
    return degree + element


def _basis_funs(
    *,
    span: int,
    t: float,
    degree: int,
    knots: tuple[float, ...],
) -> tuple[float, ...]:
    basis = [0.0 for _ in range(degree + 1)]
    left = [0.0 for _ in range(degree + 1)]
    right = [0.0 for _ in range(degree + 1)]
    basis[0] = 1.0

    for j in range(1, degree + 1):
        left[j] = t - knots[span + 1 - j]
        right[j] = knots[span + j] - t
        saved = 0.0

        for r in range(j):
            denom = right[r + 1] + left[j - r]
            temp = 0.0 if abs(denom) <= 1.0e-15 else basis[r] / denom
            basis[r] = saved + right[r + 1] * temp
            saved = left[j - r] * temp

        basis[j] = saved

    return tuple(basis)


def _basis_and_derivatives(
    *,
    span: int,
    t: float,
    degree: int,
    knots: tuple[float, ...],
) -> tuple[tuple[float, ...], tuple[float, ...]]:
    values = _basis_funs(span=span, t=t, degree=degree, knots=knots)
    if degree == 0:
        return values, (0.0,)

    lower = _basis_funs(span=span, t=t, degree=degree - 1, knots=knots)
    derivatives = [0.0 for _ in range(degree + 1)]
    for local in range(degree + 1):
        global_index = span - degree + local

        term_left = 0.0
        if local > 0:
            denom_left = knots[global_index + degree] - knots[global_index]
            if abs(denom_left) > 1.0e-15:
                term_left = degree * lower[local - 1] / denom_left

        term_right = 0.0
        if local < degree:
            denom_right = knots[global_index + degree + 1] - knots[global_index + 1]
            if abs(denom_right) > 1.0e-15:
                term_right = degree * lower[local] / denom_right

        derivatives[local] = term_left - term_right

    return values, tuple(derivatives)


def _cell_rule_samples(
    clip: awb2d.CellClipResult,
    *,
    backend_mode: BackendMode,
    order: int,
) -> tuple[tuple[float, float, float], ...]:
    if clip.kind == "inside":
        nodes, quad_weights = gauss_legendre_01(order)
        samples: list[tuple[float, float, float]] = []
        for ux, wx in zip(nodes, quad_weights):
            x = clip.cell.x0 + ux * clip.cell.width
            for uy, wy in zip(nodes, quad_weights):
                y = clip.cell.y0 + uy * clip.cell.height
                samples.append((x, y, wx * wy * clip.cell.area))
        return tuple(samples)

    if backend_mode == "jplus":
        anchor = None
        require_interior_anchor = True
    else:
        anchor = (clip.cell.x0, clip.cell.y0)
        require_interior_anchor = False

    if awb2d._np is not None:
        points_arr, weights_arr = awb2d._cached_rule_arrays(
            clip.polygon,
            order,
            anchor,
            require_interior_anchor,
        )
        return tuple(
            (
                float(points_arr[index, 0]),
                float(points_arr[index, 1]),
                float(weights_arr[index]),
            )
            for index in range(len(weights_arr))
        )

    points, weights = awb2d._cached_rule(
        clip.polygon,
        order,
        anchor,
        require_interior_anchor,
    )
    return tuple(
        (float(x), float(y), float(weight)) for (x, y), weight in zip(points, weights)
    )


def _add_to_sparse_row(row: dict[int, float], col: int, value: float) -> None:
    existing = row.get(col)
    if existing is None:
        row[col] = value
    else:
        row[col] = existing + value


def _basis_terms_at_point(
    *,
    x: float,
    y: float,
    resolution: int,
    spline_degree: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
) -> tuple[tuple[int, float, float, float], ...]:
    xmin, ymin, xmax, ymax = bounds
    tx = _normalize(x, vmin=xmin, vmax=xmax)
    ty = _normalize(y, vmin=ymin, vmax=ymax)

    span_x = _span_from_param(tx, resolution=resolution, degree=spline_degree)
    span_y = _span_from_param(ty, resolution=resolution, degree=spline_degree)
    bx, dbx_dt = _basis_and_derivatives(
        span=span_x,
        t=tx,
        degree=spline_degree,
        knots=knots_x,
    )
    by, dby_dt = _basis_and_derivatives(
        span=span_y,
        t=ty,
        degree=spline_degree,
        knots=knots_y,
    )

    inv_dx = 1.0 / (xmax - xmin)
    inv_dy = 1.0 / (ymax - ymin)
    terms: list[tuple[int, float, float, float]] = []

    ix_start = span_x - spline_degree
    iy_start = span_y - spline_degree
    for jy in range(spline_degree + 1):
        basis_y = by[jy]
        deriv_y = dby_dt[jy] * inv_dy
        global_y = iy_start + jy
        if global_y < 0 or global_y >= n_basis_axis:
            continue

        row_base = global_y * n_basis_axis
        for jx in range(spline_degree + 1):
            basis_x = bx[jx]
            deriv_x = dbx_dt[jx] * inv_dx
            global_x = ix_start + jx
            if global_x < 0 or global_x >= n_basis_axis:
                continue

            value = basis_x * basis_y
            grad_x = deriv_x * basis_y
            grad_y = basis_x * deriv_y
            terms.append((row_base + global_x, value, grad_x, grad_y))

    return tuple(terms)


def _apply_zero_dirichlet(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    fixed_mask: list[bool],
) -> tuple[int, ...]:
    fixed_indices = tuple(index for index, fixed in enumerate(fixed_mask) if fixed)
    fixed_set = set(fixed_indices)

    for index in fixed_indices:
        matrix_rows[index] = {index: 1.0}
        rhs[index] = 0.0

    for row_index, row in enumerate(matrix_rows):
        if row_index in fixed_set:
            continue
        for fixed_index in fixed_indices:
            if fixed_index in row:
                del row[fixed_index]

    return tuple(index for index, fixed in enumerate(fixed_mask) if not fixed)


def _dot(a: list[float], b: list[float]) -> float:
    return sum(x * y for x, y in zip(a, b, strict=True))


def _matvec(matrix_rows: list[dict[int, float]], vector: list[float]) -> list[float]:
    return [
        sum(value * vector[col] for col, value in row.items()) for row in matrix_rows
    ]


def _conjugate_gradient(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    tolerance: float,
    max_iterations: int | None,
) -> tuple[tuple[float, ...], int, float]:
    size = len(rhs)
    if max_iterations is None:
        max_iterations = max(8 * size, 200)
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")

    x = [0.0 for _ in range(size)]
    r = rhs.copy()
    p = r.copy()

    rhs_norm = sqrt(_dot(rhs, rhs))
    r_norm_sq = _dot(r, r)
    target = tolerance * max(rhs_norm, 1.0)
    if sqrt(r_norm_sq) <= target:
        return tuple(x), 0, sqrt(r_norm_sq)

    for iteration in range(1, max_iterations + 1):
        ap = _matvec(matrix_rows, p)
        denom = _dot(p, ap)
        if abs(denom) <= 1.0e-30:
            raise RuntimeError("conjugate-gradient breakdown: singular direction")

        alpha = r_norm_sq / denom
        for index in range(size):
            x[index] += alpha * p[index]
            r[index] -= alpha * ap[index]

        new_r_norm_sq = _dot(r, r)
        residual = sqrt(new_r_norm_sq)
        if residual <= target:
            return tuple(x), iteration, residual

        beta = new_r_norm_sq / r_norm_sq
        for index in range(size):
            p[index] = r[index] + beta * p[index]
        r_norm_sq = new_r_norm_sq

    raise RuntimeError("conjugate-gradient did not converge within max_iterations")


def _assemble_poisson_system(
    panel: TrimmedPanel2D,
    *,
    resolution: int,
    spline_degree: int,
    quadrature_order: int,
    backend_mode: BackendMode,
    source: Callable[[float, float], float],
    bounds: tuple[float, float, float, float] | None,
) -> tuple[
    list[dict[int, float]],
    list[float],
    tuple[bool, ...],
    tuple[int, ...],
    tuple[float, float, float, float],
]:
    panel_polygon = awb2d._panel_polygon(panel)
    effective_bounds = awb2d._resolve_panel_bounds(panel, bounds)
    clipped = awb2d._cached_clipped_cells(panel_polygon, resolution, effective_bounds)

    n_basis_axis = resolution + spline_degree
    dof_count = n_basis_axis * n_basis_axis
    matrix_rows: list[dict[int, float]] = [dict() for _ in range(dof_count)]
    rhs = [0.0 for _ in range(dof_count)]
    active_mask = [False for _ in range(dof_count)]

    knots_x = _open_uniform_knots(num_elements=resolution, degree=spline_degree)
    knots_y = _open_uniform_knots(num_elements=resolution, degree=spline_degree)

    for clip in clipped:
        if clip.kind == "outside":
            continue

        ix = clip.cell.ix
        iy = clip.cell.iy
        for local_j in range(spline_degree + 1):
            global_j = iy + local_j
            if global_j < 0 or global_j >= n_basis_axis:
                continue
            row_base = global_j * n_basis_axis
            for local_i in range(spline_degree + 1):
                global_i = ix + local_i
                if global_i < 0 or global_i >= n_basis_axis:
                    continue
                active_mask[row_base + global_i] = True

        samples = _cell_rule_samples(
            clip,
            backend_mode=backend_mode,
            order=quadrature_order,
        )
        for x, y, weight in samples:
            terms = _basis_terms_at_point(
                x=x,
                y=y,
                resolution=resolution,
                spline_degree=spline_degree,
                n_basis_axis=n_basis_axis,
                knots_x=knots_x,
                knots_y=knots_y,
                bounds=effective_bounds,
            )
            source_value = source(x, y)

            for global_a, value_a, grad_ax, grad_ay in terms:
                rhs[global_a] += weight * source_value * value_a
                row = matrix_rows[global_a]
                for global_b, _value_b, grad_bx, grad_by in terms:
                    stiffness = weight * (grad_ax * grad_bx + grad_ay * grad_by)
                    if abs(stiffness) <= 1.0e-20:
                        continue
                    _add_to_sparse_row(row, global_b, stiffness)

    fixed_mask = [not active for active in active_mask]
    for index, is_active in enumerate(active_mask):
        if not is_active:
            continue
        ix = index % n_basis_axis
        iy = index // n_basis_axis
        if ix == 0 or ix == (n_basis_axis - 1) or iy == 0 or iy == (n_basis_axis - 1):
            fixed_mask[index] = True

    free_indices = _apply_zero_dirichlet(matrix_rows, rhs, fixed_mask)
    if not free_indices:
        raise ValueError("assembled system has no free degrees of freedom")

    return matrix_rows, rhs, tuple(active_mask), free_indices, effective_bounds


def _sample_solution_on_grid(
    coefficients: tuple[float, ...],
    *,
    resolution: int,
    spline_degree: int,
    bounds: tuple[float, float, float, float],
) -> tuple[float, ...]:
    xmin, ymin, xmax, ymax = bounds
    n_basis_axis = resolution + spline_degree
    if len(coefficients) != n_basis_axis * n_basis_axis:
        raise ValueError("coefficient size does not match resolution/degree")

    knots_x = _open_uniform_knots(num_elements=resolution, degree=spline_degree)
    knots_y = _open_uniform_knots(num_elements=resolution, degree=spline_degree)

    sampled: list[float] = []
    for iy in range(resolution + 1):
        y = ymin + (ymax - ymin) * iy / resolution
        ty = _normalize(y, vmin=ymin, vmax=ymax)
        span_y = _span_from_param(ty, resolution=resolution, degree=spline_degree)
        by = _basis_funs(span=span_y, t=ty, degree=spline_degree, knots=knots_y)
        start_y = span_y - spline_degree

        for ix in range(resolution + 1):
            x = xmin + (xmax - xmin) * ix / resolution
            tx = _normalize(x, vmin=xmin, vmax=xmax)
            span_x = _span_from_param(tx, resolution=resolution, degree=spline_degree)
            bx = _basis_funs(span=span_x, t=tx, degree=spline_degree, knots=knots_x)
            start_x = span_x - spline_degree

            value = 0.0
            for local_j in range(spline_degree + 1):
                global_j = start_y + local_j
                if global_j < 0 or global_j >= n_basis_axis:
                    continue
                row_base = global_j * n_basis_axis
                for local_i in range(spline_degree + 1):
                    global_i = start_x + local_i
                    if global_i < 0 or global_i >= n_basis_axis:
                        continue
                    value += (
                        coefficients[row_base + global_i] * bx[local_i] * by[local_j]
                    )

            sampled.append(value)

    return tuple(sampled)


def solve_trimmed_poisson_galerkin(
    panel: TrimmedPanel2D,
    *,
    resolution: int,
    spline_degree: int = 2,
    quadrature_order: int,
    backend_mode: BackendMode,
    source: Callable[[float, float], float] = default_poisson_source,
    bounds: tuple[float, float, float, float] | None = None,
    cg_tolerance: float = 1.0e-10,
    cg_max_iterations: int | None = None,
) -> PoissonGalerkinSolveResult:
    """Solve a trimmed-domain immersed tensor-product B-spline Poisson problem."""

    if resolution < 1:
        raise ValueError("resolution must be positive")
    if spline_degree < 1:
        raise ValueError("spline_degree must be positive")
    if backend_mode not in {"jplus", "folded"}:
        raise ValueError(f"unknown backend mode: {backend_mode!r}")
    if quadrature_order < 1:
        raise ValueError("quadrature_order must be positive")

    matrix_rows, rhs, active_mask, free_indices, effective_bounds = (
        _assemble_poisson_system(
            panel,
            resolution=resolution,
            spline_degree=spline_degree,
            quadrature_order=quadrature_order,
            backend_mode=backend_mode,
            source=source,
            bounds=bounds,
        )
    )

    coefficients, iterations, residual = _conjugate_gradient(
        matrix_rows,
        rhs,
        tolerance=cg_tolerance,
        max_iterations=cg_max_iterations,
    )
    sampled_solution = _sample_solution_on_grid(
        coefficients,
        resolution=resolution,
        spline_degree=spline_degree,
        bounds=effective_bounds,
    )

    return PoissonGalerkinSolveResult(
        resolution=resolution,
        spline_degree=spline_degree,
        quadrature_order=quadrature_order,
        backend_mode=backend_mode,
        dof_count=len(coefficients),
        active_dof_count=sum(1 for active in active_mask if active),
        free_dof_count=len(free_indices),
        cg_iterations=iterations,
        residual_norm=residual,
        coefficients=coefficients,
        solution=sampled_solution,
    )


def build_poisson_galerkin_geometry_snapshot(
    panel: TrimmedPanel2D,
    *,
    resolution: int,
    bounds: tuple[float, float, float, float] | None = None,
) -> PoissonGalerkinGeometrySnapshot:
    """Return clipped-cell geometry data for paper-style figure generation."""

    if resolution < 1:
        raise ValueError("resolution must be positive")

    panel_polygon = awb2d._panel_polygon(panel)
    effective_bounds = awb2d._resolve_panel_bounds(panel, bounds)
    clipped = awb2d._cached_clipped_cells(panel_polygon, resolution, effective_bounds)
    inside_cell_count = sum(1 for clip in clipped if clip.kind == "inside")
    trimmed_cell_count = sum(1 for clip in clipped if clip.kind == "trimmed")
    return PoissonGalerkinGeometrySnapshot(
        resolution=resolution,
        bounds=effective_bounds,
        panel_polygon=panel_polygon,
        clipped_cells=clipped,
        inside_cell_count=inside_cell_count,
        trimmed_cell_count=trimmed_cell_count,
    )


def _free_indices_for_compare(
    panel: TrimmedPanel2D,
    *,
    resolution: int,
    bounds: tuple[float, float, float, float] | None,
) -> tuple[int, ...]:
    panel_polygon = awb2d._panel_polygon(panel)
    effective_bounds = awb2d._resolve_panel_bounds(panel, bounds)
    clipped = awb2d._cached_clipped_cells(panel_polygon, resolution, effective_bounds)

    active_mask = [False for _ in range((resolution + 1) * (resolution + 1))]
    for clip in clipped:
        if clip.kind == "outside":
            continue
        nodes = (
            _node_index(clip.cell.ix, clip.cell.iy, resolution=resolution),
            _node_index(clip.cell.ix + 1, clip.cell.iy, resolution=resolution),
            _node_index(clip.cell.ix + 1, clip.cell.iy + 1, resolution=resolution),
            _node_index(clip.cell.ix, clip.cell.iy + 1, resolution=resolution),
        )
        for node in nodes:
            active_mask[node] = True

    free: list[int] = []
    for index, active in enumerate(active_mask):
        if not active:
            continue
        ix = index % (resolution + 1)
        iy = index // (resolution + 1)
        if ix == 0 or ix == resolution or iy == 0 or iy == resolution:
            continue
        free.append(index)
    return tuple(free)


def run_poisson_galerkin_benchmark(
    *,
    profile_name: ProfileName = "quick",
    backend_mode: BackendMode = "jplus",
    panel: TrimmedPanel2D | None = None,
    bounds: tuple[float, float, float, float] | None = None,
) -> PoissonGalerkinBenchmarkResult:
    """Run solver-level immersed Poisson Galerkin/IGA validation."""

    if profile_name not in PROFILES:
        raise ValueError(f"unknown profile: {profile_name!r}")
    if backend_mode not in {"jplus", "folded"}:
        raise ValueError(f"unknown backend mode: {backend_mode!r}")

    profile = PROFILES[profile_name]
    if panel is None:
        panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=256)

    rows: list[PoissonGalerkinResolutionResult] = []
    for resolution in profile.grid_resolutions:
        reference = solve_trimmed_poisson_galerkin(
            panel,
            resolution=resolution,
            spline_degree=profile.spline_degree,
            quadrature_order=profile.reference_quadrature_order,
            backend_mode="jplus",
            bounds=bounds,
        )

        solve = solve_trimmed_poisson_galerkin(
            panel,
            resolution=resolution,
            spline_degree=profile.spline_degree,
            quadrature_order=profile.quadrature_order,
            backend_mode=backend_mode,
            bounds=bounds,
        )

        free_indices = _free_indices_for_compare(
            panel,
            resolution=resolution,
            bounds=bounds,
        )
        if not free_indices:
            raise ValueError("no free interior degrees of freedom for error comparison")

        abs_error = max(
            abs(solve.solution[index] - reference.solution[index])
            for index in free_indices
        )
        reference_scale = max(abs(reference.solution[index]) for index in free_indices)
        if reference_scale <= 1.0e-30:
            reference_scale = 1.0
        rel_error = abs_error / reference_scale
        threshold = max(
            profile.abs_tolerance,
            profile.rel_tolerance * reference_scale,
        )

        rows.append(
            PoissonGalerkinResolutionResult(
                resolution=resolution,
                spline_degree=profile.spline_degree,
                quadrature_order=profile.quadrature_order,
                abs_error=abs_error,
                rel_error=rel_error,
                reference_scale=reference_scale,
                threshold=threshold,
                residual_norm=solve.residual_norm,
                cg_iterations=solve.cg_iterations,
                free_dof_count=solve.free_dof_count,
            )
        )

    return PoissonGalerkinBenchmarkResult(
        profile=profile_name,
        backend_mode=backend_mode,
        spline_degree=profile.spline_degree,
        reference_quadrature_order=profile.reference_quadrature_order,
        rows=tuple(rows),
        passed=all(row.abs_error <= row.threshold for row in rows),
    )
