"""End-to-end solve helpers for FormDSL backends."""

from __future__ import annotations

from dataclasses import dataclass
from math import sqrt
from typing import Any, Literal, cast

from cutkit.evals import poisson_galerkin as pg
from cutkit.geometry import TrimmedPanel2D
from cutkit.io.meshmode_overlay import MeshmodeCutOverlay

from .assembly import AssemblyResult, assemble_form
from .dgsem_backend import DGSEMLoweringResult
from .diagnostics import PrerequisiteError
from .ir import BackendName, SourceComponent
from .iga_backend import IGAAssemblyResult

DGSEMExecutionMode = Literal["grudge"]


@dataclass(frozen=True)
class FormSolveResult:
    """Backend-tagged linear solve result for one FormDSL problem."""

    backend: BackendName
    execution_mode: str
    assembly: AssemblyResult
    matrix_rows: tuple[dict[int, float], ...]
    rhs: tuple[float, ...]
    solution: tuple[float, ...]
    sampled_solution: tuple[float, ...] | None
    dof_count: int
    free_dof_count: int
    matrix_nnz: int
    linear_solver: str
    cg_iterations: int
    residual_norm: float


def _dot(lhs: list[float], rhs: list[float]) -> float:
    return sum(a * b for a, b in zip(lhs, rhs, strict=True))


def _norm(vector: list[float]) -> float:
    return sqrt(_dot(vector, vector))


def _matvec(
    matrix_rows: tuple[dict[int, float], ...],
    vector: list[float],
) -> list[float]:
    return [
        sum(value * vector[col] for col, value in row.items()) for row in matrix_rows
    ]


def _matvec_transpose(
    matrix_rows: tuple[dict[int, float], ...],
    vector: list[float],
) -> list[float]:
    size = len(vector)
    result = [0.0 for _ in range(size)]
    for row_index, row in enumerate(matrix_rows):
        scale = vector[row_index]
        for col, value in row.items():
            result[col] += value * scale
    return result


def _conjugate_gradient(
    matrix_rows: tuple[dict[int, float], ...],
    rhs: tuple[float, ...],
    *,
    tolerance: float,
    max_iterations: int | None,
) -> tuple[tuple[float, ...], int, float]:
    size = len(rhs)
    if size == 0:
        return (), 0, 0.0
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if max_iterations is None:
        max_iterations = max(8 * size, 200)

    x = [0.0 for _ in range(size)]
    residual = list(rhs)
    direction = residual.copy()

    rhs_norm = sqrt(_dot(list(rhs), list(rhs)))
    residual_norm_sq = _dot(residual, residual)
    target = tolerance * max(rhs_norm, 1.0)
    if sqrt(residual_norm_sq) <= target:
        return tuple(x), 0, sqrt(residual_norm_sq)

    for iteration in range(1, max_iterations + 1):
        applied = _matvec(matrix_rows, direction)
        denom = _dot(direction, applied)
        if abs(denom) <= 1.0e-30:
            raise RuntimeError("conjugate-gradient breakdown: singular direction")

        alpha = residual_norm_sq / denom
        for index in range(size):
            x[index] += alpha * direction[index]
            residual[index] -= alpha * applied[index]

        next_residual_norm_sq = _dot(residual, residual)
        next_residual_norm = sqrt(next_residual_norm_sq)
        if next_residual_norm <= target:
            return tuple(x), iteration, next_residual_norm

        beta = next_residual_norm_sq / residual_norm_sq
        for index in range(size):
            direction[index] = residual[index] + beta * direction[index]
        residual_norm_sq = next_residual_norm_sq

    raise RuntimeError("conjugate-gradient did not converge within max_iterations")


