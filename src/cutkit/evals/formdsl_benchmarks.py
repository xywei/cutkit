"""Convergence and parity benchmark helpers for formdsl backends."""

from __future__ import annotations

from dataclasses import dataclass
from typing import cast

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import assemble_form
from cutkit.formdsl.dgsem_backend import DGSEMLoweringResult
from cutkit.formdsl.iga_backend import IGAAssemblyResult


@dataclass(frozen=True)
class FormDslParityRow:
    resolution: int
    iga_abs_error: float


@dataclass(frozen=True)
class FormDslParityBenchmark:
    rows: tuple[FormDslParityRow, ...]
    dgsem_signature: tuple[str, ...]


def run_formdsl_parity_benchmark(
    *,
    resolutions: tuple[int, ...] = (8, 16),
) -> FormDslParityBenchmark:
    """Run a lightweight parity benchmark for shared scalar forms."""

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
    for resolution in resolutions:
        iga = assemble_form(
            form,
            backend="iga",
            panel=panel,
            resolution=resolution,
            spline_degree=2,
            quadrature_order=4,
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
        overlay_payload={"contract_version": 1},
    )
    dgsem_payload = cast(DGSEMLoweringResult, dgsem.payload)
    signature = dgsem_payload.volume_terms + dgsem_payload.trace_terms
    return FormDslParityBenchmark(rows=tuple(rows), dgsem_signature=signature)
