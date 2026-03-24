"""OpenCascade adapters for CAD-native 3D solid ingestion and clipping."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from typing import Any

from cutkit.geometry import BoundaryTriangulation3D, Point3D, Triangle3D
from cutkit.topology import orient_boundary_triangles_outward


class OpenCascade3DUnavailableError(RuntimeError):
    """Raised when OpenCascade 3D bindings are unavailable."""


@dataclass(frozen=True)
class OpenCascade3DStatus:
    """Availability probe for the OpenCascade 3D backend."""

    available: bool
    reason: str | None = None


def _import_module(name: str) -> Any:
    try:
        return importlib.import_module(name)
    except Exception as exc:  # pragma: no cover - environment specific
        raise OpenCascade3DUnavailableError(f"failed to import {name}: {exc}") from exc


@lru_cache(maxsize=1)
def _ocp_modules_3d() -> dict[str, Any]:
    return {
        "gp": _import_module("OCP.gp"),
        "TopAbs": _import_module("OCP.TopAbs"),
        "TopExp": _import_module("OCP.TopExp"),
        "TopoDS": _import_module("OCP.TopoDS"),
        "TopLoc": _import_module("OCP.TopLoc"),
        "BRep": _import_module("OCP.BRep"),
        "BRepAlgoAPI": _import_module("OCP.BRepAlgoAPI"),
        "BRepMesh": _import_module("OCP.BRepMesh"),
        "BRepPrimAPI": _import_module("OCP.BRepPrimAPI"),
    }


def opencascade3d_status() -> OpenCascade3DStatus:
    try:
        _ocp_modules_3d()
    except OpenCascade3DUnavailableError as exc:  # pragma: no cover
        return OpenCascade3DStatus(available=False, reason=str(exc))
    return OpenCascade3DStatus(available=True, reason=None)


def opencascade3d_available() -> bool:
    return opencascade3d_status().available


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


def _shape_faces(shape: Any, mods: dict[str, Any]) -> tuple[Any, ...]:
    faces: list[Any] = []
    explorer = mods["TopExp"].TopExp_Explorer(shape, mods["TopAbs"].TopAbs_FACE)
    while explorer.More():
        faces.append(_topods_cast(mods, explorer.Current(), "Face"))
        explorer.Next()
    return tuple(faces)


def _run_incremental_mesh(
    shape: Any,
    *,
    linear_deflection: float,
    angular_deflection: float,
    mods: dict[str, Any],
) -> None:
    if linear_deflection <= 0.0:
        raise ValueError("linear_deflection must be positive")
    if angular_deflection <= 0.0:
        raise ValueError("angular_deflection must be positive")

    mesh_cls = mods["BRepMesh"].BRepMesh_IncrementalMesh
    mesher: Any
    try:
        mesher = mesh_cls(
            shape,
            float(linear_deflection),
            False,
            float(angular_deflection),
            True,
        )
    except TypeError:
        try:
            mesher = mesh_cls(
                shape,
                float(linear_deflection),
                False,
                float(angular_deflection),
            )
        except TypeError:
            mesher = mesh_cls(shape, float(linear_deflection))

    perform = getattr(mesher, "Perform", None)
    if callable(perform):
        perform()


def _triangulation_for_face(face: Any, mods: dict[str, Any]) -> tuple[Any, Any] | None:
    location = mods["TopLoc"].TopLoc_Location()
    brep_tool = mods["BRep"].BRep_Tool

    triangulation: Any
    getter = getattr(brep_tool, "Triangulation_s", None)
    if callable(getter):
        triangulation = getter(face, location)
    else:
        getter = getattr(brep_tool, "Triangulation", None)
        if not callable(getter):
            raise RuntimeError("OpenCascade BRep_Tool triangulation API unavailable")
        triangulation = getter(face, location)

    if triangulation is None:
        return None
    is_null = getattr(triangulation, "IsNull", None)
    if callable(is_null) and is_null():
        return None
    return triangulation, location


def _node_point(
    triangulation: Any,
    index: int,
    *,
    location: Any,
) -> Point3D:
    node_getter = getattr(triangulation, "Node", None)
    point: Any
    if callable(node_getter):
        point = node_getter(index)
    else:
        nodes_getter = getattr(triangulation, "Nodes", None)
        if not callable(nodes_getter):
            raise RuntimeError("OpenCascade triangulation nodes API unavailable")
        nodes = nodes_getter()
        value = getattr(nodes, "Value", None)
        if not callable(value):
            raise RuntimeError("OpenCascade triangulation nodes.Value API unavailable")
        point = value(index)

    transform_getter = getattr(location, "Transformation", None)
    transformed = getattr(point, "Transformed", None)
    if callable(transform_getter) and callable(transformed):
        point = transformed(transform_getter())

    return (float(point.X()), float(point.Y()), float(point.Z()))


def _triangle_indices(poly_triangle: Any) -> tuple[int, int, int]:
    get_method = getattr(poly_triangle, "Get", None)
    if callable(get_method):
        try:
            result = get_method()
            if isinstance(result, tuple) and len(result) == 3:
                return (int(result[0]), int(result[1]), int(result[2]))
        except TypeError:
            pass

    value_method = getattr(poly_triangle, "Value", None)
    if callable(value_method):
        return (int(value_method(1)), int(value_method(2)), int(value_method(3)))

    n_values: list[int] = []
    for name in ("N1", "N2", "N3"):
        getter = getattr(poly_triangle, name, None)
        if callable(getter):
            n_values.append(int(getter()))
    if len(n_values) == 3:
        return (n_values[0], n_values[1], n_values[2])

    raise RuntimeError("OpenCascade triangle index API unavailable")


def solid_to_boundary_triangles(
    solid: Any,
    *,
    linear_deflection: float = 1.0e-3,
    angular_deflection: float = 0.5,
) -> tuple[Triangle3D, ...]:
    """Extract triangulated boundary triangles from a CAD solid shape."""

    mods = _ocp_modules_3d()
    _run_incremental_mesh(
        solid,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
        mods=mods,
    )

    reversed_flag = getattr(mods["TopAbs"], "TopAbs_REVERSED", None)
    triangles: list[Triangle3D] = []

    for face in _shape_faces(solid, mods):
        tri_info = _triangulation_for_face(face, mods)
        if tri_info is None:
            continue
        triangulation, location = tri_info

        is_face_reversed = (
            reversed_flag is not None
            and hasattr(face, "Orientation")
            and face.Orientation() == reversed_flag
        )

        nb_triangles = int(triangulation.NbTriangles())
        for tri_index in range(1, nb_triangles + 1):
            poly_triangle = triangulation.Triangle(tri_index)
            i0, i1, i2 = _triangle_indices(poly_triangle)
            p0 = _node_point(triangulation, i0, location=location)
            p1 = _node_point(triangulation, i1, location=location)
            p2 = _node_point(triangulation, i2, location=location)
            if is_face_reversed:
                triangles.append((p0, p2, p1))
            else:
                triangles.append((p0, p1, p2))

    if not triangles:
        raise ValueError("solid triangulation produced no boundary triangles")
    return tuple(triangles)


def solid_to_oriented_boundary_triangles(
    solid: Any,
    *,
    linear_deflection: float = 1.0e-3,
    angular_deflection: float = 0.5,
    tol: float = 1.0e-12,
) -> tuple[Triangle3D, ...]:
    """Extract and orient CAD solid boundary triangles for folded 3D workflows."""

    raw = solid_to_boundary_triangles(
        solid,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
    )
    return orient_boundary_triangles_outward(raw, tol=tol, validate_closed=True)


def solid_to_boundary_triangulation(
    solid: Any,
    *,
    linear_deflection: float = 1.0e-3,
    angular_deflection: float = 0.5,
    tol: float = 1.0e-12,
) -> BoundaryTriangulation3D:
    """Extract an oriented boundary triangulation dataclass from a CAD solid."""

    return BoundaryTriangulation3D(
        triangles=solid_to_oriented_boundary_triangles(
            solid,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
        )
    )


def build_axis_aligned_box_solid(
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
) -> Any:
    """Build an axis-aligned CAD solid box."""

    if x1 <= x0 or y1 <= y0 or z1 <= z0:
        raise ValueError("box bounds must satisfy x1>x0, y1>y0, z1>z0")

    mods = _ocp_modules_3d()
    gp = mods["gp"]
    maker = mods["BRepPrimAPI"].BRepPrimAPI_MakeBox(
        gp.gp_Pnt(float(x0), float(y0), float(z0)),
        gp.gp_Pnt(float(x1), float(y1), float(z1)),
    )
    solid = maker.Solid() if hasattr(maker, "Solid") else maker.Shape()
    return _topods_cast(mods, solid, "Solid")


def clip_solid_with_axis_aligned_box(
    solid: Any,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
) -> Any:
    """Clip a CAD solid against an axis-aligned CAD box using boolean common."""

    mods = _ocp_modules_3d()
    clip_box = build_axis_aligned_box_solid(
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        z0=z0,
        z1=z1,
    )
    operation = mods["BRepAlgoAPI"].BRepAlgoAPI_Common(solid, clip_box)
    if hasattr(operation, "Build"):
        operation.Build()
    return operation.Shape()


def clip_solid_with_axis_aligned_box_to_oriented_boundary(
    solid: Any,
    *,
    x0: float,
    x1: float,
    y0: float,
    y1: float,
    z0: float,
    z1: float,
    linear_deflection: float = 1.0e-3,
    angular_deflection: float = 0.5,
    tol: float = 1.0e-12,
) -> tuple[Triangle3D, ...]:
    """Clip a CAD solid and return oriented boundary triangles of the result."""

    clipped = clip_solid_with_axis_aligned_box(
        solid,
        x0=x0,
        x1=x1,
        y0=y0,
        y1=y1,
        z0=z0,
        z1=z1,
    )
    return solid_to_oriented_boundary_triangles(
        clipped,
        linear_deflection=linear_deflection,
        angular_deflection=angular_deflection,
        tol=tol,
    )