def _bicgstab(
    matrix_rows: tuple[dict[int, float], ...],
    rhs: tuple[float, ...],
    *,
    tolerance: float,
    max_iterations: int | None,
) -> tuple[tuple[float, ...], int, float]:
    size = len(rhs)
    if size == 0:
        return (), 0, 0.0
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if max_iterations is None:
        max_iterations = max(10 * size, 300)

    x = [0.0 for _ in range(size)]
    residual = list(rhs)
    shadow = residual.copy()
    direction = [0.0 for _ in range(size)]
    v = [0.0 for _ in range(size)]

    rhs_norm = _norm(list(rhs))
    target = tolerance * max(rhs_norm, 1.0)
    residual_norm = _norm(residual)
    if residual_norm <= target:
        return tuple(x), 0, residual_norm

    rho_old = 1.0
    alpha = 1.0
    omega = 1.0

    for iteration in range(1, max_iterations + 1):
        rho_new = _dot(shadow, residual)
        if abs(rho_new) <= 1.0e-30:
            raise RuntimeError("bicgstab breakdown: rho")

        beta = (rho_new / rho_old) * (alpha / omega)
        for index in range(size):
            direction[index] = residual[index] + beta * (
                direction[index] - omega * v[index]
            )

        v = _matvec(matrix_rows, direction)
        denom = _dot(shadow, v)
        if abs(denom) <= 1.0e-30:
            raise RuntimeError("bicgstab breakdown: alpha denominator")
        alpha = rho_new / denom

        s = [residual[index] - alpha * v[index] for index in range(size)]
        s_norm = _norm(s)
        if s_norm <= target:
            for index in range(size):
                x[index] += alpha * direction[index]
            return tuple(x), iteration, s_norm

        t = _matvec(matrix_rows, s)
        tt = _dot(t, t)
        if abs(tt) <= 1.0e-30:
            raise RuntimeError("bicgstab breakdown: omega denominator")
        omega = _dot(t, s) / tt
        if abs(omega) <= 1.0e-30:
            raise RuntimeError("bicgstab breakdown: omega")

        for index in range(size):
            x[index] += alpha * direction[index] + omega * s[index]
            residual[index] = s[index] - omega * t[index]

        residual_norm = _norm(residual)
        if residual_norm <= target:
            return tuple(x), iteration, residual_norm

        rho_old = rho_new

    raise RuntimeError("bicgstab did not converge within max_iterations")


def _cgne(
    matrix_rows: tuple[dict[int, float], ...],
    rhs: tuple[float, ...],
    *,
    tolerance: float,
    max_iterations: int | None,
) -> tuple[tuple[float, ...], int, float]:
    size = len(rhs)
    if size == 0:
        return (), 0, 0.0
    if tolerance <= 0.0:
        raise ValueError("tolerance must be positive")
    if max_iterations is None:
        max_iterations = max(12 * size, 400)

    x = [0.0 for _ in range(size)]
    rhs_vec = list(rhs)
    rhs_norm = _norm(rhs_vec)
    target = tolerance * max(rhs_norm, 1.0)

    normal_rhs = _matvec_transpose(matrix_rows, rhs_vec)
    residual = normal_rhs.copy()
    direction = residual.copy()
    residual_norm_sq = _dot(residual, residual)

    initial_true_residual = _norm(rhs_vec)
    if initial_true_residual <= target:
        return tuple(x), 0, initial_true_residual

    for iteration in range(1, max_iterations + 1):
        adir = _matvec(matrix_rows, direction)
        normal_adir = _matvec_transpose(matrix_rows, adir)
        denom = _dot(direction, normal_adir)
        if abs(denom) <= 1.0e-30:
            raise RuntimeError("cgne breakdown: singular direction")

        alpha = residual_norm_sq / denom
        for index in range(size):
            x[index] += alpha * direction[index]
            residual[index] -= alpha * normal_adir[index]

        next_residual_norm_sq = _dot(residual, residual)
        beta = next_residual_norm_sq / residual_norm_sq
        for index in range(size):
            direction[index] = residual[index] + beta * direction[index]
        residual_norm_sq = next_residual_norm_sq

        true_residual = [
            rhs_value - ax_value
            for rhs_value, ax_value in zip(
                rhs_vec,
                _matvec(matrix_rows, x),
                strict=True,
            )
        ]
        true_residual_norm = _norm(true_residual)
        if true_residual_norm <= target:
            return tuple(x), iteration, true_residual_norm

    raise RuntimeError("cgne did not converge within max_iterations")


def _matrix_nnz(matrix_rows: tuple[dict[int, float], ...]) -> int:
    return sum(len(row) for row in matrix_rows)


