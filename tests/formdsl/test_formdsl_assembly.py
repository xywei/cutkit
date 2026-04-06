from __future__ import annotations

from math import isclose, isfinite
from typing import Any, cast

import pytest

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.io import MeshmodeCutOverlay, MeshmodeOverlayDiagnostic, OverlayStatus
from cutkit.formdsl import (
    BoundaryCondition,
    CapabilityError,
    PrerequisiteError,
    Term,
    WeakFormIR,
    assemble_form,
    iga_backend as iga_backend_module,
    parse_form,
)
from cutkit.formdsl.dgsem_backend import (
    DGSEMLoweringResult,
    DGSEMTraceLowering,
    DGSEMVolumeLowering,
)
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


def _overlay_contract(
    *,
    contract_version: int = 1,
    statuses: tuple[OverlayStatus, ...] = ("ok",),
    diagnostics: tuple[MeshmodeOverlayDiagnostic, ...] = (),
) -> MeshmodeCutOverlay:
    target_element_ids = tuple(range(len(statuses)))
    source_element_ids = tuple(
        index if status == "ok" else None for index, status in enumerate(statuses)
    )
    return MeshmodeCutOverlay(
        contract_version=contract_version,
        target_element_ids=target_element_ids,
        source_element_ids=source_element_ids,
        statuses=statuses,
        diagnostics=diagnostics,
        point_indptr_by_element=tuple(0 for _ in range(len(statuses) + 1)),
        point_coords=(),
        point_weights=(),
        geometry_metadata_by_element=tuple(() for _ in statuses),
    )


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


def test_parse_form_accepts_ufl_like_scalar_form() -> None:
    class Argument:
        def __init__(self, number: int, element: str) -> None:
            self._number = number
            self._element = element
            self.ufl_operands: tuple[object, ...] = ()

        def number(self) -> int:
            return self._number

        def ufl_element(self) -> str:
            return self._element

    class FloatValue:
        def __init__(self, value: float) -> None:
            self._value = value
            self.ufl_operands: tuple[object, ...] = ()

        def __float__(self) -> float:
            return self._value

    class Grad:
        def __init__(self, operand: object) -> None:
            self.ufl_operands = (operand,)

    class Inner:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Product:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Division:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Sum:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Integral:
        def __init__(
            self,
            integral_type: str,
            integrand: object,
            *,
            subdomain_id: object | None = None,
        ) -> None:
            self._integral_type = integral_type
            self._integrand = integrand
            self._subdomain_id = subdomain_id

        def integral_type(self) -> str:
            return self._integral_type

        def integrand(self) -> object:
            return self._integrand

        def subdomain_id(self) -> object | None:
            return self._subdomain_id

    class UflLikeForm:
        def __init__(
            self,
            integrals: tuple[Integral, ...],
            arguments: tuple[Argument, ...],
            *,
            boundary_marker_map: dict[int, str] | None = None,
        ):
            self._integrals = integrals
            self._arguments = arguments
            self.boundary_marker_map = (
                dict(boundary_marker_map) if boundary_marker_map is not None else {}
            )

        def integrals(self) -> tuple[Integral, ...]:
            return self._integrals

        def arguments(self) -> tuple[Argument, ...]:
            return self._arguments

    UflLikeForm.__module__ = "ufl.mock"

    test_arg = Argument(0, "P2")
    trial_arg = Argument(1, "P2")
    diffusion = Product(FloatValue(2.0), Inner(Grad(trial_arg), Grad(test_arg)))
    source = Product(FloatValue(-3.0), test_arg)
    natural = Product(FloatValue(4.0), test_arg)
    form = UflLikeForm(
        integrals=(
            Integral("cell", Sum(diffusion, source)),
            Integral("exterior_facet", natural),
        ),
        arguments=(test_arg, trial_arg),
    )

    ir = parse_form(form, backend="iga")

    assert ir.trial_space == "P2"
    assert ir.test_space == "P2"
    assert ir.terms == (
        Term(kind="diffusion", coefficient=2.0, source=None),
        Term(kind="source", coefficient=-3.0, source=1.0),
    )
    assert ir.boundary_conditions == (
        BoundaryCondition(kind="natural", value=4.0, boundary="all"),
    )

    localized = UflLikeForm(
        integrals=(
            Integral("cell", diffusion),
            Integral("exterior_facet", natural, subdomain_id=3),
        ),
        arguments=(test_arg, trial_arg),
        boundary_marker_map={3: "top"},
    )
    localized_ir = parse_form(localized, backend="iga")
    assert localized_ir.boundary_conditions == (
        BoundaryCondition(kind="natural", value=4.0, boundary="marker:3"),
    )
    assert localized_ir.metadata["boundary_marker:3"] == "top"

    nonlinear = UflLikeForm(
        integrals=(
            Integral(
                "cell",
                Product(Product(trial_arg, trial_arg), test_arg),
            ),
        ),
        arguments=(test_arg, trial_arg),
    )
    with pytest.raises(ValueError, match="unsupported UFL cell integrand"):
        parse_form(nonlinear, backend="iga")

    rational = UflLikeForm(
        integrals=(
            Integral(
                "cell",
                Division(test_arg, trial_arg),
            ),
        ),
        arguments=(test_arg, trial_arg),
    )
    with pytest.raises(ValueError, match="unsupported UFL"):
        parse_form(rational, backend="iga")

    nonlinear_facet = UflLikeForm(
        integrals=(
            Integral(
                "exterior_facet",
                Product(test_arg, test_arg),
            ),
        ),
        arguments=(test_arg, trial_arg),
    )
    with pytest.raises(ValueError, match="unsupported UFL exterior facet"):
        parse_form(nonlinear_facet, backend="iga")


