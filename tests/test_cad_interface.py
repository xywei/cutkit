from __future__ import annotations

from typing import Any

import pytest

import cutkit.cad as cad
from cutkit.cad import Box2D, Box2DArray, Box3D, CadFace2D, CadSession, CadSolid3D
from cutkit.io import OpenCascade3DStatus, OpenCascadeStatus


def test_clip_boxes_2d_array_mode_broadcasts_scalars(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    face = CadFace2D.from_face("face")
    seen: list[tuple[float, float, float, float]] = []

    def fake_intersect(
        _face: object,
        *,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> tuple[Any, ...]:
        seen.append((x0, x1, y0, y1))
        return ((x0, x1, y0, y1),)

    monkeypatch.setattr(cad, "intersect_face_with_rectangle", fake_intersect)

    result = face.clip_boxes(
        x0=(0.0, 0.5),
        x1=(0.25, 0.75),
        y0=0.0,
        y1=1.0,
    )

    assert result.shape == (2,)
    assert result.statuses == ("ok", "ok")
    assert seen == [(0.0, 0.25, 0.0, 1.0), (0.5, 0.75, 0.0, 1.0)]


def test_clip_boxes_2d_non_strict_marks_invalid_boxes(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    face = CadFace2D.from_face("face")
    call_count = 0

    def fake_intersect(
        _face: object,
        *,
        x0: float,
        x1: float,
        y0: float,
        y1: float,
    ) -> tuple[Any, ...]:
        nonlocal call_count
        call_count += 1
        return ((x0, x1, y0, y1),)

    monkeypatch.setattr(cad, "intersect_face_with_rectangle", fake_intersect)

    result = face.clip_boxes(
        x0=(0.0, 1.0),
        x1=(0.5, 0.5),
        y0=(0.0, 0.0),
        y1=(1.0, 1.0),
        strict=False,
    )

    assert result.statuses == ("ok", "invalid_box")
    assert result.errors[0] is None
    assert result.errors[1] and "x1>x0" in result.errors[1]
    assert call_count == 1


def test_clip_boxes_2d_strict_raises_on_invalid_box(
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
        return ((x0, x1, y0, y1),)

    monkeypatch.setattr(cad, "intersect_face_with_rectangle", fake_intersect)

    with pytest.raises(ValueError, match="x1>x0"):
        face.clip_boxes(
            x0=(0.0, 1.0),
            x1=(0.5, 0.5),
            y0=(0.0, 0.0),
            y1=(1.0, 1.0),
            strict=True,
        )


def test_integrate_over_boxes_2d_object_and_array_modes_match(
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
        return ((x0, x1, y0, y1),)

    def fake_integrate_panel(
        panel: Any,
        *,
        integrand: Any,
        order: int,
        anchor: Any,
        require_interior_anchor: bool,
        anchor_sample_points: int,
    ) -> float:
        x0, x1, y0, y1 = panel
        _ = (integrand, order, anchor, require_interior_anchor, anchor_sample_points)
        return (x1 - x0) + (y1 - y0)

    monkeypatch.setattr(cad, "intersect_face_with_rectangle", fake_intersect)
    monkeypatch.setattr(cad, "_integrate_curve_panel", fake_integrate_panel)

    object_mode = face.integrate_over_boxes(
        lambda x, y: x + y,
        order=4,
        boxes=(
            Box2D(x0=0.0, x1=0.5, y0=0.0, y1=1.0),
            Box2D(x0=0.5, x1=1.0, y0=0.0, y1=1.0),
        ),
    )
    array_mode = face.integrate_over_boxes(
        lambda x, y: x + y,
        order=4,
        boxes=Box2DArray(x0=(0.0, 0.5), x1=(0.5, 1.0), y0=0.0, y1=1.0),
    )

    assert object_mode.statuses == ("ok", "ok")
    assert array_mode.statuses == ("ok", "ok")
    assert object_mode.values == array_mode.values


def test_integrate_over_boxes_3d_non_strict_marks_backend_errors(
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
        if x0 > 0.5:
            raise RuntimeError("simulated clipping failure")
        return {"bounds": (x0, x1, y0, y1, z0, z1)}

    def fake_boundary(
        clipped: Any,
        *,
        linear_deflection: float,
        angular_deflection: float,
        tol: float,
    ) -> tuple[
        tuple[
            tuple[float, float, float],
            tuple[float, float, float],
            tuple[float, float, float],
        ],
        ...,
    ]:
        _ = (linear_deflection, angular_deflection, tol)
        x0, _x1, y0, _y1, z0, _z1 = clipped["bounds"]
        return (((x0, y0, z0), (x0 + 0.1, y0, z0), (x0, y0 + 0.1, z0)),)

    def fake_integrate(
        boundary: tuple[
            tuple[
                tuple[float, float, float],
                tuple[float, float, float],
                tuple[float, float, float],
            ],
            ...,
        ],
        *,
        seed: tuple[float, float, float],
        order: int,
        integrand: Any,
    ) -> float:
        _ = (seed, order, integrand)
        return boundary[0][0][0]

    monkeypatch.setattr(cad, "clip_solid_with_axis_aligned_box", fake_clip)
    monkeypatch.setattr(cad, "solid_to_oriented_boundary_triangles", fake_boundary)
    monkeypatch.setattr(cad, "integrate_general_over_boundary_3d", fake_integrate)

    result = solid.integrate_over_boxes(
        lambda x, y, z: x + y + z,
        order=4,
        x0=(0.0, 0.6),
        x1=(0.4, 1.0),
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        strict=False,
    )

    assert result.statuses == ("ok", "backend_error")
    assert result.values[0] == pytest.approx(0.0)
    assert result.values[1] is None
    assert result.errors[1] and "simulated clipping failure" in result.errors[1]


def test_clip_boxes_3d_marks_empty_when_shape_is_null(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    solid = CadSolid3D.from_solid("solid")

    class NullShape:
        def IsNull(self) -> bool:  # noqa: N802 - OCC-style API
            return True

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
        _ = (x1, y0, y1, z0, z1)
        if x0 < 0.5:
            return {"non_null": True}
        return NullShape()

    monkeypatch.setattr(cad, "clip_solid_with_axis_aligned_box", fake_clip)

    result = solid.clip_boxes(
        x0=(0.0, 0.5),
        x1=(0.4, 0.9),
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
        strict=True,
    )

    assert result.statuses == ("ok", "empty")
    assert result.solids[0] is not None
    assert result.solids[1] is None


def test_integrate_over_boxes_3d_object_and_array_modes_match(
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
        clipped: Any,
        *,
        linear_deflection: float,
        angular_deflection: float,
        tol: float,
    ) -> tuple[
        tuple[
            tuple[float, float, float],
            tuple[float, float, float],
            tuple[float, float, float],
        ],
        ...,
    ]:
        _ = (linear_deflection, angular_deflection, tol)
        x0, _x1, y0, _y1, z0, _z1 = clipped["bounds"]
        return (((x0, y0, z0), (x0 + 0.1, y0, z0), (x0, y0 + 0.1, z0)),)

    def fake_integrate(
        boundary: tuple[
            tuple[
                tuple[float, float, float],
                tuple[float, float, float],
                tuple[float, float, float],
            ],
            ...,
        ],
        *,
        seed: tuple[float, float, float],
        order: int,
        integrand: Any,
    ) -> float:
        _ = (seed, order, integrand)
        return boundary[0][0][0]

    monkeypatch.setattr(cad, "clip_solid_with_axis_aligned_box", fake_clip)
    monkeypatch.setattr(cad, "solid_to_oriented_boundary_triangles", fake_boundary)
    monkeypatch.setattr(cad, "integrate_general_over_boundary_3d", fake_integrate)

    object_mode = solid.integrate_over_boxes(
        lambda x, y, z: x + y + z,
        order=5,
        boxes=(
            Box3D(x0=0.0, x1=0.4, y0=0.0, y1=1.0, z0=0.0, z1=1.0),
            Box3D(x0=0.4, x1=0.8, y0=0.0, y1=1.0, z0=0.0, z1=1.0),
        ),
    )
    array_mode = solid.integrate_over_boxes(
        lambda x, y, z: x + y + z,
        order=5,
        x0=(0.0, 0.4),
        x1=(0.4, 0.8),
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )

    assert object_mode.statuses == ("ok", "ok")
    assert array_mode.statuses == ("ok", "ok")
    assert object_mode.values == array_mode.values


def test_cad_session_load_requires_available_backend(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    session = CadSession.opencascade()

    monkeypatch.setattr(
        cad,
        "opencascade_status",
        lambda: OpenCascadeStatus(available=False, reason="2d missing"),
    )
    monkeypatch.setattr(
        cad,
        "opencascade3d_status",
        lambda: OpenCascade3DStatus(available=False, reason="3d missing"),
    )

    with pytest.raises(RuntimeError, match="2d missing"):
        session.load_face("dummy.brep")
    with pytest.raises(RuntimeError, match="3d missing"):
        session.load_solid("dummy.brep")


def test_clip_boxes_rejects_mixed_object_and_array_inputs() -> None:
    face = CadFace2D.from_face("face")
    with pytest.raises(ValueError, match="either boxes=... or coordinate arrays"):
        face.clip_boxes(
            boxes=Box2D(x0=0.0, x1=0.5, y0=0.0, y1=1.0),
            x0=0.0,
            x1=0.5,
            y0=0.0,
            y1=1.0,
        )