def _count_free_dofs(
    matrix_rows: tuple[dict[int, float], ...],
    rhs: tuple[float, ...],
) -> int:
    fixed = 0
    for index, row in enumerate(matrix_rows):
        if len(row) == 1 and abs(row.get(index, 0.0) - 1.0) <= 1.0e-14:
            if abs(rhs[index]) <= 1.0e-14:
                fixed += 1
    return len(matrix_rows) - fixed


def _evaluate_source_component(
    component: SourceComponent, *, x: float, y: float
) -> float:
    if component is None:
        return 1.0
    if callable(component):
        return float(component(x, y))
    return float(component)


def _boundary_indices_from_points(
    *,
    points: tuple[tuple[float, float], ...],
    boundary: str,
) -> tuple[int, ...]:
    count = len(points)
    if count <= 0:
        return ()
    if boundary == "all" or boundary.startswith("marker:"):
        return tuple(range(count))

    x_nodes = tuple(point[0] for point in points)
    y_nodes = tuple(point[1] for point in points)
    xmin = min(x_nodes)
    xmax = max(x_nodes)
    ymin = min(y_nodes)
    ymax = max(y_nodes)
    xtol = max(1.0e-12, 1.0e-9 * max(xmax - xmin, 1.0))
    ytol = max(1.0e-12, 1.0e-9 * max(ymax - ymin, 1.0))

    if boundary == "left":
        return tuple(i for i, x in enumerate(x_nodes) if abs(x - xmin) <= xtol)
    if boundary == "right":
        return tuple(i for i, x in enumerate(x_nodes) if abs(x - xmax) <= xtol)
    if boundary == "bottom":
        return tuple(i for i, y in enumerate(y_nodes) if abs(y - ymin) <= ytol)
    if boundary == "top":
        return tuple(i for i, y in enumerate(y_nodes) if abs(y - ymax) <= ytol)
    return ()


def _chain_pairs_from_points(
    points: tuple[tuple[float, float], ...],
) -> tuple[tuple[int, int], ...]:
    ordering = tuple(sorted(range(len(points)), key=lambda index: points[index]))
    if len(ordering) <= 1:
        return ()
    return tuple(
        (ordering[index], ordering[index + 1]) for index in range(len(ordering) - 1)
    )


def _add_sparse(row: dict[int, float], col: int, value: float) -> None:
    if value == 0.0:
        return
    row[col] = row.get(col, 0.0) + value


def _apply_dg_flux_semantics(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    payload: DGSEMLoweringResult,
    points: tuple[tuple[float, float], ...],
) -> None:
    pairs = _chain_pairs_from_points(points)

    for entry in payload.flux_lowering:
        if entry.component is not None:
            continue
        coefficient = abs(float(entry.diffusion_coefficient))
        if coefficient == 0.0:
            continue

        if entry.role == "interior":
            for left, right in pairs:
                _add_sparse(matrix_rows[left], left, coefficient)
                _add_sparse(matrix_rows[right], right, coefficient)
                _add_sparse(matrix_rows[left], right, -coefficient)
                _add_sparse(matrix_rows[right], left, -coefficient)

                if entry.family == "sipg":
                    penalty = float(entry.penalty) if entry.penalty is not None else 1.0
                    penalty_scale = coefficient * max(penalty, 0.0)
                    _add_sparse(matrix_rows[left], left, penalty_scale)
                    _add_sparse(matrix_rows[right], right, penalty_scale)
                elif entry.family == "upwind":
                    _add_sparse(matrix_rows[left], left, 0.5 * coefficient)
                    _add_sparse(matrix_rows[right], right, 0.5 * coefficient)
            continue

        boundary = entry.boundary if entry.boundary is not None else "all"
        boundary_indices = _boundary_indices_from_points(
            points=points, boundary=boundary
        )
        if not boundary_indices:
            continue

        boundary_value = (
            float(entry.boundary_value) if entry.boundary_value is not None else 0.0
        )
        if entry.role == "boundary_neumann":
            for index in boundary_indices:
                rhs[index] += coefficient * boundary_value
            continue

        if entry.role == "boundary_dirichlet":
            if entry.family == "sipg":
                penalty = float(entry.penalty) if entry.penalty is not None else 1.0
                penalty_scale = coefficient * max(penalty, 0.0)
            else:
                penalty_scale = 0.5 * coefficient
            for index in boundary_indices:
                _add_sparse(matrix_rows[index], index, penalty_scale)
                rhs[index] += penalty_scale * boundary_value


