from __future__ import annotations

from math import isfinite

import pytest

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import PrerequisiteError, solve_form
from cutkit.io import MeshmodeCutOverlay


def _overlay_payload(element_count: int) -> MeshmodeCutOverlay:
    return MeshmodeCutOverlay(
        contract_version=1,
        target_element_ids=tuple(range(element_count)),
        source_element_ids=tuple(range(element_count)),
        statuses=tuple("ok" for _ in range(element_count)),
        diagnostics=(),
        point_indptr_by_element=tuple(range(element_count + 1)),
        point_coords=tuple(
            (
                index / (element_count - 1) if element_count > 1 else 0.5,
                0.5,
            )
            for index in range(element_count)
        ),
        point_weights=tuple(1.0 for _ in range(element_count)),
        geometry_metadata_by_element=tuple(() for _ in range(element_count)),
    )


def test_solve_form_iga_runs_end_to_end() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    result = solve_form(
        {
            "terms": [
                {"kind": "diffusion", "coefficient": 1.0},
                {"kind": "source", "source": pg.default_poisson_source},
            ],
            "boundary_conditions": [
                {"kind": "essential", "boundary": "all", "value": 0.0}
            ],
        },
        backend="iga",
        panel=panel,
        resolution=6,
        spline_degree=2,
        quadrature_order=4,
        backend_mode="folded",
    )

    assert result.backend == "iga"
    assert result.execution_mode == "iga_cg"
    assert result.sampled_solution is not None
    assert result.dof_count > 0
    assert result.cg_iterations >= 0
    assert isfinite(result.residual_norm)


def test_solve_form_dgsem_rejects_non_grudge_execution_mode() -> None:
    with pytest.raises(ValueError, match="only supports"):
        solve_form(
            {
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "source", "coefficient": 1.0, "source": 1.0},
                ],
                "boundary_conditions": [
                    {"kind": "essential", "boundary": "all", "value": 0.0}
                ],
            },
            backend="dgsem",
            strict=False,
            overlay_payload=_overlay_payload(6),
            dgsem_execution_mode="toy",  # type: ignore[arg-type]
        )


def test_solve_form_dgsem_flux_family_penalty_influences_operator() -> None:
    overlay = _overlay_payload(10)
    base_form = {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "coefficient": 1.0, "source": 1.0},
        ],
        "boundary_conditions": [
            {"kind": "essential", "boundary": "left", "value": 0.0},
            {"kind": "essential", "boundary": "right", "value": 0.0},
        ],
    }

    try:
        sipg = solve_form(
            {
                **base_form,
                "metadata": {"dg_flux": "sipg", "dg_penalty": "2.0"},
            },
            backend="dgsem",
            strict=False,
            overlay_payload=overlay,
            dgsem_execution_mode="grudge",
        )
        central = solve_form(
            {
                **base_form,
                "metadata": {"dg_flux": "central"},
            },
            backend="dgsem",
            strict=False,
            overlay_payload=overlay,
            dgsem_execution_mode="grudge",
        )
    except PrerequisiteError as exc:
        pytest.skip(f"grudge runtime unavailable: {exc}")

    def _diag_mass(result_matrix: tuple[dict[int, float], ...]) -> float:
        return sum(row.get(index, 0.0) for index, row in enumerate(result_matrix))

    assert _diag_mass(sipg.matrix_rows) > _diag_mass(central.matrix_rows)


def test_solve_form_dgsem_grudge_runs_or_reports_prerequisite() -> None:
    try:
        result = solve_form(
            {
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
                "boundary_conditions": [
                    {"kind": "essential", "boundary": "all", "value": 0.0}
                ],
            },
            backend="dgsem",
            strict=False,
            overlay_payload=_overlay_payload(4),
            dgsem_execution_mode="grudge",
        )
    except PrerequisiteError:
        return

    assert result.execution_mode == "dgsem_grudge"
    assert result.dof_count > 0
    assert isfinite(result.residual_norm)


def test_solve_form_dgsem_convection_uses_nonsymmetric_solver() -> None:
    overlay = _overlay_payload(8)
    try:
        result = solve_form(
            {
                "terms": [
                    {"kind": "diffusion", "coefficient": 1.0},
                    {"kind": "convection", "coefficient": 0.35},
                    {"kind": "source", "coefficient": 1.0, "source": 1.0},
                ],
                "boundary_conditions": [
                    {"kind": "essential", "boundary": "left", "value": 0.0},
                    {"kind": "essential", "boundary": "right", "value": 0.0},
                ],
                "metadata": {"dg_flux": "upwind"},
            },
            backend="dgsem",
            strict=False,
            overlay_payload=overlay,
            dgsem_execution_mode="grudge",
        )
    except PrerequisiteError as exc:
        pytest.skip(f"grudge runtime unavailable: {exc}")

    assert result.execution_mode == "dgsem_grudge"
    assert result.linear_solver in {"bicgstab", "cgne"}
    assert result.dof_count > 0
    assert isfinite(result.residual_norm)
