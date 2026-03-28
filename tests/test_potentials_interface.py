from __future__ import annotations

from types import SimpleNamespace
from typing import Any, cast

import pytest

import cutkit.cad as cad
import cutkit.potentials as potentials
from cutkit.cad import Box2D, Box3D, CadFace2D, CadSolid3D
from cutkit.potentials import (
    BoundaryTraceBatch,
    NearfieldTargetBatch,
    NearfieldTargetEvaluation,
    LocalNearfieldSolveBatch,
    LocalOperatorBatch,
    PotentialCompositionResult,
    RestrictedSourceBatch,
    SignedSourceCloud,
    SignedSourceCloudBatch,
    SourceBoxSelectionBatch,
    assemble_local_nearfield_operators,
    build_nearfield_target_batch,
    build_local_box_boundary_trace,
    build_restricted_sources_from_interaction_lists,
    build_restricted_sources_from_selection,
    build_signed_source_cloud_2d,
    build_signed_source_cloud_3d,
    build_source_box_selection_from_lists,
    compose_far_and_near_potentials,
    evaluate_local_nearfield_targets,
    solve_local_operator_batch,
    source_cloud_over_boxes_2d,
    source_cloud_over_boxes_3d,
)


def test_signed_source_cloud_validates_point_arity() -> None:
    with pytest.raises(ValueError, match="point arity mismatch"):
        SignedSourceCloud(
            dim=2,
            points=((0.0, 0.0, 0.0),),
            weights=(1.0,),
            charges=(2.0,),
            backend_mode="folded",
            order=3,
        )


def test_signed_source_cloud_batch_statuses_shaped_scalar() -> None:
    batch = SignedSourceCloudBatch(
        dim=3,
        shape=(),
        box_bounds=((0.0, 1.0, 0.0, 1.0, 0.0, 1.0),),
        statuses=("ok",),
        errors=(None,),
        point_ptr=(0, 1),
        points=((0.1, 0.2, 0.3),),
        weights=(0.5,),
        charges=(1.5,),
        source_box_index=(0,),
        backend_mode="folded",
        order=5,
    )

    assert batch.statuses_shaped() == "ok"