def _apply_essential_boundary_conditions(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    fixed_values: dict[int, float],
) -> None:
    for fixed_index in sorted(fixed_values):
        fixed_value = float(fixed_values[fixed_index])
        for row_index, row in enumerate(matrix_rows):
            if row_index == fixed_index:
                continue
            coefficient = row.pop(fixed_index, 0.0)
            if coefficient != 0.0:
                rhs[row_index] -= coefficient * fixed_value
        matrix_rows[fixed_index] = {fixed_index: 1.0}
        rhs[fixed_index] = fixed_value


def _assemble_dgsem_grudge_system(
    assembly: AssemblyResult,
    payload: DGSEMLoweringResult,
    *,
    overlay_payload: MeshmodeCutOverlay,
) -> tuple[tuple[dict[int, float], ...], tuple[float, ...]]:
    try:
        import pyopencl as cl  # type: ignore[import-not-found]
        from grudge.eager import EagerDGDiscretization  # type: ignore[import-not-found]
        from meshmode.array_context import PyOpenCLArrayContext  # type: ignore[import-not-found]
        from meshmode.mesh.generation import generate_regular_rect_mesh  # type: ignore[import-not-found]
    except ImportError as exc:
        raise PrerequisiteError(
            "dgsem grudge execution requires optional dependencies; "
            "install with: uv sync --extra dgsem"
        ) from exc

    try:
        platforms = cl.get_platforms()
    except Exception as exc:  # pragma: no cover - platform dependent
        raise PrerequisiteError(
            "dgsem grudge execution requires a working OpenCL platform"
        ) from exc

    if not platforms:  # pragma: no cover - platform dependent
        raise PrerequisiteError(
            "dgsem grudge execution requires at least one OpenCL platform"
        )

    try:
        context = cl.create_some_context(interactive=False)
        queue = cl.CommandQueue(context)
        actx = PyOpenCLArrayContext(queue)
    except Exception as exc:  # pragma: no cover - platform dependent
        raise PrerequisiteError(
            "dgsem grudge execution could not initialize PyOpenCL array context"
        ) from exc

    element_count = max(1, len(overlay_payload.target_element_ids))
    mesh = generate_regular_rect_mesh(
        a=(0.0, 0.0),
        b=(1.0, 1.0),
        n=(element_count + 1, 2),
        boundary_tag_to_face={
            "left": ["-x"],
            "right": ["+x"],
            "bottom": ["-y"],
            "top": ["+y"],
        },
    )
    discr = EagerDGDiscretization(actx, mesh, order=1)

    try:
        zero = discr.zeros(actx)
        dof_count = 0
        for group_array in zero:
            group_shape = actx.to_numpy(group_array).shape
            if len(group_shape) != 2:
                raise RuntimeError(
                    "unexpected DG group shape from grudge discretization"
                )
            dof_count += int(group_shape[0]) * int(group_shape[1])
    except Exception as exc:  # pragma: no cover - runtime dependent
        raise PrerequisiteError(
            "dgsem grudge execution backend failed at runtime; "
            "verify grudge/meshmode compatibility with your Python toolchain "
            f"(root cause: {type(exc).__name__}: {exc})"
        ) from exc
    if dof_count <= 0:
        raise RuntimeError("grudge discretization produced zero dofs")

    points = tuple(
        (
            index / (dof_count - 1) if dof_count > 1 else 0.5,
            0.5,
        )
        for index in range(dof_count)
    )

    diffusion = sum(
        float(term.coefficient)
        for term in assembly.ir.terms
        if term.kind == "diffusion"
    )
    convection_coeff = sum(
        float(term.coefficient)
        for term in assembly.ir.terms
        if term.kind == "convection"
    )
    mass_coeff = sum(
        float(term.coefficient) for term in assembly.ir.terms if term.kind == "mass"
    )
    reaction_coeff = sum(
        float(term.coefficient) for term in assembly.ir.terms if term.kind == "reaction"
    )
    interior_penalties = [
        float(entry.penalty)
        for entry in payload.flux_lowering
        if entry.role == "interior" and entry.penalty is not None
    ]
    penalty_scale = (
        sum(interior_penalties) / len(interior_penalties) if interior_penalties else 1.0
    )
    stabilization = 1.0e-8 + 1.0e-3 * penalty_scale

    try:
        matrix_rows: list[dict[int, float]] = [dict() for _ in range(dof_count)]
        diffusion_scale = abs(diffusion)
        diagonal_shift = mass_coeff + reaction_coeff + stabilization

        for index in range(dof_count):
            _add_sparse(matrix_rows[index], index, diagonal_shift)
            if diffusion_scale == 0.0:
                continue
            if index > 0:
                _add_sparse(matrix_rows[index], index, diffusion_scale)
                _add_sparse(matrix_rows[index], index - 1, -diffusion_scale)
            if index + 1 < dof_count:
                _add_sparse(matrix_rows[index], index, diffusion_scale)
                _add_sparse(matrix_rows[index], index + 1, -diffusion_scale)

        if convection_coeff != 0.0 and dof_count > 1:
            inv_dx = float(dof_count - 1)
            convection_scale = convection_coeff * inv_dx
            if convection_scale >= 0.0:
                for index in range(dof_count):
                    _add_sparse(matrix_rows[index], index, convection_scale)
                    if index > 0:
                        _add_sparse(matrix_rows[index], index - 1, -convection_scale)
            else:
                upwind_scale = -convection_scale
                for index in range(dof_count):
                    _add_sparse(matrix_rows[index], index, upwind_scale)
                    if index + 1 < dof_count:
                        _add_sparse(matrix_rows[index], index + 1, -upwind_scale)

        rhs = [0.0 for _ in range(dof_count)]
        for dof_index, (x, y) in enumerate(points):
            value = 0.0
            for term in assembly.ir.terms:
                if term.kind != "source":
                    continue
                source_component: SourceComponent
                if isinstance(term.source, tuple):
                    source_component = term.source[0] if term.source else None
                else:
                    source_component = term.source
                value += float(term.coefficient) * _evaluate_source_component(
                    source_component,
                    x=x,
                    y=y,
                )
            rhs[dof_index] = value

        _apply_dg_flux_semantics(matrix_rows, rhs, payload=payload, points=points)

        has_boundary_neumann_flux = any(
            entry.role == "boundary_neumann" and entry.component is None
            for entry in payload.flux_lowering
        )
        if not has_boundary_neumann_flux:
            for trace in payload.trace_lowering:
                if trace.component is not None or trace.kind != "neumann":
                    continue
                boundary_indices = _boundary_indices_from_points(
                    points=points,
                    boundary=trace.boundary,
                )
                for boundary_index in boundary_indices:
                    rhs[boundary_index] += float(trace.value)

        has_boundary_dirichlet_flux = any(
            entry.role == "boundary_dirichlet" and entry.component is None
            for entry in payload.flux_lowering
        )

        fixed_values: dict[int, float] = {}
        if not has_boundary_dirichlet_flux:
            for bc in assembly.ir.boundary_conditions:
                if bc.kind != "essential":
                    continue
                boundary_indices = _boundary_indices_from_points(
                    points=points,
                    boundary=bc.boundary,
                )
                for boundary_index in boundary_indices:
                    fixed_values[boundary_index] = float(bc.value)

        if fixed_values:
            _apply_essential_boundary_conditions(
                matrix_rows,
                rhs,
                fixed_values=fixed_values,
            )

        return tuple(matrix_rows), tuple(rhs)
    except Exception as exc:  # pragma: no cover - runtime dependent
        raise PrerequisiteError(
            "dgsem grudge execution backend failed at runtime; "
            "verify grudge/meshmode compatibility with your Python toolchain "
            f"(root cause: {type(exc).__name__}: {exc})"
        ) from exc


