from __future__ import annotations

from pathlib import Path

import pytest

from cutkit.io import opencascade2d as oc2d
from cutkit.io import opencascade3d as oc3d


def test_load_brep_shape_2d_delegates_to_reader(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    mods = object()
    monkeypatch.setattr(oc2d, "_ocp_modules", lambda: mods)

    captured: dict[str, object] = {}

    def fake_reader(reader_mods: object, brep_path: Path) -> str:
        captured["mods"] = reader_mods
        captured["path"] = brep_path
        return "shape2d"

    monkeypatch.setattr(oc2d, "_read_shape_from_brep", fake_reader)

    shape = oc2d.load_brep_shape_2d("/tmp/panel.brep")

    assert shape == "shape2d"
    assert captured["mods"] is mods
    assert captured["path"] == Path("/tmp/panel.brep")


def test_load_brep_face_requires_single_face(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc2d, "_ocp_modules", lambda: {"dummy": object()})
    monkeypatch.setattr(oc2d, "_read_shape_from_brep", lambda _mods, _path: "shape")
    monkeypatch.setattr(oc2d, "_shape_faces", lambda _shape, _mods: ("f0", "f1"))

    with pytest.raises(ValueError, match="exactly one face"):
        oc2d.load_brep_face("/tmp/panel.brep")


def test_load_brep_panel_converts_face(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc2d, "load_brep_face", lambda _path: "face")
    monkeypatch.setattr(oc2d, "face_to_curve_panel", lambda face: f"panel:{face}")

    assert oc2d.load_brep_panel("/tmp/panel.brep") == "panel:face"


def test_load_brep_panels_requires_faces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc2d, "_ocp_modules", lambda: {"dummy": object()})
    monkeypatch.setattr(oc2d, "_read_shape_from_brep", lambda _mods, _path: "shape")
    monkeypatch.setattr(oc2d, "_shape_faces", lambda _shape, _mods: ())

    with pytest.raises(ValueError, match="no faces"):
        oc2d.load_brep_panels("/tmp/panel.brep")


def test_load_brep_panels_converts_all_faces(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc2d, "_ocp_modules", lambda: {"dummy": object()})
    monkeypatch.setattr(oc2d, "_read_shape_from_brep", lambda _mods, _path: "shape")
    monkeypatch.setattr(oc2d, "_shape_faces", lambda _shape, _mods: ("f0", "f1"))
    monkeypatch.setattr(oc2d, "face_to_curve_panel", lambda face: f"panel:{face}")

    assert oc2d.load_brep_panels("/tmp/panel.brep") == ("panel:f0", "panel:f1")


def test_write_brep_shape_2d_returns_path(monkeypatch: pytest.MonkeyPatch) -> None:
    mods = object()
    monkeypatch.setattr(oc2d, "_ocp_modules", lambda: mods)

    captured: dict[str, object] = {}

    def fake_writer(writer_mods: object, shape: object, brep_path: Path) -> None:
        captured["mods"] = writer_mods
        captured["shape"] = shape
        captured["path"] = brep_path

    monkeypatch.setattr(oc2d, "_write_shape_to_brep", fake_writer)

    out_path = oc2d.write_brep_shape_2d("shape", brep_path="/tmp/out2d.brep")

    assert out_path == Path("/tmp/out2d.brep")
    assert captured["mods"] is mods
    assert captured["shape"] == "shape"
    assert captured["path"] == Path("/tmp/out2d.brep")


def test_load_brep_solids_requires_nonempty(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc3d, "_ocp_modules_3d", lambda: {"dummy": object()})
    monkeypatch.setattr(oc3d, "_read_shape_from_brep", lambda _mods, _path: "shape")
    monkeypatch.setattr(oc3d, "_shape_solids", lambda _shape, _mods: ())

    with pytest.raises(ValueError, match="no solids"):
        oc3d.load_brep_solids("/tmp/solid.brep")


def test_load_brep_solid_requires_single_solid(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(oc3d, "load_brep_solids", lambda _path: ("s0", "s1"))

    with pytest.raises(ValueError, match="exactly one solid"):
        oc3d.load_brep_solid("/tmp/solid.brep")


def test_write_brep_shape_3d_returns_path(monkeypatch: pytest.MonkeyPatch) -> None:
    mods = object()
    monkeypatch.setattr(oc3d, "_ocp_modules_3d", lambda: mods)

    captured: dict[str, object] = {}

    def fake_writer(writer_mods: object, shape: object, brep_path: Path) -> None:
        captured["mods"] = writer_mods
        captured["shape"] = shape
        captured["path"] = brep_path

    monkeypatch.setattr(oc3d, "_write_shape_to_brep", fake_writer)

    out_path = oc3d.write_brep_shape_3d("shape", brep_path="/tmp/out3d.brep")

    assert out_path == Path("/tmp/out3d.brep")
    assert captured["mods"] is mods
    assert captured["shape"] == "shape"
    assert captured["path"] == Path("/tmp/out3d.brep")