def test_signed_source_cloud_batch_volumential_arrays_tuple_mode() -> None:
    batch = SignedSourceCloudBatch(
        dim=3,
        shape=(2,),
        box_bounds=(
            (0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
            (1.0, 2.0, 0.0, 1.0, 0.0, 1.0),
        ),
        statuses=("ok", "ok"),
        errors=(None, None),
        point_ptr=(0, 1, 3),
        points=((0.1, 0.2, 0.3), (1.1, 0.2, 0.3), (1.6, 0.4, 0.5)),
        weights=(0.5, 0.25, -0.25),
        charges=(1.0, 2.0, -3.0),
        source_box_index=(0, 1, 1),
        backend_mode="folded",
        order=4,
    )

    arrays = batch.as_volumential_arrays(use_numpy=False)
    assert arrays["dim"] == 3
    assert arrays["shape"] == (2,)
    assert arrays["coords"] == (
        (0.1, 1.1, 1.6),
        (0.2, 0.2, 0.4),
        (0.3, 0.3, 0.5),
    )
    assert arrays["charges"] == (1.0, 2.0, -3.0)
    assert arrays["point_ptr"] == (0, 1, 3)


def test_signed_source_cloud_volumential_arrays_require_numpy_when_requested(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cloud = SignedSourceCloud(
        dim=2,
        points=((0.0, 0.0),),
        weights=(1.0,),
        charges=(2.0,),
        backend_mode="folded",
        order=3,
    )
    monkeypatch.setattr(potentials, "_np", None)

    with pytest.raises(RuntimeError, match="NumPy is required"):
        cloud.as_volumential_arrays(use_numpy=True)


def test_boundary_trace_batch_validates_pointer_terminal_value() -> None:
    with pytest.raises(ValueError, match="terminal value mismatch"):
        BoundaryTraceBatch(
            dim=2,
            shape=(1,),
            box_bounds=((0.0, 1.0, 0.0, 1.0),),
            statuses=("ok",),
            errors=(None,),
            trace_ptr=(0, 1),
            trace_points=(),
            trace_values=(),
        )


def test_local_operator_batch_validates_operator_mode_payloads() -> None:
    with pytest.raises(ValueError, match="requires matvec_kernel_id"):
        LocalOperatorBatch(
            dim=2,
            operator_mode="matrix_free",
            resolution=2,
            spline_degree=2,
            shape=(1,),
            box_bounds=((0.0, 1.0, 0.0, 1.0),),
            statuses=("ok",),
            errors=(None,),
            free_dof_ptr=(0, 1),
            rhs=(1.0,),
            free_global_ptr=(0, 1),
            free_global_index=(0,),
            fixed_dof_ptr=(0, 0),
            fixed_dof_index=(),
            fixed_dof_value=(),
            csr_indptr=None,
            csr_indices=None,
            csr_data=None,
            matvec_kernel_id=None,
        )


def test_local_operator_batch_matrix_free_matvec_requires_registered_kernel() -> None:
    operators = LocalOperatorBatch(
        dim=2,
        operator_mode="matrix_free",
        resolution=2,
        spline_degree=2,
        shape=(1,),
        box_bounds=((0.0, 1.0, 0.0, 1.0),),
        statuses=("ok",),
        errors=(None,),
        free_dof_ptr=(0, 1),
        rhs=(1.0,),
        free_global_ptr=(0, 1),
        free_global_index=(0,),
        fixed_dof_ptr=(0, 0),
        fixed_dof_index=(),
        fixed_dof_value=(),
        csr_indptr=None,
        csr_indices=None,
        csr_data=None,
        matvec_kernel_id="local-mf-v1",
    )

    with pytest.raises(ValueError, match="unknown matrix_free kernel"):
        operators.matvec((2.0,))


def test_trace_fit_projects_to_boundary_plane_in_3d() -> None:
    value = potentials._fit_trace_value(
        position=(0.0, 0.5, 0.5),
        boundary_planes=((0, 0.0),),
        trace_points=((0.0, 0.0, 0.5), (0.0, 1.0, 0.5), (1.0, 0.5, 0.5)),
        trace_values=(0.0, 2.0, 100.0),
        dim=3,
    )

    assert value == pytest.approx(1.0, rel=1.0e-2, abs=1.0e-2)


def test_trace_fit_recovers_linear_edge_profile_in_2d() -> None:
    value = potentials._fit_trace_value(
        position=(0.25, 0.0),
        boundary_planes=((1, 0.0),),
        trace_points=((0.0, 0.0), (1.0, 0.0), (0.0, 1.0), (1.0, 1.0)),
        trace_values=(0.0, 2.0, 50.0, 50.0),
        dim=2,
    )

    assert value == pytest.approx(0.5, rel=1.0e-2, abs=1.0e-2)


def test_build_source_box_selection_from_lists_deduplicates_order() -> None:
    selection = build_source_box_selection_from_lists(
        (2,),
        self_boxes=((0, 1), (2,)),
        list1_boxes=((1, 3), (2, 4)),
        list3_boxes=((3,), (4, 5)),
        include=("self", "list1", "list3"),
    )

    assert isinstance(selection, SourceBoxSelectionBatch)
    assert selection.source_box_ptr == (0, 3, 6)
    assert selection.source_box_index == (0, 1, 3, 2, 4, 5)


def test_build_restricted_sources_from_selection_maps_cloud_points() -> None:
    cloud = SignedSourceCloudBatch(
        dim=2,
        shape=(3,),
        box_bounds=((0.0, 1.0, 0.0, 1.0), (1.0, 2.0, 0.0, 1.0), (2.0, 3.0, 0.0, 1.0)),
        statuses=("ok", "ok", "ok"),
        errors=(None, None, None),
        point_ptr=(0, 2, 3, 5),
        points=((0.1, 0.1), (0.2, 0.2), (1.5, 0.4), (2.2, 0.8), (2.8, 0.2)),
        weights=(1.0, 1.0, 1.0, 1.0, 1.0),
        charges=(1.0, 2.0, 3.0, 4.0, 5.0),
        source_box_index=(0, 0, 1, 2, 2),
        backend_mode="folded",
        order=3,
    )
    selection = SourceBoxSelectionBatch(
        shape=(2,),
        source_box_ptr=(0, 2, 3),
        source_box_index=(0, 2, 1),
    )

    restricted = build_restricted_sources_from_selection(
        source_cloud=cloud,
        selection=selection,
    )

    assert restricted.shape == (2,)
    assert restricted.source_ptr == (0, 4, 5)
    assert restricted.source_charges == (1.0, 2.0, 4.0, 5.0, 3.0)


def test_build_restricted_sources_from_interaction_lists_convenience() -> None:
    cloud = SignedSourceCloudBatch(
        dim=3,
        shape=(2,),
        box_bounds=((0.0, 1.0, 0.0, 1.0, 0.0, 1.0), (1.0, 2.0, 0.0, 1.0, 0.0, 1.0)),
        statuses=("ok", "ok"),
        errors=(None, None),
        point_ptr=(0, 1, 2),
        points=((0.1, 0.1, 0.1), (1.2, 0.3, 0.4)),
        weights=(1.0, 1.0),
        charges=(10.0, 20.0),
        source_box_index=(0, 1),
        backend_mode="folded",
        order=3,
    )

    restricted = build_restricted_sources_from_interaction_lists(
        source_cloud=cloud,
        shape=(1,),
        self_boxes=(0,),
        list1_boxes=(1,),
        include=("self", "list1"),
    )

    assert isinstance(restricted, RestrictedSourceBatch)
    assert restricted.dim == 3
    assert restricted.source_ptr == (0, 2)
    assert restricted.source_charges == (10.0, 20.0)


def test_build_nearfield_target_batch_maps_points_by_box() -> None:
    mapped = build_nearfield_target_batch(
        dim=2,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        points=((0.2, 0.2), (1.4, 0.5), (3.0, 3.0)),
    )

    assert isinstance(mapped, NearfieldTargetBatch)
    assert mapped.shape == (2,)
    assert mapped.statuses == ("ok", "ok")
    assert mapped.target_ptr == (0, 1, 2)
    assert mapped.target_points == ((0.2, 0.2), (1.4, 0.5))
    assert mapped.target_input_index == (0, 1)


def test_build_nearfield_target_batch_array_mode_3d() -> None:
    mapped = build_nearfield_target_batch(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        x=(0.25, 1.2),
        y=(0.25, 0.2),
        z=(0.25, 0.2),
    )

    assert mapped.shape == ()
    assert mapped.input_shape == (2,)
    assert mapped.target_ptr == (0, 1)
    assert mapped.target_input_index == (0,)


def test_build_local_box_boundary_trace_object_vs_array_equivalence_2d() -> None:
    boxes = (Box2D(0.0, 1.0, 0.0, 1.0), Box2D(1.0, 2.0, 0.0, 1.0))
    obj = build_local_box_boundary_trace(
        dim=2,
        boxes=boxes,
        trace_order=4,
        farfield_potential=lambda x, y: x - y,
    )
    arr = build_local_box_boundary_trace(
        dim=2,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        trace_order=4,
        farfield_potential=lambda x, y: x - y,
    )

    assert obj.shape == arr.shape
    assert obj.statuses == arr.statuses
    assert obj.trace_ptr == arr.trace_ptr
    assert obj.trace_points == arr.trace_points
    assert obj.trace_values == pytest.approx(arr.trace_values)


def test_build_local_box_boundary_trace_object_vs_array_equivalence_3d() -> None:
    boxes = (Box3D(0.0, 1.0, 0.0, 1.0, 0.0, 1.0),)
    obj = build_local_box_boundary_trace(
        dim=3,
        boxes=boxes,
        trace_order=3,
        farfield_potential=lambda x, y, z: x + y - z,
    )
    arr = build_local_box_boundary_trace(
        dim=3,
        x0=(0.0,),
        x1=(1.0,),
        y0=(0.0,),
        y1=(1.0,),
        z0=(0.0,),
        z1=(1.0,),
        trace_order=3,
        farfield_potential=lambda x, y, z: x + y - z,
    )

    assert obj.shape == arr.shape
    assert obj.statuses == arr.statuses
    assert obj.trace_ptr == arr.trace_ptr
    assert obj.trace_points == arr.trace_points
    assert obj.trace_values == pytest.approx(arr.trace_values)


def test_build_nearfield_target_batch_object_vs_array_equivalence_2d() -> None:
    obj = build_nearfield_target_batch(
        dim=2,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        points=((0.2, 0.2), (1.2, 0.3), (2.0, 2.0)),
    )
    arr = build_nearfield_target_batch(
        dim=2,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        x=(0.2, 1.2, 2.0),
        y=(0.2, 0.3, 2.0),
    )

    assert obj.shape == arr.shape
    assert obj.input_shape == arr.input_shape
    assert obj.target_ptr == arr.target_ptr
    assert obj.target_points == arr.target_points
    assert obj.target_input_index == arr.target_input_index


def test_build_nearfield_target_batch_object_vs_array_equivalence_3d() -> None:
    obj = build_nearfield_target_batch(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        points=((0.1, 0.2, 0.3), (2.0, 2.0, 2.0)),
    )
    arr = build_nearfield_target_batch(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        x=(0.1, 2.0),
        y=(0.2, 2.0),
        z=(0.3, 2.0),
    )

    assert obj.shape == arr.shape
    assert obj.input_shape == arr.input_shape
    assert obj.target_ptr == arr.target_ptr
    assert obj.target_points == arr.target_points
    assert obj.target_input_index == arr.target_input_index


def test_build_signed_source_cloud_2d_builds_signed_charges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    captured: dict[str, object] = {}

    def fake_rule(
        _panel: object,
        *,
        order: int,
        anchor: tuple[float, float] | None,
        require_interior_anchor: bool,
        anchor_sample_points: int = 48,
    ) -> SimpleNamespace:
        captured["order"] = order
        captured["anchor"] = anchor
        captured["require_interior_anchor"] = require_interior_anchor
        captured["anchor_sample_points"] = anchor_sample_points
        return SimpleNamespace(
            rule=SimpleNamespace(
                points=((0.0, 0.0), (1.0, 0.5)),
                weights=(0.2, -0.1),
            )
        )

    monkeypatch.setattr(potentials, "folded_curve_quadrature_rule", fake_rule)

    cloud = build_signed_source_cloud_2d(
        panel=cast(Any, SimpleNamespace()),
        density=lambda x, y: x + 2.0 * y,
        order=3,
        backend_mode="jplus",
    )

    assert captured["order"] == 3
    assert captured["anchor"] is None
    assert captured["require_interior_anchor"] is True
    assert cloud.dim == 2
    assert cloud.points == ((0.0, 0.0), (1.0, 0.5))
    assert cloud.weights == (0.2, -0.1)
    assert cloud.charges == (0.0, -0.2)


def test_build_signed_source_cloud_3d_honors_jplus_mode_default_seed(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seen: dict[str, object] = {}

    def fake_boundary_rule(
        _boundary: tuple[tuple[tuple[float, float, float], ...], ...],
        *,
        seed: tuple[float, float, float],
        order: int,
    ) -> SimpleNamespace:
        seen["seed"] = seed
        seen["order"] = order
        return SimpleNamespace(points=((0.5, 0.5, 0.5),), weights=(0.25,))

    monkeypatch.setattr(potentials, "boundary_quadrature_rule_3d", fake_boundary_rule)

    cloud = build_signed_source_cloud_3d(
        boundary=(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),),
        density=lambda x, y, z: x + y + z,
        order=4,
        backend_mode="jplus",
        seed="grid-best",
    )

    assert seen["seed"] == (1.0, 1.0, 1.0)
    assert seen["order"] == 4
    assert cloud.dim == 3
    assert cloud.weights == (0.25,)
    assert cloud.charges == (0.375,)


def test_build_signed_source_cloud_2d_constant_density_conserves_weights(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_rule(
        _panel: object,
        *,
        order: int,
        anchor: tuple[float, float] | None,
        require_interior_anchor: bool,
        anchor_sample_points: int = 48,
    ) -> SimpleNamespace:
        _ = (order, anchor, require_interior_anchor, anchor_sample_points)
        return SimpleNamespace(
            rule=SimpleNamespace(
                points=((0.0, 0.0), (1.0, 0.5), (0.5, 0.25)),
                weights=(0.2, -0.1, 0.4),
            )
        )

    monkeypatch.setattr(potentials, "folded_curve_quadrature_rule", fake_rule)

    cloud = build_signed_source_cloud_2d(
        panel=cast(Any, SimpleNamespace()),
        density=lambda x, y: 1.0,
        order=4,
    )

    assert cloud.charges == pytest.approx(cloud.weights)
    assert sum(cloud.charges) == pytest.approx(sum(cloud.weights))


def test_build_signed_source_cloud_3d_smooth_density_matches_manual_charges(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def fake_boundary_rule(
        _boundary: tuple[tuple[tuple[float, float, float], ...], ...],
        *,
        seed: tuple[float, float, float],
        order: int,
    ) -> SimpleNamespace:
        _ = (seed, order)
        return SimpleNamespace(
            points=((0.25, 0.25, 0.25), (0.75, 0.25, 0.5)),
            weights=(0.2, -0.15),
        )

    monkeypatch.setattr(potentials, "boundary_quadrature_rule_3d", fake_boundary_rule)

    cloud = build_signed_source_cloud_3d(
        boundary=(((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),),
        density=lambda x, y, z: 2.0 * x - y + 0.5 * z,
        order=5,
    )

    expected = (
        (2.0 * 0.25 - 0.25 + 0.5 * 0.25) * 0.2,
        (2.0 * 0.75 - 0.25 + 0.5 * 0.5) * -0.15,
    )
    assert cloud.charges == pytest.approx(expected)


def test_source_cloud_over_boxes_2d_object_vs_array_equivalence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    face = CadFace2D.from_face("face")

    def fake_intersect(
        _face: object,
        *,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> tuple[Any, ...]:
        return ({"bounds": (x0, x1, y0, y1)},)

    def fake_build(
        panel: Any,
        *,
        density: Any,
        order: int,
        backend_mode: potentials.FarfieldBackendMode,
    ) -> SignedSourceCloud:
        x0, x1, y0, y1 = panel["bounds"]
        cx = 0.5 * (x0 + x1)
        cy = 0.5 * (y0 + y1)
        charge = float(density(cx, cy))
        return SignedSourceCloud(
            dim=2,
            points=((cx, cy),),
            weights=(1.0,),
            charges=(charge,),
            backend_mode=backend_mode,
            order=order,
        )

    monkeypatch.setattr(cad, "intersect_face_with_rectangle", fake_intersect)
    monkeypatch.setattr(potentials, "build_signed_source_cloud_2d", fake_build)

    boxes = (Box2D(0.0, 1.0, 0.0, 1.0), Box2D(1.0, 2.0, 0.0, 1.0))
    obj = source_cloud_over_boxes_2d(
        face,
        density=lambda x, y: x + y,
        boxes=boxes,
        order=3,
    )
    arr = source_cloud_over_boxes_2d(
        face,
        density=lambda x, y: x + y,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        order=3,
    )

    assert obj.shape == arr.shape
    assert obj.statuses == arr.statuses
    assert obj.point_ptr == arr.point_ptr
    assert obj.points == arr.points
    assert obj.weights == pytest.approx(arr.weights)
    assert obj.charges == pytest.approx(arr.charges)
    assert obj.source_box_index == arr.source_box_index


def test_source_cloud_over_boxes_3d_object_vs_array_equivalence(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solid = CadSolid3D.from_solid("solid")

    def fake_clip(
        _solid: object,
        *,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
        z0: float,
        z1: float,
    ) -> Any:
        return {"bounds": (x0, x1, y0, y1, z0, z1)}

    def fake_boundary(
        shape: Any,
        *,
        linear_deflection: float,
        angular_deflection: float,
        tol: float,
    ) -> tuple[tuple[tuple[float, float, float], ...], ...]:
        _ = (linear_deflection, angular_deflection, tol)
        x0, x1, y0, y1, z0, z1 = shape["bounds"]
        return (((x0, y0, z0), (x1, y0, z0), (x0, y1, z1)),)

    def fake_build(
        boundary: tuple[tuple[tuple[float, float, float], ...], ...],
        *,
        density: Any,
        seed: cad.SeedInput3D,
        order: int,
        backend_mode: potentials.FarfieldBackendMode,
    ) -> SignedSourceCloud:
        _ = (seed,)
        p0, p1, p2 = boundary[0]
        cx = 0.5 * (p0[0] + p1[0])
        cy = 0.5 * (p0[1] + p2[1])
        cz = 0.5 * (p0[2] + p2[2])
        charge = float(density(cx, cy, cz))
        return SignedSourceCloud(
            dim=3,
            points=((cx, cy, cz),),
            weights=(1.0,),
            charges=(charge,),
            backend_mode=backend_mode,
            order=order,
        )

    monkeypatch.setattr(cad, "clip_solid_with_axis_aligned_box", fake_clip)
    monkeypatch.setattr(
        potentials, "solid_to_oriented_boundary_triangles", fake_boundary
    )
    monkeypatch.setattr(potentials, "build_signed_source_cloud_3d", fake_build)

    boxes = (Box3D(0.0, 1.0, 0.0, 1.0, 0.0, 1.0), Box3D(1.0, 2.0, 0.0, 1.0, 0.0, 1.0))
    obj = source_cloud_over_boxes_3d(
        solid,
        density=lambda x, y, z: x + y + z,
        boxes=boxes,
        order=3,
    )
    arr = source_cloud_over_boxes_3d(
        solid,
        density=lambda x, y, z: x + y + z,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        order=3,
    )

    assert obj.shape == arr.shape
    assert obj.statuses == arr.statuses
    assert obj.point_ptr == arr.point_ptr
    assert obj.points == arr.points
    assert obj.weights == pytest.approx(arr.weights)
    assert obj.charges == pytest.approx(arr.charges)
    assert obj.source_box_index == arr.source_box_index


def test_source_cloud_over_boxes_2d_batches_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    face = CadFace2D.from_face("face")

    def fake_clip_boxes(
        self: CadFace2D,
        boxes: object = None,
        *,
        x0: object = None,
        x1: object = None,
        y0: object = None,
        y1: object = None,
        strict: bool = True,
    ) -> cad.CadBatchClip2D:
        _ = (self, boxes, x0, x1, y0, y1, strict)
        return cad.CadBatchClip2D(
            shape=(2,),
            box_bounds=((0.0, 1.0, 0.0, 1.0), (1.0, 2.0, 0.0, 1.0)),
            statuses=("ok", "empty"),
            panels=cast(Any, ((SimpleNamespace(name="p0"),), ())),
            errors=(None, None),
        )

    def fake_build(
        panel: object,
        *,
        density: object,
        order: int,
        backend_mode: potentials.FarfieldBackendMode,
    ) -> SignedSourceCloud:
        _ = (density,)
        if getattr(panel, "name", "") == "p0":
            return SignedSourceCloud(
                dim=2,
                points=((0.25, 0.5),),
                weights=(0.4,),
                charges=(0.8,),
                backend_mode=backend_mode,
                order=order,
            )
        raise AssertionError("unexpected panel")

    monkeypatch.setattr(CadFace2D, "clip_boxes", fake_clip_boxes)
    monkeypatch.setattr(potentials, "build_signed_source_cloud_2d", fake_build)

    batch = source_cloud_over_boxes_2d(
        face,
        density=lambda x, y: x + y,
        order=3,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
    )

    assert batch.dim == 2
    assert batch.shape == (2,)
    assert batch.statuses == ("ok", "empty")
    assert batch.point_ptr == (0, 1, 1)
    assert batch.points == ((0.25, 0.5),)
    assert batch.source_box_index == (0,)


def test_source_cloud_over_boxes_3d_batches_points(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solid = CadSolid3D.from_solid("solid")

    def fake_clip_boxes(
        self: CadSolid3D,
        boxes: object = None,
        *,
        x0: object = None,
        x1: object = None,
        y0: object = None,
        y1: object = None,
        z0: object = None,
        z1: object = None,
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
        strict: bool = True,
        validate_boundary: bool = False,
    ) -> cad.CadBatchClip3D:
        _ = (
            self,
            boxes,
            x0,
            x1,
            y0,
            y1,
            z0,
            z1,
            linear_deflection,
            angular_deflection,
            tol,
            strict,
            validate_boundary,
        )
        return cad.CadBatchClip3D(
            shape=(2,),
            box_bounds=(
                (0.0, 1.0, 0.0, 1.0, 0.0, 1.0),
                (1.0, 2.0, 0.0, 1.0, 0.0, 1.0),
            ),
            statuses=("ok", "invalid_box"),
            solids=(CadSolid3D.from_solid("clipped"), None),
            errors=(None, "bad box"),
        )

    def fake_boundary(
        _shape: object,
        *,
        linear_deflection: float,
        angular_deflection: float,
        tol: float,
    ) -> tuple[tuple[tuple[float, float, float], ...], ...]:
        _ = (linear_deflection, angular_deflection, tol)
        return (((0.0, 0.0, 0.0), (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)),)

    def fake_build(
        boundary: tuple[tuple[tuple[float, float, float], ...], ...],
        *,
        density: object,
        seed: cad.SeedInput3D,
        order: int,
        backend_mode: potentials.FarfieldBackendMode,
    ) -> SignedSourceCloud:
        _ = (boundary, density, seed)
        return SignedSourceCloud(
            dim=3,
            points=((0.2, 0.3, 0.4),),
            weights=(0.6,),
            charges=(0.6,),
            backend_mode=backend_mode,
            order=order,
        )

    monkeypatch.setattr(CadSolid3D, "clip_boxes", fake_clip_boxes)
    monkeypatch.setattr(
        potentials, "solid_to_oriented_boundary_triangles", fake_boundary
    )
    monkeypatch.setattr(potentials, "build_signed_source_cloud_3d", fake_build)

    batch = source_cloud_over_boxes_3d(
        solid,
        density=lambda x, y, z: x + y + z,
        order=3,
        x0=(0.0, 1.0),
        x1=(1.0, 2.0),
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )

    assert batch.dim == 3
    assert batch.shape == (2,)
    assert batch.statuses == ("ok", "invalid_box")
    assert batch.errors == (None, "bad box")
    assert batch.point_ptr == (0, 1, 1)
    assert batch.points == ((0.2, 0.3, 0.4),)
    assert batch.source_box_index == (0,)


def test_build_local_box_boundary_trace_builds_values() -> None:
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=3,
        farfield_potential=lambda x, y: x + y,
    )

    assert trace.dim == 2
    assert trace.shape == ()
    assert trace.statuses == ("ok",)
    assert trace.trace_ptr == (0, 8)
    assert len(trace.trace_points) == 8
    assert len(trace.trace_values) == 8


def test_assemble_local_nearfield_operators_and_solve() -> None:
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=3,
        farfield_potential=lambda x, y: x - y,
    )
    sources = RestrictedSourceBatch(
        dim=2,
        shape=trace.shape,
        source_ptr=(0, 2),
        source_points=((0.25, 0.25), (0.75, 0.75)),
        source_charges=(1.0, -0.5),
    )

    assembled = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        operator_mode="assembled",
    )

    matrix_free = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        operator_mode="matrix_free",
    )

    assert assembled.statuses == ("ok",)
    assert matrix_free.statuses == ("ok",)
    assert assembled.free_dof_ptr == matrix_free.free_dof_ptr
    assert assembled.rhs == matrix_free.rhs

    assembled_export = assembled.as_assembled_arrays(use_numpy=False)
    matrix_free_export = matrix_free.as_matrix_free_descriptor(use_numpy=False)
    assert assembled_export["csr_indptr"][0] == 0
    assert assembled_export["resolution"] == 2
    assert matrix_free_export["matvec_kernel_id"] is not None
    assert matrix_free_export["free_dof_ptr"] == assembled_export["free_dof_ptr"]

    vector = tuple(1.0 for _ in assembled.rhs)
    assert assembled.matvec(vector) == pytest.approx(matrix_free.matvec(vector))

    assembled_solve = solve_local_operator_batch(assembled)
    matrix_free_solve = solve_local_operator_batch(matrix_free)

    assert assembled_solve.statuses == ("ok",)
    assert matrix_free_solve.statuses == ("ok",)
    assert assembled_solve.solution == pytest.approx(matrix_free_solve.solution)
    assert assembled_solve.residual_norms[0] is not None
    assert matrix_free_solve.residual_norms[0] is not None

    with pytest.raises(ValueError, match="operator_mode='assembled'"):
        matrix_free.as_assembled_arrays(use_numpy=False)
    with pytest.raises(ValueError, match="operator_mode='matrix_free'"):
        assembled.as_matrix_free_descriptor(use_numpy=False)


def test_evaluate_local_nearfield_targets_matches_operator_modes() -> None:
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=4,
        farfield_potential=lambda x, y: x + y,
    )
    sources = RestrictedSourceBatch(
        dim=2,
        shape=trace.shape,
        source_ptr=(0, 2),
        source_points=((0.2, 0.2), (0.8, 0.8)),
        source_charges=(1.0, -0.25),
    )

    assembled = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        operator_mode="assembled",
    )
    matrix_free = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        operator_mode="matrix_free",
    )

    assembled_solve = solve_local_operator_batch(assembled)
    matrix_free_solve = solve_local_operator_batch(matrix_free)

    targets = build_nearfield_target_batch(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        points=((0.25, 0.25), (0.75, 0.75), (2.0, 2.0)),
    )

    assembled_eval = evaluate_local_nearfield_targets(
        operators=assembled,
        solve=assembled_solve,
        targets=targets,
    )
    matrix_free_eval = evaluate_local_nearfield_targets(
        operators=matrix_free,
        solve=matrix_free_solve,
        targets=targets,
    )

    assert isinstance(assembled_eval, NearfieldTargetEvaluation)
    assert assembled_eval.hit_count == (1, 1, 0)
    assert assembled_eval.values == pytest.approx(matrix_free_eval.values)


def test_compose_far_and_near_potentials_modes() -> None:
    near_eval = NearfieldTargetEvaluation(
        dim=2,
        input_shape=(2,),
        values=(1.0, 2.0),
        hit_count=(1, 1),
    )

    add_mode = compose_far_and_near_potentials(
        far_values=(10.0, 20.0),
        near_evaluation=near_eval,
    )
    assert isinstance(add_mode, PotentialCompositionResult)
    assert add_mode.mode == "far_plus_near"
    assert add_mode.combined_values == pytest.approx((11.0, 22.0))

    subtract_mode = compose_far_and_near_potentials(
        far_values=(10.0, 20.0),
        near_evaluation=near_eval,
        far_includes_near=True,
        near_direct_values=(0.5, 1.5),
    )
    assert subtract_mode.mode == "far_minus_near_direct_plus_near"
    assert subtract_mode.combined_values == pytest.approx((10.5, 20.5))

    with pytest.raises(ValueError, match="near_direct_values"):
        compose_far_and_near_potentials(
            far_values=(10.0, 20.0),
            near_evaluation=near_eval,
            far_includes_near=True,
        )


def test_far_near_composition_matches_higher_order_reference_2d() -> None:
    source_cloud = SignedSourceCloudBatch(
        dim=2,
        shape=(2,),
        box_bounds=((0.0, 0.5, 0.0, 0.5), (0.5, 1.0, 0.5, 1.0)),
        statuses=("ok", "ok"),
        errors=(None, None),
        point_ptr=(0, 1, 2),
        points=((0.25, 0.25), (0.75, 0.75)),
        weights=(1.0, 1.0),
        charges=(1.0, -0.4),
        source_box_index=(0, 1),
        backend_mode="folded",
        order=4,
    )

    restricted = build_restricted_sources_from_interaction_lists(
        source_cloud=source_cloud,
        shape=(),
        self_boxes=(0, 1),
        include=("self",),
    )
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=8,
        farfield_potential=lambda x, y: 0.2 + 0.3 * x - 0.1 * y,
    )

    low = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=restricted,
        boundary_trace=trace,
        resolution=3,
        spline_degree=2,
        quadrature_order=5,
        operator_mode="assembled",
    )
    high = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=restricted,
        boundary_trace=trace,
        resolution=6,
        spline_degree=2,
        quadrature_order=8,
        operator_mode="assembled",
    )

    low_solve = solve_local_operator_batch(low)
    high_solve = solve_local_operator_batch(high)

    targets = build_nearfield_target_batch(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        points=((0.2, 0.3), (0.7, 0.6)),
    )
    near_low = evaluate_local_nearfield_targets(
        operators=low,
        solve=low_solve,
        targets=targets,
    )
    near_high = evaluate_local_nearfield_targets(
        operators=high,
        solve=high_solve,
        targets=targets,
    )

    far_values = tuple(0.6 * x + 0.1 * y for x, y in ((0.2, 0.3), (0.7, 0.6)))
    composed_low = compose_far_and_near_potentials(
        far_values=far_values,
        near_evaluation=near_low,
    )
    composed_high = compose_far_and_near_potentials(
        far_values=far_values,
        near_evaluation=near_high,
    )

    assert composed_low.mode == "far_plus_near"
    assert composed_high.mode == "far_plus_near"
    assert composed_low.combined_values == pytest.approx(
        composed_high.combined_values,
        rel=8.0e-2,
        abs=8.0e-2,
    )