def test_parse_form_requires_value_shape_for_vector_space_labels() -> None:
    with pytest.raises(ValueError, match="must declare value_shape"):
        parse_form(
            {
                "trial_space": "Vector(P2)",
                "test_space": "Vector(P2)",
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            },
            backend="iga",
        )


def test_parse_form_accepts_vector_mapping_payload_with_value_shape() -> None:
    ir = parse_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [2],
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
        },
        backend="dgsem",
    )

    assert ir.value_shape == (2,)


def test_parse_form_rejects_invalid_value_shape_entries() -> None:
    with pytest.raises(ValueError, match="value_shape entry"):
        parse_form(
            {
                "trial_space": "Vector(P2)",
                "test_space": "Vector(P2)",
                "value_shape": [0],
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            },
            backend="dgsem",
        )

    with pytest.raises(ValueError, match="value_shape entry"):
        parse_form(
            {
                "trial_space": "Vector(P2)",
                "test_space": "Vector(P2)",
                "value_shape": [2.5],
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            },
            backend="dgsem",
        )


def test_parse_form_accepts_vector_source_sequence() -> None:
    ir = parse_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [2],
            "terms": [
                {
                    "kind": "source",
                    "coefficient": 1.0,
                    "source": [1.0, 2.0],
                }
            ],
        },
        backend="dgsem",
    )

    assert ir.terms[0].source == (1.0, 2.0)


def test_parse_form_rejects_vector_source_sequence_length_mismatch() -> None:
    with pytest.raises(ValueError, match="vector source length"):
        parse_form(
            {
                "trial_space": "Vector(P2)",
                "test_space": "Vector(P2)",
                "value_shape": [2],
                "terms": [
                    {
                        "kind": "source",
                        "coefficient": 1.0,
                        "source": [1.0, 2.0, 3.0],
                    }
                ],
            },
            backend="dgsem",
        )


def test_parse_form_rejects_vector_source_sequence_for_scalar_shape() -> None:
    with pytest.raises(ValueError, match="vector source for scalar value_shape"):
        parse_form(
            {
                "terms": [
                    {
                        "kind": "source",
                        "coefficient": 1.0,
                        "source": [1.0, 2.0],
                    }
                ],
            },
            backend="iga",
        )


def test_parse_form_accepts_scalar_tensor_product_space_labels() -> None:
    ir = parse_form(
        {
            "trial_space": "TensorProductElement(Q2,Q2)",
            "test_space": "TensorProductElement(Q2,Q2)",
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
        },
        backend="iga",
    )

    assert ir.trial_space == "TensorProductElement(Q2,Q2)"
    assert ir.test_space == "TensorProductElement(Q2,Q2)"


def test_parse_form_rejects_vector_labels_in_weakform_ir_without_shape() -> None:
    form_ir = WeakFormIR(
        trial_space="Vector(P1)",
        test_space="Vector(P1)",
        terms=(Term(kind="diffusion", coefficient=1.0),),
    )

    with pytest.raises(ValueError, match="must declare value_shape"):
        parse_form(form_ir, backend="dgsem")


def test_parse_form_accepts_vector_space_labels_in_weakform_ir() -> None:
    form_ir = WeakFormIR(
        trial_space="Tensor(P1)",
        test_space="P1",
        terms=(Term(kind="diffusion", coefficient=1.0),),
        value_shape=(3,),
    )

    parsed = parse_form(form_ir, backend="dgsem")
    assert parsed.value_shape == (3,)


