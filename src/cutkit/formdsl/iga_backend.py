"""IR-to-IGA lowering and assembly using trimmed quadrature."""

from __future__ import annotations

from dataclasses import dataclass
from math import isclose
from typing import Callable

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.geometry import TrimmedPanel2D

from .ir import WeakFormIR


@dataclass(frozen=True)
class IGAAssemblyResult:
    """Assembled linear system and effective integration bounds."""

    matrix_rows: tuple[dict[int, float], ...]
    rhs: tuple[float, ...]
    bounds: tuple[float, float, float, float]


def _term_scalar(form_ir: WeakFormIR, kind: str) -> float:
    value = 0.0
    for term in form_ir.terms:
        if term.kind == kind:
            value += term.coefficient
    return value


def _source_fn(form_ir: WeakFormIR) -> Callable[[float, float], float]:
    for term in form_ir.terms:
        if term.kind != "source":
            continue
        if callable(term.source):
            return term.source
        if term.source is not None:
            constant = float(term.source)

            def _constant_source(_x: float, _y: float) -> float:
                return constant

            return _constant_source
    return lambda _x, _y: 0.0


def _is_boundary_dof(index: int, *, n_basis_axis: int, boundary: str) -> bool:
    ix = index % n_basis_axis
    iy = index // n_basis_axis
    if boundary == "all":
        return (
            ix == 0 or ix == (n_basis_axis - 1) or iy == 0 or iy == (n_basis_axis - 1)
        )
    if boundary == "left":
        return ix == 0
    if boundary == "right":
        return ix == (n_basis_axis - 1)
    if boundary == "bottom":
        return iy == 0
    if boundary == "top":
        return iy == (n_basis_axis - 1)
    raise ValueError(f"unknown boundary selector: {boundary!r}")


def _apply_essential_values(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    fixed_values: dict[int, float],
) -> None:
    for row_index, row in enumerate(matrix_rows):
        if row_index in fixed_values:
            continue
        adjustment = 0.0
        for fixed_index, fixed_value in fixed_values.items():
            if fixed_index not in row:
                continue
            adjustment += row[fixed_index] * fixed_value
            del row[fixed_index]
        rhs[row_index] -= adjustment

    for fixed_index, fixed_value in fixed_values.items():
        matrix_rows[fixed_index] = {fixed_index: 1.0}
        rhs[fixed_index] = fixed_value


def _add_natural_rhs(
    rhs: list[float],
    *,
    form_ir: WeakFormIR,
    resolution: int,
    spline_degree: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
) -> None:
    for condition in form_ir.boundary_conditions:
        if condition.kind != "natural" or isclose(condition.value, 0.0):
            continue

        nodes_1d, weights_1d = pg.gauss_legendre_01(max(2, spline_degree + 1))
        xmin, ymin, xmax, ymax = bounds

        if condition.boundary in {"all", "left", "right"}:
            x = xmin if condition.boundary in {"all", "left"} else xmax
            for t, w in zip(nodes_1d, weights_1d, strict=True):
                y = ymin + t * (ymax - ymin)
                terms = pg._basis_terms_at_point(
                    x=x,
                    y=y,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_basis_axis=n_basis_axis,
                    knots_x=knots_x,
                    knots_y=knots_y,
                    bounds=bounds,
                )
                edge_weight = w * (ymax - ymin)
                for index, value, _gx, _gy in terms:
                    rhs[index] += edge_weight * condition.value * value

        if condition.boundary in {"all", "bottom", "top"}:
            y = ymin if condition.boundary in {"all", "bottom"} else ymax
            for t, w in zip(nodes_1d, weights_1d, strict=True):
                x = xmin + t * (xmax - xmin)
                terms = pg._basis_terms_at_point(
                    x=x,
                    y=y,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_basis_axis=n_basis_axis,
                    knots_x=knots_x,
                    knots_y=knots_y,
                    bounds=bounds,
                )
                edge_weight = w * (xmax - xmin)
                for index, value, _gx, _gy in terms:
                    rhs[index] += edge_weight * condition.value * value


def assemble_iga(
    form_ir: WeakFormIR,
    *,
    panel: TrimmedPanel2D,
    resolution: int,
    spline_degree: int,
    quadrature_order: int,
    backend_mode: pg.BackendMode,
    bounds: tuple[float, float, float, float] | None,
) -> IGAAssemblyResult:
    """Assemble a scalar trimmed-domain system from the shared form IR."""

    if resolution < 1:
        raise ValueError("resolution must be positive")
    if spline_degree < 1:
        raise ValueError("spline_degree must be positive")
    if quadrature_order < 1:
        raise ValueError("quadrature_order must be positive")

    diffusion = _term_scalar(form_ir, "diffusion")
    mass = _term_scalar(form_ir, "mass")
    reaction = _term_scalar(form_ir, "reaction")
    source = _source_fn(form_ir)

    panel_polygon = awb2d._panel_polygon(panel)
    effective_bounds = awb2d._resolve_panel_bounds(panel, bounds)
    clipped = awb2d._cached_clipped_cells(panel_polygon, resolution, effective_bounds)

    n_basis_axis = resolution + spline_degree
    dof_count = n_basis_axis * n_basis_axis
    matrix_rows: list[dict[int, float]] = [dict() for _ in range(dof_count)]
    rhs = [0.0 for _ in range(dof_count)]
    active_mask = [False for _ in range(dof_count)]

    knots_x = pg._open_uniform_knots(num_elements=resolution, degree=spline_degree)
    knots_y = pg._open_uniform_knots(num_elements=resolution, degree=spline_degree)

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

        samples = pg._cell_rule_samples(
            clip,
            backend_mode=backend_mode,
            order=quadrature_order,
        )
        for x, y, weight in samples:
            terms = pg._basis_terms_at_point(
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
                for global_b, value_b, grad_bx, grad_by in terms:
                    stiffness = 0.0
                    if not isclose(diffusion, 0.0):
                        stiffness += diffusion * (grad_ax * grad_bx + grad_ay * grad_by)
                    if not isclose(mass, 0.0):
                        stiffness += mass * value_a * value_b
                    if not isclose(reaction, 0.0):
                        stiffness += reaction * value_a * value_b
                    stiffness *= weight
                    if abs(stiffness) <= 1.0e-20:
                        continue
                    pg._add_to_sparse_row(row, global_b, stiffness)

    _add_natural_rhs(
        rhs,
        form_ir=form_ir,
        resolution=resolution,
        spline_degree=spline_degree,
        n_basis_axis=n_basis_axis,
        knots_x=knots_x,
        knots_y=knots_y,
        bounds=effective_bounds,
    )

    fixed_values: dict[int, float] = {}
    for index, active in enumerate(active_mask):
        if not active:
            fixed_values[index] = 0.0

    for condition in form_ir.boundary_conditions:
        if condition.kind != "essential":
            continue
        for index in range(dof_count):
            if not active_mask[index]:
                continue
            if _is_boundary_dof(
                index, n_basis_axis=n_basis_axis, boundary=condition.boundary
            ):
                fixed_values[index] = condition.value

    _apply_essential_values(matrix_rows, rhs, fixed_values=fixed_values)
    return IGAAssemblyResult(
        matrix_rows=tuple(matrix_rows),
        rhs=tuple(rhs),
        bounds=effective_bounds,
    )