def test_local_manufactured_linear_trace_recovery_2d() -> None:
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=5,
        farfield_potential=lambda x, y: 1.0 + 2.0 * x - 3.0 * y,
    )
    sources = RestrictedSourceBatch(
        dim=2,
        shape=trace.shape,
        source_ptr=(0, 0),
        source_points=(),
        source_charges=(),
    )
    operators = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=3,
        spline_degree=2,
        quadrature_order=5,
        operator_mode="assembled",
    )
    solve = solve_local_operator_batch(operators)
    targets = build_nearfield_target_batch(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        points=((0.2, 0.3), (0.8, 0.4)),
    )
    evaluated = evaluate_local_nearfield_targets(
        operators=operators,
        solve=solve,
        targets=targets,
    )

    expected = (1.0 + 2.0 * 0.2 - 3.0 * 0.3, 1.0 + 2.0 * 0.8 - 3.0 * 0.4)
    assert evaluated.values == pytest.approx(expected, rel=5.0e-2, abs=5.0e-2)


def test_local_manufactured_linear_trace_recovery_3d() -> None:
    trace = build_local_box_boundary_trace(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        trace_order=4,
        farfield_potential=lambda x, y, z: 0.5 + x - 2.0 * y + 0.75 * z,
    )
    sources = RestrictedSourceBatch(
        dim=3,
        shape=trace.shape,
        source_ptr=(0, 0),
        source_points=(),
        source_charges=(),
    )
    operators = assemble_local_nearfield_operators(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        restricted_sources=sources,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        operator_mode="assembled",
    )
    solve = solve_local_operator_batch(operators)
    targets = build_nearfield_target_batch(
        dim=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        points=((0.25, 0.25, 0.25), (0.8, 0.2, 0.7)),
    )
    evaluated = evaluate_local_nearfield_targets(
        operators=operators,
        solve=solve,
        targets=targets,
    )

    expected = (
        0.5 + 0.25 - 2.0 * 0.25 + 0.75 * 0.25,
        0.5 + 0.8 - 2.0 * 0.2 + 0.75 * 0.7,
    )
    assert evaluated.values == pytest.approx(expected, rel=1.0e-1, abs=1.0e-1)


