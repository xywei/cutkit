"""OpenCascade adapters for CAD-native 2D Section 6 geometries."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from math import sqrt
from typing import Any

from cutkit.geometry import (
    CurveEdge2D,
    CurveLoop2D,
    CurveTrimmedPanel2D,
    curve_loop_signed_area,
)


class OpenCascadeUnavailableError(RuntimeError):
    """Raised when OpenCascade bindings are unavailable."""


@dataclass(frozen=True)
class OpenCascadeStatus:
    """Availability probe for the OpenCascade backend."""

    available: bool
    reason: str | None = None


def _import_module(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - environment specific
        raise OpenCascadeUnavailableError(f"failed to import {name}: {exc}") from exc


@lru_cache(maxsize=1)
def _ocp_modules() -> dict[str, Any]:
    return {
        "gp": _import_module("OCP.gp"),
        "Geom": _import_module("OCP.Geom"),
        "TopoDS": _import_module("OCP.TopoDS"),
        "TopAbs": _import_module("OCP.TopAbs"),
        "TopExp": _import_module("OCP.TopExp"),
        "TColgp": _import_module("OCP.TColgp"),
        "TColStd": _import_module("OCP.TColStd"),
        "BRep": _import_module("OCP.BRep"),
        "BRepTools": _import_module("OCP.BRepTools"),
        "BRepAlgoAPI": _import_module("OCP.BRepAlgoAPI"),
        "BRepAdaptor": _import_module("OCP.BRepAdaptor"),
        "BRepBuilderAPI": _import_module("OCP.BRepBuilderAPI"),
    }


def opencascade_status() -> OpenCascadeStatus:
    try:
        _ocp_modules()
    except OpenCascadeUnavailableError as exc:  # pragma: no cover
        return OpenCascadeStatus(available=False, reason=str(exc))
    return OpenCascadeStatus(available=True, reason=None)


def opencascade_available() -> bool:
    return opencascade_status().available


def _gp_pnt(mods: dict[str, Any], x: float, y: float) -> Any:
    return mods["gp"].gp_Pnt(float(x), float(y), 0.0)


def _topods_cast(mods: dict[str, Any], shape: Any, kind: str) -> Any:
    topo_ds = mods["TopoDS"]
    topo_ds_class = getattr(topo_ds, "TopoDS", None)
    if topo_ds_class is not None:
        caster = getattr(topo_ds_class, f"{kind}_s", None)
        if callable(caster):
            return caster(shape)

    caster = getattr(topo_ds, f"topods_{kind.lower()}", None)
    if callable(caster):
        return caster(shape)

    return shape


def _make_edge_from_points(
    mods: dict[str, Any], p0: tuple[float, float], p1: tuple[float, float]
) -> Any:
    maker = mods["BRepBuilderAPI"].BRepBuilderAPI_MakeEdge(
        _gp_pnt(mods, p0[0], p0[1]),
        _gp_pnt(mods, p1[0], p1[1]),
    )
    return maker.Edge()


def _make_edge_from_curve(mods: dict[str, Any], curve: Any) -> Any:
    maker = mods["BRepBuilderAPI"].BRepBuilderAPI_MakeEdge(curve)
    return maker.Edge()


def _make_wire(mods: dict[str, Any], edges: tuple[Any, ...]) -> Any:
    maker = mods["BRepBuilderAPI"].BRepBuilderAPI_MakeWire()
    for edge in edges:
        maker.Add(edge)
    return maker.Wire()


def _make_face_from_wire(mods: dict[str, Any], wire: Any) -> Any:
    maker = mods["BRepBuilderAPI"].BRepBuilderAPI_MakeFace(wire)
    return maker.Face()


def _make_bspline_curve(
    mods: dict[str, Any],
    *,
    controls: tuple[tuple[float, float], ...],
    degree: int,
    knot_vector: tuple[float, ...],
) -> Any:
    tcolgp = mods["TColgp"]
    tcolstd = mods["TColStd"]
    geom = mods["Geom"]

    poles = tcolgp.TColgp_Array1OfPnt(1, len(controls))
    for idx, (x, y) in enumerate(controls, start=1):
        poles.SetValue(idx, _gp_pnt(mods, x, y))

    distinct_knots: list[float] = []
    multiplicities: list[int] = []
    for knot in knot_vector:
        if not distinct_knots or abs(knot - distinct_knots[-1]) > 1.0e-14:
            distinct_knots.append(float(knot))
            multiplicities.append(1)
        else:
            multiplicities[-1] += 1

    knots = tcolstd.TColStd_Array1OfReal(1, len(distinct_knots))
    mults = tcolstd.TColStd_Array1OfInteger(1, len(multiplicities))
    for idx, knot in enumerate(distinct_knots, start=1):
        knots.SetValue(idx, knot)
    for idx, mult in enumerate(multiplicities, start=1):
        mults.SetValue(idx, int(mult))

    return geom.Geom_BSplineCurve(poles, knots, mults, int(degree))


def _make_rational_bezier_curve(
    mods: dict[str, Any],
    *,
    controls: tuple[tuple[float, float], ...],
    weights: tuple[float, ...],
) -> Any:
    tcolgp = mods["TColgp"]
    tcolstd = mods["TColStd"]
    geom = mods["Geom"]

    poles = tcolgp.TColgp_Array1OfPnt(1, len(controls))
    wgts = tcolstd.TColStd_Array1OfReal(1, len(weights))
    for idx, (x, y) in enumerate(controls, start=1):
        poles.SetValue(idx, _gp_pnt(mods, x, y))
    for idx, weight in enumerate(weights, start=1):
        wgts.SetValue(idx, float(weight))

    return geom.Geom_BezierCurve(poles, wgts)


def build_section_6_1_1_face() -> Any:
    """Build exact CAD face for Antolin-Wei-Buffa (2022) Section 6.1.1."""

    mods = _ocp_modules()
    controls = (
        (0.0, 0.25),
        (0.25, 0.0),
        (0.5, 0.5),
        (0.9, 0.25),
        (0.8, 0.125),
        (0.75, 0.0),
    )
    knot_vector = (0.0, 0.0, 0.0, 0.25, 0.5, 0.75, 1.0, 1.0, 1.0)
    curve = _make_bspline_curve(
        mods,
        controls=controls,
        degree=2,
        knot_vector=knot_vector,
    )

    curved_edge = _make_edge_from_curve(mods, curve)
    edges = (
        curved_edge,
        _make_edge_from_points(mods, (0.75, 0.0), (1.0, 0.0)),
        _make_edge_from_points(mods, (1.0, 0.0), (1.0, 1.0)),
        _make_edge_from_points(mods, (1.0, 1.0), (0.0, 1.0)),
        _make_edge_from_points(mods, (0.0, 1.0), (0.0, 0.25)),
    )

    return _make_face_from_wire(mods, _make_wire(mods, edges))


def build_section_6_1_2_face() -> Any:
    """Build exact CAD face for Antolin-Wei-Buffa (2022) Section 6.1.2."""

    mods = _ocp_modules()
    controls = ((0.0, 0.5), (0.0, 0.0), (0.5, 0.0))
    weights = (1.0, 1.0 / sqrt(2.0), 1.0)
    curve = _make_rational_bezier_curve(mods, controls=controls, weights=weights)

    curved_edge = _make_edge_from_curve(mods, curve)
    edges = (
        curved_edge,
        _make_edge_from_points(mods, (0.5, 0.0), (1.0, 0.0)),
        _make_edge_from_points(mods, (1.0, 0.0), (1.0, 1.0)),
        _make_edge_from_points(mods, (1.0, 1.0), (0.0, 1.0)),
        _make_edge_from_points(mods, (0.0, 1.0), (0.0, 0.5)),
    )

    return _make_face_from_wire(mods, _make_wire(mods, edges))


def build_rectangle_face(
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> Any:
    """Build a rectangular CAD face in the xy-plane."""

    mods = _ocp_modules()
    edges = (
        _make_edge_from_points(mods, (x0, y0), (x1, y0)),
        _make_edge_from_points(mods, (x1, y0), (x1, y1)),
        _make_edge_from_points(mods, (x1, y1), (x0, y1)),
        _make_edge_from_points(mods, (x0, y1), (x0, y0)),
    )
    return _make_face_from_wire(mods, _make_wire(mods, edges))


def _shape_faces(shape: Any, mods: dict[str, Any]) -> tuple[Any, ...]:
    faces: list[Any] = []
    explorer = mods["TopExp"].TopExp_Explorer(shape, mods["TopAbs"].TopAbs_FACE)
    while explorer.More():
        faces.append(_topods_cast(mods, explorer.Current(), "Face"))
        explorer.Next()
    return tuple(faces)


def _wire_edges(wire: Any, face: Any, mods: dict[str, Any]) -> tuple[Any, ...]:
    edges: list[Any] = []
    btools = mods["BRepTools"].BRepTools_WireExplorer
    try:
        explorer = btools(wire, face)
    except TypeError:
        explorer = btools(wire)

    while explorer.More():
        edges.append(_topods_cast(mods, explorer.Current(), "Edge"))
        explorer.Next()

    if edges:
        return tuple(edges)

    fallback = mods["TopExp"].TopExp_Explorer(wire, mods["TopAbs"].TopAbs_EDGE)
    while fallback.More():
        edges.append(_topods_cast(mods, fallback.Current(), "Edge"))
        fallback.Next()
    return tuple(edges)


def _edge_curve(edge: Any, mods: dict[str, Any]) -> CurveEdge2D:
    adaptor = mods["BRepAdaptor"].BRepAdaptor_Curve(edge)
    u0 = float(adaptor.FirstParameter())
    u1 = float(adaptor.LastParameter())
    du = u1 - u0

    is_reversed = False
    if hasattr(edge, "Orientation"):
        reversed_flag = getattr(mods["TopAbs"], "TopAbs_REVERSED", None)
        is_reversed = reversed_flag is not None and edge.Orientation() == reversed_flag

    def map_param(s: float) -> float:
        s = float(s)
        if s <= 0.0:
            s = 0.0
        elif s >= 1.0:
            s = 1.0
        if is_reversed:
            return u1 - s * du
        return u0 + s * du

    def value_from_s(s: float) -> tuple[float, float]:
        param = map_param(s)
        point = adaptor.Value(param)
        return (float(point.X()), float(point.Y()))

    def deriv_from_s(s: float) -> tuple[float, float]:
        eps = 1.0e-6
        s0 = s - eps
        s1 = s + eps
        if s0 < 0.0:
            s0 = 0.0
        if s1 > 1.0:
            s1 = 1.0
        if s1 - s0 <= 1.0e-14:
            if s <= 0.5:
                s0 = s
                s1 = min(1.0, s + 1.0e-4)
            else:
                s0 = max(0.0, s - 1.0e-4)
                s1 = s

        p0 = value_from_s(s0)
        p1 = value_from_s(s1)
        inv = 1.0 / (s1 - s0)
        return ((p1[0] - p0[0]) * inv, (p1[1] - p0[1]) * inv)

    return CurveEdge2D(evaluator=value_from_s, derivative=deriv_from_s)


def face_to_curve_panel(face: Any) -> CurveTrimmedPanel2D:
    """Convert one OpenCascade face to curve-loop outer + holes."""

    mods = _ocp_modules()
    face = _topods_cast(mods, face, "Face")

    loops: list[CurveLoop2D] = []
    explorer = mods["TopExp"].TopExp_Explorer(face, mods["TopAbs"].TopAbs_WIRE)
    while explorer.More():
        wire = _topods_cast(mods, explorer.Current(), "Wire")
        edges = tuple(_edge_curve(edge, mods) for edge in _wire_edges(wire, face, mods))
        if edges:
            loops.append(CurveLoop2D(edges=edges))
        explorer.Next()

    if not loops:
        raise ValueError("face has no boundary wires")

    areas = tuple(curve_loop_signed_area(loop) for loop in loops)
    outer_index = max(range(len(loops)), key=lambda idx: abs(areas[idx]))
    outer = loops[outer_index]
    holes = tuple(loop for idx, loop in enumerate(loops) if idx != outer_index)
    return CurveTrimmedPanel2D(outer=outer, holes=holes)


def intersect_face_with_rectangle(
    face: Any,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
) -> tuple[CurveTrimmedPanel2D, ...]:
    """Clip one CAD face with one rectangle and return resulting panels."""

    mods = _ocp_modules()
    cell_face = build_rectangle_face(x0=x0, x1=x1, y0=y0, y1=y1)
    op = mods["BRepAlgoAPI"].BRepAlgoAPI_Common(face, cell_face)
    if hasattr(op, "Build"):
        op.Build()
    shape = op.Shape()

    return tuple(face_to_curve_panel(item) for item in _shape_faces(shape, mods))