def test_parse_form_accepts_vector_valued_ufl_arguments() -> None:
    class Argument:
        def __init__(
            self,
            number: int,
            element: str,
            shape: tuple[int, ...],
        ) -> None:
            self._number = number
            self._element = element
            self._shape = shape
            self.ufl_operands: tuple[object, ...] = ()

        def number(self) -> int:
            return self._number

        def ufl_element(self) -> str:
            return self._element

        def ufl_shape(self) -> tuple[int, ...]:
            return self._shape

    class FloatValue:
        def __init__(self, value: float) -> None:
            self._value = value
            self.ufl_operands: tuple[object, ...] = ()

        def __float__(self) -> float:
            return self._value

    class Grad:
        def __init__(self, operand: object) -> None:
            self.ufl_operands = (operand,)

    class Inner:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Product:
        def __init__(self, left: object, right: object) -> None:
            self.ufl_operands = (left, right)

    class Integral:
        def __init__(self, integral_type: str, integrand: object) -> None:
            self._integral_type = integral_type
            self._integrand = integrand

        def integral_type(self) -> str:
            return self._integral_type

        def integrand(self) -> object:
            return self._integrand

        def subdomain_id(self) -> object | None:
            return None

    class UflLikeForm:
        def __init__(
            self,
            integrals: tuple[Integral, ...],
            arguments: tuple[Argument, ...],
        ) -> None:
            self._integrals = integrals
            self._arguments = arguments

        def integrals(self) -> tuple[Integral, ...]:
            return self._integrals

        def arguments(self) -> tuple[Argument, ...]:
            return self._arguments

    UflLikeForm.__module__ = "ufl.mock"

    test_arg = Argument(0, "P2", (2,))
    trial_arg = Argument(1, "P2", (2,))
    diffusion = Product(
        FloatValue(1.0),
        Inner(Grad(trial_arg), Grad(test_arg)),
    )
    form = UflLikeForm(
        integrals=(Integral("cell", diffusion),),
        arguments=(test_arg, trial_arg),
    )

    ir = parse_form(form, backend="dgsem")
    assert ir.value_shape == (2,)


def test_parse_form_weakformir_rejects_invalid_boundary_selector() -> None:
    form_ir = WeakFormIR(
        trial_space="P1",
        test_space="P1",
        terms=(Term(kind="diffusion", coefficient=1.0),),
        boundary_conditions=(
            BoundaryCondition(kind="natural", value=1.0, boundary="diagonal"),
        ),
    )

    with pytest.raises(ValueError, match="unsupported boundary"):
        parse_form(form_ir, backend="iga")


def test_parse_form_weakformir_rejects_empty_terms() -> None:
    form_ir = WeakFormIR(
        trial_space="P1",
        test_space="P1",
        terms=(),
    )

    with pytest.raises(ValueError, match="non-empty 'terms' list"):
        parse_form(form_ir, backend="iga")


def test_parse_form_weakformir_rejects_invalid_marker_metadata() -> None:
    form_ir = WeakFormIR(
        trial_space="P1",
        test_space="P1",
        terms=(Term(kind="diffusion", coefficient=1.0),),
        boundary_conditions=(
            BoundaryCondition(kind="natural", value=1.0, boundary="marker:3"),
        ),
        metadata={"boundary_marker:3": "diagonal"},
    )

    with pytest.raises(ValueError, match="unsupported selector"):
        parse_form(form_ir, backend="iga")


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


def test_iga_accepts_nurbs_geometry_map_metadata() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form = _base_form()
    form["metadata"] = {"geometry_map": "nurbs"}

    result = assemble_form(
        form,
        backend="iga",
        panel=panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
    )
    payload = cast(IGAAssemblyResult, result.payload)

    assert not result.diagnostics
    assert payload.geometry_map == "nurbs"
    assert payload.execution_path == "nurbs_rational_single_patch"


def test_iga_bspline_execution_path_default_is_stable() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    result = assemble_form(
        _base_form(),
        backend="iga",
        panel=panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
    )
    payload = cast(IGAAssemblyResult, result.payload)

    assert payload.geometry_map == "bspline"
    assert payload.execution_path == "bspline"


def test_iga_bspline_ignores_nurbs_weight_metadata() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form = _base_form()
    form["metadata"] = {
        "geometry_map": "bspline",
        "nurbs_weights": "nan",
    }

    result = assemble_form(
        form,
        backend="iga",
        panel=panel,
        resolution=8,
        spline_degree=2,
        quadrature_order=4,
    )
    payload = cast(IGAAssemblyResult, result.payload)

    assert not result.diagnostics
    assert payload.execution_path == "bspline"


def test_iga_nurbs_weights_length_mismatch_rejected() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form = _base_form()
    form["metadata"] = {
        "geometry_map": "nurbs",
        "nurbs_weights": "1, 1, 1",
    }

    with pytest.raises(ValueError, match="does not match dof count"):
        assemble_form(
            form,
            backend="iga",
            panel=panel,
            resolution=2,
            spline_degree=1,
            quadrature_order=2,
        )


@pytest.mark.parametrize("bad_weight", ["nan", "inf", "-inf"])
def test_iga_nurbs_weights_nonfinite_rejected(bad_weight: str) -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form = _base_form()
    form["metadata"] = {
        "geometry_map": "nurbs",
        "nurbs_weights": f"1,1,1,1,{bad_weight},1,1,1,1",
    }

    with pytest.raises(ValueError, match="must be finite"):
        assemble_form(
            form,
            backend="iga",
            panel=panel,
            resolution=2,
            spline_degree=1,
            quadrature_order=2,
        )