def test_compact_support_outside_points_ignored_when_non_strict() -> None:
    trace = build_local_box_boundary_trace(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        trace_order=4,
        farfield_potential=lambda x, y: x - y,
    )
    inside_only = RestrictedSourceBatch(
        dim=2,
        shape=trace.shape,
        source_ptr=(0, 1),
        source_points=((0.5, 0.5),),
        source_charges=(1.0,),
    )
    mixed = RestrictedSourceBatch(
        dim=2,
        shape=trace.shape,
        source_ptr=(0, 2),
        source_points=((0.5, 0.5), (2.0, 2.0)),
        source_charges=(1.0, 3.0),
    )

    ref = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=inside_only,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        strict=True,
    )
    non_strict = assemble_local_nearfield_operators(
        dim=2,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        restricted_sources=mixed,
        boundary_trace=trace,
        resolution=2,
        spline_degree=2,
        quadrature_order=4,
        strict=False,
    )

    assert non_strict.statuses == ("ok",)
    assert non_strict.rhs == pytest.approx(ref.rhs)

    with pytest.raises(ValueError, match="outside local box"):
        assemble_local_nearfield_operators(
            dim=2,
            x0=0.0,
            x1=1.0,
            y0=0.0,
            y1=1.0,
            restricted_sources=mixed,
            boundary_trace=trace,
            resolution=2,
            spline_degree=2,
            quadrature_order=4,
            strict=True,
        )


def test_cad_source_cloud_methods_delegate_to_potentials(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    face = CadFace2D.from_face("face")
    solid = CadSolid3D.from_solid("solid")

    monkeypatch.setattr(
        potentials,
        "source_cloud_over_boxes_2d",
        lambda *args, **kwargs: "face-cloud",
    )
    monkeypatch.setattr(
        potentials,
        "source_cloud_over_boxes_3d",
        lambda *args, **kwargs: "solid-cloud",
    )

    face_result = face.source_cloud_over_boxes(
        density=lambda x, y: x + y,
        order=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
    )
    solid_result = solid.source_cloud_over_boxes(
        density=lambda x, y, z: x + y + z,
        order=3,
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )

    assert face_result == "face-cloud"
    assert solid_result == "solid-cloud"


def test_local_nearfield_solve_batch_validates_shape_lengths() -> None:
    with pytest.raises(ValueError, match="residual_norms"):
        LocalNearfieldSolveBatch(
            dim=3,
            shape=(2,),
            statuses=("ok", "ok"),
            errors=(None, None),
            free_dof_ptr=(0, 1, 2),
            solution=(0.0, 1.0),
            residual_norms=(1.0e-12,),
            iterations=(5, 6),
        )
