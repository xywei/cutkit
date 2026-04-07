"""Convergence and parity benchmark helpers for formdsl backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import BoundaryCondition, Term, assemble_form
from cutkit.formdsl.dgsem_backend import DGSEMLoweringResult
from cutkit.formdsl.ir import SourceComponent
from cutkit.formdsl.iga_backend import IGAAssemblyResult
from cutkit.io import MeshmodeCutOverlay


def _benchmark_overlay_payload() -> MeshmodeCutOverlay:
    return MeshmodeCutOverlay(
        contract_version=1,
        target_element_ids=(0,),
        source_element_ids=(0,),
        statuses=("ok",),
        diagnostics=(),
        point_indptr_by_element=(0, 0),
        point_coords=(),
        point_weights=(),
        geometry_metadata_by_element=((),),
    )


@dataclass(frozen=True)
class FormDslParityRow:
    resolution: int
    iga_abs_error: float


@dataclass(frozen=True)
class FormDslParityBenchmark:
    rows: tuple[FormDslParityRow, ...]
    shared_term_signature: tuple[str, ...]
    shared_boundary_signature: tuple[str, ...]
    shared_metadata_signature: tuple[str, ...]
    dgsem_signature: tuple[str, ...]
    dgsem_flux_signature: tuple[str, ...]


@dataclass(frozen=True)
class FormDslMultipatchStressFixture:
    name: str
    form: dict[str, object]
    resolution: int = 2
    spline_degree: int = 1
    quadrature_order: int = 2


@dataclass(frozen=True)
class FormDslMultipatchStressRow:
    name: str
    resolution: int
    execution_path: str
    interface_count: int
    matrix_nnz: int
    matrix_max_abs: float
    rhs_max_abs: float
    repeat_matrix_max_abs_diff: float
    repeat_rhs_max_abs_diff: float


@dataclass(frozen=True)
class FormDslMultipatchStressBenchmark:
    rows: tuple[FormDslMultipatchStressRow, ...]
    orientation_delta_max_abs: float


def _format_float(value: float) -> str:
    return f"{value:.16g}"


def _term_signature(term: Term) -> str:
    coefficient = _format_float(float(term.coefficient))
    if term.kind != "source":
        return f"{term.kind}:{coefficient}"

    if term.source is None:
        source_signature = "implicit:1"
    elif callable(term.source):
        module = getattr(term.source, "__module__", "")
        qualname = getattr(term.source, "__qualname__", type(term.source).__name__)
        source_signature = (
            f"callable:{module}.{qualname}" if module else f"callable:{qualname}"
        )
    elif isinstance(term.source, tuple):
        source_signature = (
            "vector:("
            + ",".join(
                _term_source_component_signature(component) for component in term.source
            )
            + ")"
        )
    else:
        source_signature = f"const:{_format_float(float(term.source))}"
    return f"source:{coefficient}:{source_signature}"


def _term_source_component_signature(component: SourceComponent) -> str:
    if component is None:
        return "implicit:1"
    if callable(component):
        module = getattr(component, "__module__", "")
        qualname = getattr(component, "__qualname__", type(component).__name__)
        return f"callable:{module}.{qualname}" if module else f"callable:{qualname}"
    return f"const:{_format_float(float(component))}"


def _boundary_signature(boundary: BoundaryCondition) -> str:
    signature = (
        f"{boundary.kind}:{boundary.boundary}:{_format_float(float(boundary.value))}"
    )
    return signature


def _metadata_signature(metadata: dict[str, str]) -> tuple[str, ...]:
    return tuple(f"{key}={metadata[key]}" for key in sorted(metadata))


def _ir_signatures(
    terms: tuple[Term, ...],
    boundary_conditions: tuple[BoundaryCondition, ...],
    metadata: dict[str, str],
) -> tuple[tuple[str, ...], tuple[str, ...], tuple[str, ...]]:
    return (
        tuple(sorted(_term_signature(term) for term in terms)),
        tuple(
            sorted(_boundary_signature(boundary) for boundary in boundary_conditions)
        ),
        _metadata_signature(metadata),
    )


def run_formdsl_parity_benchmark(
    *,
    resolutions: tuple[int, ...] = (8, 16),
) -> FormDslParityBenchmark:
    """Run a lightweight parity benchmark for shared scalar forms."""

    if not resolutions:
        raise ValueError("resolutions must be non-empty")

    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=256)
    form: dict[str, object] = {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "source": pg.default_poisson_source},
        ],
        "boundary_conditions": [{"kind": "essential", "value": 0.0}],
        "metadata": {"dg_flux": "sipg"},
    }

    rows: list[FormDslParityRow] = []
    shared_term_signature: tuple[str, ...] | None = None
    shared_boundary_signature: tuple[str, ...] | None = None
    shared_metadata_signature: tuple[str, ...] | None = None
    for resolution in resolutions:
        iga = assemble_form(
            form,
            backend="iga",
            panel=panel,
            resolution=resolution,
            spline_degree=2,
            quadrature_order=4,
        )
        term_signature, boundary_signature, metadata_signature = _ir_signatures(
            iga.ir.terms,
            iga.ir.boundary_conditions,
            iga.ir.metadata,
        )
        if shared_term_signature is None:
            shared_term_signature = term_signature
            shared_boundary_signature = boundary_signature
            shared_metadata_signature = metadata_signature
        elif (
            term_signature != shared_term_signature
            or boundary_signature != shared_boundary_signature
            or metadata_signature != shared_metadata_signature
        ):
            raise RuntimeError(
                "formdsl parity benchmark requires deterministic IGA IR signatures"
            )

        iga_payload = cast(IGAAssemblyResult, iga.payload)
        coefficients, _iters, _residual = pg._conjugate_gradient(
            list(iga_payload.matrix_rows),
            list(iga_payload.rhs),
            tolerance=1.0e-10,
            max_iterations=None,
        )
        sampled = pg._sample_solution_on_grid(
            coefficients,
            resolution=resolution,
            spline_degree=2,
            bounds=iga_payload.bounds,
        )
        reference = pg.solve_trimmed_poisson_galerkin(
            panel,
            resolution=resolution,
            spline_degree=2,
            quadrature_order=6,
            backend_mode="jplus",
        )
        free = pg._free_indices_for_compare(panel, resolution=resolution, bounds=None)
        max_error = max(
            abs(sampled[index] - reference.solution[index]) for index in free
        )
        rows.append(FormDslParityRow(resolution=resolution, iga_abs_error=max_error))

    dgsem = assemble_form(
        form,
        backend="dgsem",
        overlay_payload=_benchmark_overlay_payload(),
    )
    dgsem_term_signature, dgsem_boundary_signature, dgsem_metadata_signature = (
        _ir_signatures(
            dgsem.ir.terms,
            dgsem.ir.boundary_conditions,
            dgsem.ir.metadata,
        )
    )
    if (
        shared_term_signature is None
        or shared_boundary_signature is None
        or shared_metadata_signature is None
    ):
        raise RuntimeError("formdsl parity benchmark did not record IGA signatures")
    if (
        dgsem_term_signature != shared_term_signature
        or dgsem_boundary_signature != shared_boundary_signature
        or dgsem_metadata_signature != shared_metadata_signature
    ):
        raise RuntimeError(
            "formdsl parity benchmark requires matching IR signatures on iga and dgsem"
        )

    dgsem_payload = cast(DGSEMLoweringResult, dgsem.payload)
    signature = dgsem_payload.volume_terms + dgsem_payload.trace_terms
    return FormDslParityBenchmark(
        rows=tuple(rows),
        shared_term_signature=shared_term_signature,
        shared_boundary_signature=shared_boundary_signature,
        shared_metadata_signature=shared_metadata_signature,
        dgsem_signature=signature,
        dgsem_flux_signature=dgsem_payload.flux_terms,
    )


def _sparse_max_abs_entry(matrix_rows: tuple[dict[int, float], ...]) -> float:
    return max(
        (abs(value) for row in matrix_rows for value in row.values()),
        default=0.0,
    )


def _rhs_max_abs(rhs: tuple[float, ...]) -> float:
    return max((abs(value) for value in rhs), default=0.0)


def _sparse_max_abs_diff(
    lhs: tuple[dict[int, float], ...],
    rhs: tuple[dict[int, float], ...],
) -> float:
    if len(lhs) != len(rhs):
        raise ValueError("sparse row counts must match")

    max_diff = 0.0
    for lhs_row, rhs_row in zip(lhs, rhs, strict=True):
        keys = set(lhs_row) | set(rhs_row)
        for key in keys:
            diff = abs(lhs_row.get(key, 0.0) - rhs_row.get(key, 0.0))
            if diff > max_diff:
                max_diff = diff
    return max_diff


def _rhs_max_abs_diff(lhs: tuple[float, ...], rhs: tuple[float, ...]) -> float:
    if len(lhs) != len(rhs):
        raise ValueError("rhs lengths must match")
    return max((abs(a - b) for a, b in zip(lhs, rhs, strict=True)), default=0.0)


def multipatch_stress_fixtures() -> tuple[FormDslMultipatchStressFixture, ...]:
    return (
        FormDslMultipatchStressFixture(
            name="three_patch_mixed_orientations_bspline",
            form={
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "source", "source": pg.default_poisson_source},
                ],
                "boundary_conditions": [],
                "metadata": {
                    "geometry_map": "bspline",
                    "multipatch_penalty": "1.25",
                    "multipatch_boundary:patch-b:marker:b-right": "right",
                    "multipatch_boundary:patch-a:marker:a-top": "top",
                    "multipatch_boundary:patch-c:marker:c-top": "top",
                    "multipatch_boundary:patch-a:marker:a-right": "right",
                },
                "multipatch": {
                    "patch_ids": ["patch-a", "patch-b", "patch-c"],
                    "interfaces": [
                        {
                            "plus_patch": "patch-b",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:b-right",
                            "minus_boundary": "marker:a-top",
                            "orientation": "aligned",
                            "penalty": 0.75,
                        },
                        {
                            "plus_patch": "patch-c",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:c-top",
                            "minus_boundary": "marker:a-right",
                            "orientation": "reversed",
                            "penalty": 1.5,
                        },
                    ],
                },
            },
        ),
        FormDslMultipatchStressFixture(
            name="three_patch_mixed_orientations_nurbs",
            form={
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "source", "source": pg.default_poisson_source},
                ],
                "boundary_conditions": [],
                "metadata": {
                    "geometry_map": "nurbs",
                    "nurbs_weights": "1,2,1,2,3,2,1,2,1",
                    "multipatch_penalty": "1.25",
                    "multipatch_boundary:patch-b:marker:b-right": "right",
                    "multipatch_boundary:patch-a:marker:a-top": "top",
                    "multipatch_boundary:patch-c:marker:c-top": "top",
                    "multipatch_boundary:patch-a:marker:a-right": "right",
                },
                "multipatch": {
                    "patch_ids": ["patch-a", "patch-b", "patch-c"],
                    "interfaces": [
                        {
                            "plus_patch": "patch-b",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:b-right",
                            "minus_boundary": "marker:a-top",
                            "orientation": "aligned",
                            "penalty": 0.75,
                        },
                        {
                            "plus_patch": "patch-c",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:c-top",
                            "minus_boundary": "marker:a-right",
                            "orientation": "reversed",
                            "penalty": 1.5,
                        },
                    ],
                },
            },
        ),
        FormDslMultipatchStressFixture(
            name="orientation_pair_aligned",
            form={
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "source", "source": pg.default_poisson_source},
                ],
                "boundary_conditions": [],
                "metadata": {
                    "geometry_map": "bspline",
                    "multipatch_boundary:patch-b:marker:b-right": "right",
                    "multipatch_boundary:patch-a:marker:a-top": "top",
                },
                "multipatch": {
                    "patch_ids": ["patch-a", "patch-b"],
                    "interfaces": [
                        {
                            "plus_patch": "patch-b",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:b-right",
                            "minus_boundary": "marker:a-top",
                            "orientation": "aligned",
                        }
                    ],
                },
            },
        ),
        FormDslMultipatchStressFixture(
            name="orientation_pair_reversed",
            form={
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "source", "source": pg.default_poisson_source},
                ],
                "boundary_conditions": [],
                "metadata": {
                    "geometry_map": "bspline",
                    "multipatch_boundary:patch-b:marker:b-right": "right",
                    "multipatch_boundary:patch-a:marker:a-top": "top",
                },
                "multipatch": {
                    "patch_ids": ["patch-a", "patch-b"],
                    "interfaces": [
                        {
                            "plus_patch": "patch-b",
                            "minus_patch": "patch-a",
                            "plus_boundary": "marker:b-right",
                            "minus_boundary": "marker:a-top",
                            "orientation": "reversed",
                        }
                    ],
                },
            },
        ),
    )


def run_formdsl_multipatch_stress_benchmark() -> FormDslMultipatchStressBenchmark:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=256)
    rows: list[FormDslMultipatchStressRow] = []
    orientation_payloads: dict[str, IGAAssemblyResult] = {}

    for fixture in multipatch_stress_fixtures():
        first = assemble_form(
            fixture.form,
            backend="iga",
            panel=panel,
            resolution=fixture.resolution,
            spline_degree=fixture.spline_degree,
            quadrature_order=fixture.quadrature_order,
        )
        second = assemble_form(
            fixture.form,
            backend="iga",
            panel=panel,
            resolution=fixture.resolution,
            spline_degree=fixture.spline_degree,
            quadrature_order=fixture.quadrature_order,
        )

        if first.diagnostics or second.diagnostics:
            raise RuntimeError(
                "multipatch stress benchmark expects deterministic iga assembly without diagnostics"
            )

        first_payload = cast(IGAAssemblyResult, first.payload)
        second_payload = cast(IGAAssemblyResult, second.payload)
        rows.append(
            FormDslMultipatchStressRow(
                name=fixture.name,
                resolution=fixture.resolution,
                execution_path=first_payload.execution_path,
                interface_count=len(first_payload.interface_lowering),
                matrix_nnz=sum(len(row) for row in first_payload.matrix_rows),
                matrix_max_abs=_sparse_max_abs_entry(first_payload.matrix_rows),
                rhs_max_abs=_rhs_max_abs(first_payload.rhs),
                repeat_matrix_max_abs_diff=_sparse_max_abs_diff(
                    first_payload.matrix_rows,
                    second_payload.matrix_rows,
                ),
                repeat_rhs_max_abs_diff=_rhs_max_abs_diff(
                    first_payload.rhs,
                    second_payload.rhs,
                ),
            )
        )

        if fixture.name in {"orientation_pair_aligned", "orientation_pair_reversed"}:
            orientation_payloads[fixture.name] = first_payload

    if set(orientation_payloads) != {
        "orientation_pair_aligned",
        "orientation_pair_reversed",
    }:
        raise RuntimeError(
            "multipatch stress benchmark requires aligned/reversed orientation fixtures"
        )
    orientation_delta_max_abs = _sparse_max_abs_diff(
        orientation_payloads["orientation_pair_aligned"].matrix_rows,
        orientation_payloads["orientation_pair_reversed"].matrix_rows,
    )

    return FormDslMultipatchStressBenchmark(
        rows=tuple(rows),
        orientation_delta_max_abs=orientation_delta_max_abs,
    )