def test_iga_nurbs_uniform_tiny_weights_are_scale_invariant() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    bspline = _base_form()
    tiny_nurbs = _base_form()
    tiny_nurbs["metadata"] = {
        "geometry_map": "nurbs",
        "nurbs_weights": "1e-40,1e-40,1e-40,1e-40,1e-40,1e-40,1e-40,1e-40,1e-40",
    }

    bspline_result = assemble_form(
        bspline,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )
    tiny_nurbs_result = assemble_form(
        tiny_nurbs,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )

    bspline_payload = cast(IGAAssemblyResult, bspline_result.payload)
    tiny_nurbs_payload = cast(IGAAssemblyResult, tiny_nurbs_result.payload)

    assert tiny_nurbs_payload.execution_path == "nurbs_rational_single_patch"
    assert all(
        isfinite(value)
        for row in tiny_nurbs_payload.matrix_rows
        for value in row.values()
    )
    assert all(isfinite(value) for value in tiny_nurbs_payload.rhs)
    _assert_sparse_close(
        tiny_nurbs_payload.matrix_rows,
        [dict(row) for row in bspline_payload.matrix_rows],
        tolerance=1.0e-12,
    )
    for bspline_value, tiny_nurbs_value in zip(
        bspline_payload.rhs,
        tiny_nurbs_payload.rhs,
        strict=True,
    ):
        assert isclose(bspline_value, tiny_nurbs_value, rel_tol=0.0, abs_tol=1.0e-12)


def test_iga_nurbs_uniform_huge_weights_are_scale_invariant() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    bspline = _base_form()
    huge_nurbs = _base_form()
    huge_nurbs["metadata"] = {
        "geometry_map": "nurbs",
        "nurbs_weights": "1e308,1e308,1e308,1e308,1e308,1e308,1e308,1e308,1e308",
    }

    bspline_result = assemble_form(
        bspline,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )
    huge_nurbs_result = assemble_form(
        huge_nurbs,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )

    bspline_payload = cast(IGAAssemblyResult, bspline_result.payload)
    huge_nurbs_payload = cast(IGAAssemblyResult, huge_nurbs_result.payload)

    assert huge_nurbs_payload.execution_path == "nurbs_rational_single_patch"
    assert all(
        isfinite(value)
        for row in huge_nurbs_payload.matrix_rows
        for value in row.values()
    )
    assert all(isfinite(value) for value in huge_nurbs_payload.rhs)
    _assert_sparse_close(
        huge_nurbs_payload.matrix_rows,
        [dict(row) for row in bspline_payload.matrix_rows],
        tolerance=1.0e-12,
    )
    for bspline_value, huge_nurbs_value in zip(
        bspline_payload.rhs,
        huge_nurbs_payload.rhs,
        strict=True,
    ):
        assert isclose(bspline_value, huge_nurbs_value, rel_tol=0.0, abs_tol=1.0e-12)


