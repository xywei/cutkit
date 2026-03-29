from __future__ import annotations

from types import SimpleNamespace

import pytest

import cutkit.io.opencascade3d as oc3d
from cutkit.io import (
    build_axis_aligned_box_solid,
    clip_solid_with_axis_aligned_box,
    integrate_general_over_solid_folded_3d,
    opencascade3d_available,
    opencascade3d_status,
    solid_has_boundary_faces_3d,
    solid_to_folded_quadrature_rule_3d,
    solid_to_surface_quadrature_3d,
)


def test_opencascade3d_status_shape() -> None:
    status = opencascade3d_status()
    assert isinstance(status.available, bool)
    if status.available:
        assert status.reason is None
    else:
        assert status.reason


def test_opencascade3d_surface_and_folded_rules_or_unavailable_error() -> None:
    if not opencascade3d_available():
        with pytest.raises(RuntimeError):
            solid_to_surface_quadrature_3d(object(), order=3)
        return

    solid = build_axis_aligned_box_solid(
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )
    surface_rule = solid_to_surface_quadrature_3d(solid, order=4)
    assert surface_rule.points
    assert surface_rule.weighted_normals

    folded = solid_to_folded_quadrature_rule_3d(
        solid,
        seed=(0.25, 0.25, 0.25),
        order=6,
        surface_order=6,
    )
    assert folded.rule.points
    volume_from_weights = sum(folded.rule.weights)
    assert volume_from_weights == pytest.approx(1.0, rel=5.0e-2, abs=5.0e-2)


def test_opencascade3d_clip_half_box_volume_or_unavailable_error() -> None:
    if not opencascade3d_available():
        with pytest.raises(RuntimeError):
            integrate_general_over_solid_folded_3d(
                object(),
                seed=(0.1, 0.1, 0.1),
                order=4,
                integrand=lambda x, y, z: x + y + z,
            )
        return

    solid = build_axis_aligned_box_solid(
        x0=0.0,
        x1=1.0,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )
    clipped = clip_solid_with_axis_aligned_box(
        solid,
        x0=0.0,
        x1=0.5,
        y0=0.0,
        y1=1.0,
        z0=0.0,
        z1=1.0,
    )
    volume = integrate_general_over_solid_folded_3d(
        clipped,
        seed=(0.1, 0.1, 0.1),
        order=6,
        surface_order=6,
        integrand=lambda x, y, z: 1.0,
    )
    assert volume == pytest.approx(0.5, rel=7.0e-2, abs=7.0e-2)


def test_solid_has_boundary_faces_uses_topology_not_surface_quadrature(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        oc3d,
        "solid_to_surface_quadrature_3d",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("surface quadrature should not be called")
        ),
    )
    monkeypatch.setattr(oc3d, "_ocp_modules_3d", lambda: {"dummy": object()})
    monkeypatch.setattr(oc3d, "_shape_has_volume_topology", lambda solid, *, mods: True)
    monkeypatch.setattr(
        oc3d,
        "_solid_has_non_null_faces",
        lambda solid, *, mods: bool(solid == "solid" and mods),
    )

    assert solid_has_boundary_faces_3d("solid")


def test_solid_has_boundary_faces_rejects_non_volumetric_topology(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(oc3d, "_ocp_modules_3d", lambda: {"dummy": object()})
    monkeypatch.setattr(
        oc3d, "_shape_has_volume_topology", lambda solid, *, mods: False
    )
    monkeypatch.setattr(oc3d, "_solid_has_non_null_faces", lambda solid, *, mods: True)

    assert not solid_has_boundary_faces_3d("surface-only")


def test_face_classifier_fails_fast_when_classifier_unavailable() -> None:
    with pytest.raises(RuntimeError, match="trimmed-face classifier API unavailable"):
        oc3d._face_classifier(
            object(),
            tol=1.0e-12,
            mods={"BRepTopAdaptor": object()},
        )


def test_classify_uv_inside_fails_fast_when_gp_point2d_unavailable() -> None:
    classifier = SimpleNamespace(Perform=lambda point: point)
    with pytest.raises(RuntimeError, match="gp_Pnt2d API unavailable"):
        oc3d._classify_uv_inside(
            classifier,
            u=0.25,
            v=0.75,
            mods={"TopAbs": object()},
        )