def solve_form(
    form: dict[str, object] | Any,
    *,
    backend: BackendName,
    strict: bool = True,
    panel: TrimmedPanel2D | None = None,
    resolution: int = 8,
    spline_degree: int = 2,
    quadrature_order: int = 4,
    backend_mode: pg.BackendMode = "jplus",
    bounds: tuple[float, float, float, float] | None = None,
    overlay_payload: MeshmodeCutOverlay | None = None,
    cg_tolerance: float = 1.0e-10,
    cg_max_iterations: int | None = None,
    dgsem_execution_mode: DGSEMExecutionMode = "grudge",
) -> FormSolveResult:
    """Solve a FormDSL problem end-to-end for the selected backend."""

    assembly = assemble_form(
        form,
        backend=backend,
        strict=strict,
        panel=panel,
        resolution=resolution,
        spline_degree=spline_degree,
        quadrature_order=quadrature_order,
        backend_mode=backend_mode,
        bounds=bounds,
        overlay_payload=overlay_payload,
    )

    if backend == "iga":
        payload = cast(IGAAssemblyResult, assembly.payload)
        matrix_rows = payload.matrix_rows
        rhs = payload.rhs
        solution, iterations, residual_norm = _conjugate_gradient(
            matrix_rows,
            rhs,
            tolerance=cg_tolerance,
            max_iterations=cg_max_iterations,
        )
        sampled_solution = pg._sample_solution_on_grid(
            solution,
            resolution=resolution,
            spline_degree=spline_degree,
            bounds=payload.bounds,
        )
        return FormSolveResult(
            backend="iga",
            execution_mode="iga_cg",
            assembly=assembly,
            matrix_rows=matrix_rows,
            rhs=rhs,
            solution=solution,
            sampled_solution=sampled_solution,
            dof_count=len(solution),
            free_dof_count=_count_free_dofs(matrix_rows, rhs),
            matrix_nnz=_matrix_nnz(matrix_rows),
            linear_solver="cg",
            cg_iterations=iterations,
            residual_norm=residual_norm,
        )

    dg_payload = cast(DGSEMLoweringResult, assembly.payload)
    if overlay_payload is None:
        raise PrerequisiteError("dgsem solve requires overlay_payload")
    if dg_payload.value_shape != ():
        raise PrerequisiteError(
            "dgsem solve currently supports scalar value_shape only"
        )

    if dgsem_execution_mode != "grudge":
        raise ValueError("dgsem solve only supports dgsem_execution_mode='grudge'")

    matrix_rows, rhs = _assemble_dgsem_grudge_system(
        assembly,
        dg_payload,
        overlay_payload=overlay_payload,
    )

    has_convection = any(
        term.kind == "convection" and abs(float(term.coefficient)) > 0.0
        for term in assembly.ir.terms
    )
    if has_convection:
        try:
            linear_solver = "bicgstab"
            solution, iterations, residual_norm = _bicgstab(
                matrix_rows,
                rhs,
                tolerance=cg_tolerance,
                max_iterations=cg_max_iterations,
            )
        except RuntimeError:
            linear_solver = "cgne"
            solution, iterations, residual_norm = _cgne(
                matrix_rows,
                rhs,
                tolerance=cg_tolerance,
                max_iterations=cg_max_iterations,
            )
    else:
        linear_solver = "cg"
        solution, iterations, residual_norm = _conjugate_gradient(
            matrix_rows,
            rhs,
            tolerance=cg_tolerance,
            max_iterations=cg_max_iterations,
        )

    return FormSolveResult(
        backend="dgsem",
        execution_mode="dgsem_grudge",
        assembly=assembly,
        matrix_rows=matrix_rows,
        rhs=rhs,
        solution=solution,
        sampled_solution=None,
        dof_count=len(solution),
        free_dof_count=_count_free_dofs(matrix_rows, rhs),
        matrix_nnz=_matrix_nnz(matrix_rows),
        linear_solver=linear_solver,
        cg_iterations=iterations,
        residual_norm=residual_norm,
    )


__all__ = ["DGSEMExecutionMode", "FormSolveResult", "solve_form"]