def test_iga_rational_terms_avoid_denominator_square_underflow(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_basis_terms_at_point(
        **_kwargs: object,
    ) -> tuple[tuple[int, float, float, float], ...]:
        return (
            (0, 0.0, 0.0, 0.0),
            (1, 1.0, 1.0, 1.0),
        )

    monkeypatch.setattr(pg, "_basis_terms_at_point", _fake_basis_terms_at_point)

    terms = iga_backend_module._basis_terms_at_point_rational(
        x=0.25,
        y=0.75,
        resolution=2,
        spline_degree=1,
        n_basis_axis=2,
        knots_x=(0.0, 0.0, 1.0, 1.0),
        knots_y=(0.0, 0.0, 1.0, 1.0),
        bounds=(0.0, 0.0, 1.0, 1.0),
        weights=(1.0, 1.0e-300),
    )

    assert len(terms) == 2
    assert isclose(terms[1][1], 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    for _index, value, grad_x, grad_y in terms:
        assert isfinite(value)
        assert isfinite(grad_x)
        assert isfinite(grad_y)


def test_iga_rational_terms_scale_by_contributing_values(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_basis_terms_at_point(
        **_kwargs: object,
    ) -> tuple[tuple[int, float, float, float], ...]:
        return (
            (0, 0.0, 0.0, 0.0),
            (1, 1.0, 1.0, 0.0),
        )

    monkeypatch.setattr(pg, "_basis_terms_at_point", _fake_basis_terms_at_point)

    terms = iga_backend_module._basis_terms_at_point_rational(
        x=0.25,
        y=0.75,
        resolution=2,
        spline_degree=1,
        n_basis_axis=2,
        knots_x=(0.0, 0.0, 1.0, 1.0),
        knots_y=(0.0, 0.0, 1.0, 1.0),
        bounds=(0.0, 0.0, 1.0, 1.0),
        weights=(1.0e308, 1.0e-100),
    )

    assert len(terms) == 2
    assert isclose(terms[1][1], 1.0, rel_tol=0.0, abs_tol=1.0e-12)
    for _index, value, grad_x, grad_y in terms:
        assert isfinite(value)
        assert isfinite(grad_x)
        assert isfinite(grad_y)


def test_iga_rational_terms_reject_nonfinite_gradients(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_basis_terms_at_point(
        **_kwargs: object,
    ) -> tuple[tuple[int, float, float, float], ...]:
        return (
            (0, 1.0e-308, 1.0e200, 0.0),
            (1, 1.0, 0.0, 0.0),
        )

    monkeypatch.setattr(pg, "_basis_terms_at_point", _fake_basis_terms_at_point)

    with pytest.raises(ValueError, match="numerically unstable"):
        iga_backend_module._basis_terms_at_point_rational(
            x=0.25,
            y=0.75,
            resolution=2,
            spline_degree=1,
            n_basis_axis=2,
            knots_x=(0.0, 0.0, 1.0, 1.0),
            knots_y=(0.0, 0.0, 1.0, 1.0),
            bounds=(0.0, 0.0, 1.0, 1.0),
            weights=(1.0, 1.0e-308),
        )


def test_iga_nurbs_weights_modify_rational_lowering() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    bspline = _base_form()
    nurbs = _base_form()
    nurbs["metadata"] = {
        "geometry_map": "nurbs",
        "nurbs_weights": "1,1,1,1,2,1,1,1,1",
    }

    bspline_result = assemble_form(
        bspline,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )
    nurbs_result = assemble_form(
        nurbs,
        backend="iga",
        panel=panel,
        resolution=2,
        spline_degree=1,
        quadrature_order=2,
    )

    bspline_payload = cast(IGAAssemblyResult, bspline_result.payload)
    nurbs_payload = cast(IGAAssemblyResult, nurbs_result.payload)

    assert bspline_payload.execution_path == "bspline"
    assert nurbs_payload.execution_path == "nurbs_rational_single_patch"
    assert not isclose(
        bspline_payload.matrix_rows[4][4],
        nurbs_payload.matrix_rows[4][4],
        rel_tol=0.0,
        abs_tol=1.0e-12,
    )


def test_iga_rejects_unknown_geometry_map() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    form = _base_form()
    form["metadata"] = {"geometry_map": "foo"}

    with pytest.raises(CapabilityError) as error:
        assemble_form(
            form,
            backend="iga",
            panel=panel,
            resolution=8,
            spline_degree=2,
            quadrature_order=4,
        )

    assert error.value.diagnostic.code == "unsupported_geometry_map"
    assert error.value.diagnostic.alternatives == ("bspline", "nurbs")


def test_dgsem_strict_rejects_nurbs_geometry_map() -> None:
    form = _base_form()
    form["metadata"] = {"geometry_map": "nurbs", "dg_flux": "sipg"}

    with pytest.raises(CapabilityError) as error:
        assemble_form(
            form,
            backend="dgsem",
            overlay_payload=_overlay_contract(),
            strict=True,
        )

    assert error.value.diagnostic.code == "unsupported_geometry_map"
    assert error.value.diagnostic.alternatives == ("bspline",)


def test_dgsem_permissive_reports_nurbs_geometry_map_diagnostic() -> None:
    form = _base_form()
    form["metadata"] = {"geometry_map": "nurbs", "dg_flux": "sipg"}

    result = assemble_form(
        form,
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=False,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert any(d.code == "unsupported_geometry_map" for d in result.diagnostics)
    assert payload.geometry_map == "nurbs"


def test_iga_rejects_vector_value_shape() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)

    with pytest.raises(CapabilityError) as error:
        assemble_form(
            {
                "trial_space": "Vector(P2)",
                "test_space": "Vector(P2)",
                "value_shape": [2],
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
                "boundary_conditions": [{"kind": "essential", "value": 0.0}],
            },
            backend="iga",
            panel=panel,
        )

    assert error.value.diagnostic.code == "unsupported_value_shape"


def test_iga_permissive_reports_vector_value_shape_diagnostic() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)

    result = assemble_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [2],
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [{"kind": "essential", "value": 0.0}],
        },
        backend="iga",
        panel=panel,
        strict=False,
    )

    assert any(d.code == "unsupported_value_shape" for d in result.diagnostics)


def test_dgsem_accepts_vector_value_shape() -> None:
    result = assemble_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [2],
            "terms": [
                {"kind": "diffusion", "coefficient": 1.0},
                {"kind": "source", "coefficient": 1.0, "source": 0.0},
            ],
            "boundary_conditions": [{"kind": "essential", "value": 0.0}],
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert result.ir.value_shape == (2,)
    assert payload.value_shape == (2,)
    assert payload.volume_terms
    assert {entry.component for entry in payload.volume_lowering} == {0, 1}
    assert {entry.component for entry in payload.trace_lowering} == {0, 1}
    assert {entry.component for entry in payload.flux_lowering} == {0, 1}


def test_dgsem_vector_source_lowering_is_component_aware() -> None:
    result = assemble_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [2],
            "terms": [
                {
                    "kind": "source",
                    "coefficient": 1.0,
                    "source": [1.0, 2.0],
                }
            ],
            "boundary_conditions": [{"kind": "essential", "value": 0.0}],
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.volume_terms == (
        "component[0]:source:1:const:1",
        "component[1]:source:1:const:2",
    )
    assert payload.volume_lowering == (
        DGSEMVolumeLowering(
            kind="source",
            coefficient=1.0,
            operator_chain=(
                "grudge.op.mass",
                "grudge.op.inverse_mass",
            ),
            source_signature="const:1",
            component=0,
        ),
        DGSEMVolumeLowering(
            kind="source",
            coefficient=1.0,
            operator_chain=(
                "grudge.op.mass",
                "grudge.op.inverse_mass",
            ),
            source_signature="const:2",
            component=1,
        ),
    )
    assert payload.geometry_map == "bspline"


def test_dgsem_vector_term_signatures_use_numeric_component_order() -> None:
    result = assemble_form(
        {
            "trial_space": "Vector(P2)",
            "test_space": "Vector(P2)",
            "value_shape": [12],
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [{"kind": "essential", "value": 0.0}],
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    component_indices = [
        int(signature.split("]:", maxsplit=1)[0].removeprefix("component["))
        for signature in payload.volume_terms
    ]
    assert component_indices == list(range(12))


def test_dgsem_rejects_rank2_value_shape() -> None:
    with pytest.raises(CapabilityError) as error:
        assemble_form(
            {
                "trial_space": "TensorElement(P2)",
                "test_space": "TensorElement(P2)",
                "value_shape": [2, 2],
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            },
            backend="dgsem",
            overlay_payload=_overlay_contract(),
        )

    assert error.value.diagnostic.code == "unsupported_value_shape"


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


def test_iga_backend_mode_must_be_supported() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)
    with pytest.raises(ValueError, match="unsupported backend_mode"):
        assemble_form(
            _base_form(),
            backend="iga",
            panel=panel,
            backend_mode="jpls",  # type: ignore[arg-type]
        )


def test_dgsem_lowering_requires_overlay_payload() -> None:
    with pytest.raises(PrerequisiteError):
        assemble_form(_base_form(), backend="dgsem")


def test_dgsem_overlay_payload_must_be_contract_object() -> None:
    with pytest.raises(PrerequisiteError, match="MeshmodeCutOverlay"):
        assemble_form(
            _base_form(),
            backend="dgsem",
            overlay_payload=cast(Any, {"contract_version": 1}),
        )


def test_unknown_backend_reports_capability_error() -> None:
    with pytest.raises(CapabilityError) as error:
        assemble_form(_base_form(), backend="foo")  # type: ignore[arg-type]
    assert error.value.diagnostic.code == "unsupported_backend"


def test_dgsem_permissive_omits_unsupported_terms_from_lowering() -> None:
    result = assemble_form(
        {"terms": [{"kind": "convection", "coefficient": 1.0}]},
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=False,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.volume_terms == ()
    assert payload.volume_lowering == ()
    assert any(d.code == "unsupported_term" for d in payload.lowering_diagnostics)


def test_dgsem_overlay_contract_version_must_be_supported() -> None:
    with pytest.raises(ValueError, match="contract_version must be >= 1"):
        _overlay_contract(contract_version=0)


def test_dgsem_overlay_contract_version_must_be_integer() -> None:
    with pytest.raises(PrerequisiteError, match="integer meshmode cut-overlay"):
        assemble_form(
            _base_form(),
            backend="dgsem",
            overlay_payload=_overlay_contract(contract_version=cast(int, 1.5)),
        )


def test_dgsem_strict_rejects_overlay_diagnostics() -> None:
    with pytest.raises(PrerequisiteError, match="source_unmapped"):
        assemble_form(
            _base_form(),
            backend="dgsem",
            overlay_payload=_overlay_contract(
                diagnostics=(
                    MeshmodeOverlayDiagnostic(
                        code="source_unmapped",
                        detail="unused source",
                        source_element_id=99,
                    ),
                ),
            ),
            strict=True,
        )


def test_dgsem_permissive_passthrough_overlay_diagnostics() -> None:
    result = assemble_form(
        _base_form(),
        backend="dgsem",
        overlay_payload=_overlay_contract(
            statuses=("mapping_mismatch",),
            diagnostics=(
                MeshmodeOverlayDiagnostic(
                    code="target_unmapped",
                    detail="target 0 missing",
                    target_element_id=0,
                ),
            ),
        ),
        strict=False,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.overlay_statuses == ("mapping_mismatch",)
    assert payload.overlay_diagnostics
    assert payload.overlay_diagnostics[0].code == "target_unmapped"


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
        overlay_payload=_overlay_contract(),
        strict=True,
    )

    iga_payload = cast(IGAAssemblyResult, iga.payload)
    assert iga.ir == dgsem.ir
    dgsem_payload = cast(DGSEMLoweringResult, dgsem.payload)

    assert not iga.diagnostics
    assert not dgsem.diagnostics
    assert dgsem_payload.volume_terms == (
        "diffusion:1",
        "mass:0.1",
        "reaction:0.2",
        "source:1:const:1",
    )
    assert dgsem_payload.trace_terms == ("dirichlet:all:0", "neumann:top:1")
    assert dgsem_payload.overlay_statuses == ("ok",)
    assert iga_payload.geometry_map == "bspline"
    assert dgsem_payload.geometry_map == "bspline"
    assert not dgsem_payload.overlay_diagnostics
    assert not dgsem_payload.lowering_diagnostics
    assert dgsem_payload.volume_lowering == (
        DGSEMVolumeLowering(
            kind="diffusion",
            coefficient=1.0,
            operator_chain=(
                "grudge.op.weak_local_grad",
                "grudge.op.weak_local_div",
                "grudge.op.inverse_mass",
            ),
            source_signature=None,
        ),
        DGSEMVolumeLowering(
            kind="mass",
            coefficient=0.1,
            operator_chain=("grudge.op.mass", "grudge.op.inverse_mass"),
            source_signature=None,
        ),
        DGSEMVolumeLowering(
            kind="reaction",
            coefficient=0.2,
            operator_chain=("grudge.op.mass", "grudge.op.inverse_mass"),
            source_signature=None,
        ),
        DGSEMVolumeLowering(
            kind="source",
            coefficient=1.0,
            operator_chain=("grudge.op.mass", "grudge.op.inverse_mass"),
            source_signature="const:1",
        ),
    )
    assert dgsem_payload.trace_lowering == (
        DGSEMTraceLowering(
            kind="dirichlet",
            boundary="all",
            value=0.0,
            operator_chain=("grudge.op.project", "grudge.op.face_mass"),
        ),
        DGSEMTraceLowering(
            kind="neumann",
            boundary="top",
            value=1.0,
            operator_chain=("grudge.op.project", "grudge.op.face_mass"),
        ),
    )
    assert dgsem_payload.flux_terms == (
        "sipg:boundary_dirichlet:all:1:0:1",
        "sipg:boundary_neumann:top:1:1:1",
        "sipg:interior:interior:1:none:1",
    )


def test_dgsem_lowering_distinguishes_term_coefficients() -> None:
    low = assemble_form(
        {"terms": [{"kind": "mass", "coefficient": 0.1}]},
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    high = assemble_form(
        {"terms": [{"kind": "mass", "coefficient": 10.0}]},
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    low_payload = cast(DGSEMLoweringResult, low.payload)
    high_payload = cast(DGSEMLoweringResult, high.payload)

    assert low_payload.volume_terms == ("mass:0.1",)
    assert high_payload.volume_terms == ("mass:10",)
    assert low_payload.volume_terms != high_payload.volume_terms


def test_dgsem_lowering_distinguishes_boundary_values() -> None:
    unit = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [{"kind": "natural", "value": 1.0}],
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    double = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [{"kind": "natural", "value": 2.0}],
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    unit_payload = cast(DGSEMLoweringResult, unit.payload)
    double_payload = cast(DGSEMLoweringResult, double.payload)

    assert unit_payload.trace_terms == ("neumann:all:1",)
    assert double_payload.trace_terms == ("neumann:all:2",)
    assert unit_payload.trace_terms != double_payload.trace_terms


def test_dgsem_flux_lowering_uses_configured_penalty() -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 2.0}],
            "boundary_conditions": [{"kind": "essential", "value": 1.0}],
            "metadata": {"dg_flux": "sipg", "dg_penalty": 3.5},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.flux_family == "sipg"
    for entry in payload.flux_lowering:
        assert isclose(entry.penalty if entry.penalty is not None else -1.0, 3.5)


def test_dgsem_flux_lowering_rejects_unknown_family_in_strict_mode() -> None:
    with pytest.raises(PrerequisiteError, match="unsupported dg_flux"):
        assemble_form(
            {
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
                "metadata": {"dg_flux": "roe"},
            },
            backend="dgsem",
            overlay_payload=_overlay_contract(),
            strict=True,
        )


def test_dgsem_non_diffusion_form_skips_flux_metadata_validation() -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "mass", "coefficient": 2.0}],
            "metadata": {"dg_flux": "roe", "dg_penalty": "bad"},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=True,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.flux_lowering == ()
    assert payload.flux_terms == ()
    assert not payload.lowering_diagnostics


def test_dgsem_flux_lowering_fallback_in_permissive_mode() -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "metadata": {"dg_flux": "roe"},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=False,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.flux_family == "sipg"
    assert payload.lowering_diagnostics
    assert payload.lowering_diagnostics[0].code == "unsupported_flux_family"


def test_dgsem_flux_lowering_fallback_on_invalid_penalty_permissive() -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "metadata": {"dg_penalty": -4.0},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=False,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.flux_family == "sipg"
    assert any(d.code == "invalid_penalty" for d in payload.lowering_diagnostics)
    assert all(
        isclose(entry.penalty if entry.penalty is not None else -1.0, 1.0)
        for entry in payload.flux_lowering
    )


def test_dgsem_non_sipg_ignores_invalid_penalty_metadata() -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "metadata": {"dg_flux": "central", "dg_penalty": "bad"},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=True,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    assert payload.flux_family == "central"
    assert not payload.lowering_diagnostics
    assert all(entry.penalty is None for entry in payload.flux_lowering)


@pytest.mark.parametrize(
    ("family", "expected_boundary_chain", "expected_interior_chain", "uses_penalty"),
    [
        (
            "sipg",
            (
                "grudge.op.bdry_trace_pair",
                "grudge.op.project",
                "grudge.op.face_mass",
                "grudge.op.inverse_mass",
            ),
            (
                "grudge.op.interior_trace_pairs",
                "grudge.op.project",
                "grudge.op.face_mass",
                "grudge.op.inverse_mass",
            ),
            True,
        ),
        (
            "central",
            (
                "grudge.op.bdry_trace_pair",
                "grudge.op.project",
                "grudge.op.face_mass",
            ),
            (
                "grudge.op.interior_trace_pairs",
                "grudge.op.project",
                "grudge.op.face_mass",
            ),
            False,
        ),
        (
            "upwind",
            (
                "grudge.op.bdry_trace_pair",
                "grudge.op.project",
                "grudge.op.face_mass",
            ),
            (
                "grudge.op.interior_trace_pairs",
                "grudge.op.project",
                "grudge.op.face_mass",
            ),
            False,
        ),
    ],
)
def test_dgsem_flux_lowering_uses_family_specific_operator_chains(
    family: str,
    expected_boundary_chain: tuple[str, ...],
    expected_interior_chain: tuple[str, ...],
    uses_penalty: bool,
) -> None:
    result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [{"kind": "essential", "value": 0.0}],
            "metadata": {"dg_flux": family, "dg_penalty": 2.5},
        },
        backend="dgsem",
        overlay_payload=_overlay_contract(),
        strict=True,
    )
    payload = cast(DGSEMLoweringResult, result.payload)

    boundary_entries = [
        entry for entry in payload.flux_lowering if entry.role == "boundary_dirichlet"
    ]
    interior_entries = [
        entry for entry in payload.flux_lowering if entry.role == "interior"
    ]
    assert boundary_entries
    assert interior_entries
    assert all(
        entry.operator_chain == expected_boundary_chain for entry in boundary_entries
    )
    assert all(
        entry.operator_chain == expected_interior_chain for entry in interior_entries
    )

    if uses_penalty:
        assert all(
            isclose(entry.penalty if entry.penalty is not None else -1.0, 2.5)
            for entry in payload.flux_lowering
        )
    else:
        assert all(entry.penalty is None for entry in payload.flux_lowering)


