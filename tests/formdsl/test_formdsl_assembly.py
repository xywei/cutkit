from __future__ import annotations

from math import isclose
from typing import cast

import pytest

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import CapabilityError, PrerequisiteError, assemble_form, parse_form
from cutkit.formdsl.dgsem_backend import DGSEMLoweringResult
from cutkit.formdsl.iga_backend import IGAAssemblyResult


def _base_form() -> dict[str, object]:
    return {
        "trial_space": "P2",
        "test_space": "P2",
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "source": pg.default_poisson_source},
        ],
        "boundary_conditions": [{"kind": "essential", "value": 0.0}],
    }


def _assert_sparse_close(
    lhs: tuple[dict[int, float], ...],
    rhs: list[dict[int, float]],
    *,
    tolerance: float = 1.0e-12,
) -> None:
    assert len(lhs) == len(rhs)
    for row_l, row_r in zip(lhs, rhs, strict=True):
        assert set(row_l) == set(row_r)
        for key in row_l:
            assert isclose(row_l[key], row_r[key], abs_tol=tolerance, rel_tol=0.0)


def test_parse_form_mapping_roundtrips() -> None:
    ir = parse_form(_base_form(), backend="iga")
    assert ir.trial_space == "P2"
    assert tuple(term.kind for term in ir.terms) == ("diffusion", "source")
    assert tuple(condition.kind for condition in ir.boundary_conditions) == (
        "essential",
    )


def test_capability_check_strict_vs_permissive() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    unsupported: dict[str, object] = {
        "terms": [{"kind": "convection", "coefficient": 1.0}],
    }

    with pytest.raises(CapabilityError):
        assemble_form(unsupported, backend="iga", panel=panel)

    permissive = assemble_form(unsupported, backend="iga", panel=panel, strict=False)
    assert permissive.diagnostics
    assert permissive.diagnostics[0].code == "unsupported_term"


def test_iga_diffusion_assembly_matches_existing_poisson_path() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    assembled = assemble_form(
        _base_form(),
        backend="iga",
        panel=panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
    )
    iga_payload = cast(IGAAssemblyResult, assembled.payload)

    matrix_rows, rhs, _active_mask, _free, bounds = pg._assemble_poisson_system(
        panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
        backend_mode="jplus",
        source=pg.default_poisson_source,
        bounds=None,
    )
    assert iga_payload.bounds == bounds
    _assert_sparse_close(iga_payload.matrix_rows, matrix_rows)
    for left, right in zip(iga_payload.rhs, rhs, strict=True):
        assert isclose(left, right, abs_tol=1.0e-12, rel_tol=0.0)


def test_manufactured_solution_iga_path_is_consistent() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=256)
    assembled = assemble_form(
        _base_form(),
        backend="iga",
        panel=panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
    )
    iga_payload = cast(IGAAssemblyResult, assembled.payload)
    coefficients, _iters, _residual = pg._conjugate_gradient(
        list(iga_payload.matrix_rows),
        list(iga_payload.rhs),
        tolerance=1.0e-10,
        max_iterations=None,
    )
    sampled = pg._sample_solution_on_grid(
        coefficients,
        resolution=8,
        spline_degree=2,
        bounds=iga_payload.bounds,
    )

    reference = pg.solve_trimmed_poisson_galerkin(
        panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=6,
        backend_mode="jplus",
    )
    free = pg._free_indices_for_compare(panel, resolution=8, bounds=None)
    max_error = max(abs(sampled[index] - reference.solution[index]) for index in free)
    assert max_error <= 2.0e-4


def test_dgsem_lowering_requires_overlay_payload() -> None:
    with pytest.raises(PrerequisiteError):
        assemble_form(_base_form(), backend="dgsem")


def test_backend_parity_payload_uses_shared_ir_terms() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form: dict[str, object] = {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "mass", "coefficient": 0.1},
            {"kind": "reaction", "coefficient": 0.2},
            {"kind": "source", "source": 1.0},
        ],
        "boundary_conditions": [
            {"kind": "essential", "value": 0.0, "boundary": "all"},
            {"kind": "natural", "value": 1.0, "boundary": "top"},
        ],
        "metadata": {"dg_flux": "sipg"},
    }

    iga = assemble_form(form, backend="iga", panel=panel, strict=True)
    dgsem = assemble_form(
        form,
        backend="dgsem",
        overlay_payload={"contract_version": 1},
        strict=True,
    )
    dgsem_payload = cast(DGSEMLoweringResult, dgsem.payload)

    assert not iga.diagnostics
    assert not dgsem.diagnostics
    assert dgsem_payload.volume_terms == ("diffusion", "mass", "reaction", "source")
    assert dgsem_payload.trace_terms == ("dirichlet:all", "neumann:top")


def test_source_term_coefficients_contribute_to_rhs() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    weighted_form: dict[str, object] = {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {
                "kind": "source",
                "coefficient": 2.5,
                "source": pg.default_poisson_source,
            },
            {"kind": "source", "coefficient": -0.75, "source": 1.0},
        ],
        "boundary_conditions": [{"kind": "essential", "value": 0.0}],
    }
    equivalent_form: dict[str, object] = {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {
                "kind": "source",
                "source": lambda x, y: 2.5 * pg.default_poisson_source(x, y) - 0.75,
            },
        ],
        "boundary_conditions": [{"kind": "essential", "value": 0.0}],
    }

    weighted = assemble_form(weighted_form, backend="iga", panel=panel, strict=True)
    equivalent = assemble_form(equivalent_form, backend="iga", panel=panel, strict=True)
    weighted_payload = cast(IGAAssemblyResult, weighted.payload)
    equivalent_payload = cast(IGAAssemblyResult, equivalent.payload)

    for left, right in zip(weighted_payload.rhs, equivalent_payload.rhs, strict=True):
        assert isclose(left, right, abs_tol=1.0e-12, rel_tol=0.0)


def test_natural_boundary_all_matches_sum_of_each_edge() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)

    def _assemble_natural(boundary: str) -> tuple[float, ...]:
        form: dict[str, object] = {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [
                {"kind": "natural", "value": 1.0, "boundary": boundary}
            ],
        }
        result = assemble_form(form, backend="iga", panel=panel, strict=True)
        payload = cast(IGAAssemblyResult, result.payload)
        return payload.rhs

    rhs_all = _assemble_natural("all")
    rhs_left = _assemble_natural("left")
    rhs_right = _assemble_natural("right")
    rhs_bottom = _assemble_natural("bottom")
    rhs_top = _assemble_natural("top")

    for idx, value in enumerate(rhs_all):
        expected = rhs_left[idx] + rhs_right[idx] + rhs_bottom[idx] + rhs_top[idx]
        assert isclose(value, expected, abs_tol=1.0e-12, rel_tol=0.0)