def test_dgsem_lowering_distinguishes_callable_source_closures() -> None:
    def make_source(scale: float):
        return lambda x, y: scale * (x + y)

    low = assemble_form(
        {"terms": [{"kind": "source", "source": make_source(1.0)}]},
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    high = assemble_form(
        {"terms": [{"kind": "source", "source": make_source(2.0)}]},
        backend="dgsem",
        overlay_payload=_overlay_contract(),
    )
    low_payload = cast(DGSEMLoweringResult, low.payload)
    high_payload = cast(DGSEMLoweringResult, high.payload)

    assert low_payload.volume_terms != high_payload.volume_terms


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


def test_marker_boundary_selector_requires_mapping() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)

    with pytest.raises(ValueError, match="missing selector mapping"):
        assemble_form(
            {
                "terms": [{"kind": "diffusion", "coefficient": 1.0}],
                "boundary_conditions": [
                    {"kind": "natural", "value": 1.0, "boundary": "marker:42"}
                ],
            },
            backend="iga",
            panel=panel,
            strict=True,
        )


def test_marker_boundary_selector_matches_named_selector() -> None:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=128)

    marker_result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [
                {"kind": "natural", "value": 1.0, "boundary": "marker:3"}
            ],
            "metadata": {"boundary_marker:3": "top"},
        },
        backend="iga",
        panel=panel,
        strict=True,
    )
    top_result = assemble_form(
        {
            "terms": [{"kind": "diffusion", "coefficient": 1.0}],
            "boundary_conditions": [
                {"kind": "natural", "value": 1.0, "boundary": "top"}
            ],
        },
        backend="iga",
        panel=panel,
        strict=True,
    )

    marker_rhs = cast(IGAAssemblyResult, marker_result.payload).rhs
    top_rhs = cast(IGAAssemblyResult, top_result.payload).rhs
    for marker_value, top_value in zip(marker_rhs, top_rhs, strict=True):
        assert isclose(marker_value, top_value, abs_tol=1.0e-12, rel_tol=0.0)


def test_natural_boundary_all_matches_sum_of_box_edges_for_square() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))
    )

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


def test_natural_boundary_all_includes_non_box_trimmed_edges() -> None:
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

    all_total = sum(rhs_all)
    box_total = sum(rhs_left) + sum(rhs_right) + sum(rhs_bottom) + sum(rhs_top)
    assert all_total > box_total + 1.0e-6
