"""OpenCascade adapters for CAD-native 3D solid ingestion and clipping."""

from __future__ import annotations

import importlib
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal

from cutkit.geometry import Point3D
from cutkit.quadrature.folded2d import gauss_legendre_01
from cutkit.quadrature.rule3d import QuadratureRule3D


class OpenCascade3DUnavailableError(RuntimeError):
    """Raised when OpenCascade 3D bindings are unavailable."""


@dataclass(frozen=True)
class OpenCascade3DStatus:
    """Availability probe for the OpenCascade 3D backend."""

    available: bool
    reason: str | None = None


SeedMode3D = Literal["jplus", "centroid", "grid-best"]
SeedInput3D = Point3D | SeedMode3D


@dataclass(frozen=True)
class SurfaceQuadratureRule3D:
    """Deterministic oriented surface quadrature over a clipped solid boundary."""

    points: tuple[Point3D, ...]
    weighted_normals: tuple[Point3D, ...]


@dataclass(frozen=True)
class FoldedSolidQuadrature3D:
    """Seed-resolved folded quadrature rule over one clipped solid."""

    seed: Point3D
    rule: QuadratureRule3D


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
        "BRep": _import_module("OCP.BRep"),
        "BRepAdaptor": _import_module("OCP.BRepAdaptor"),
        "BRepTools": _import_module("OCP.BRepTools"),
        "BRepTopAdaptor": _import_module("OCP.BRepTopAdaptor"),
        "BRepAlgoAPI": _import_module("OCP.BRepAlgoAPI"),
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


def _sub3(a: Point3D, b: Point3D) -> Point3D:
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _add3(a: Point3D, b: Point3D) -> Point3D:
    return (a[0] + b[0], a[1] + b[1], a[2] + b[2])


def _scale3(value: float, vector: Point3D) -> Point3D:
    return (value * vector[0], value * vector[1], value * vector[2])


def _dot3(a: Point3D, b: Point3D) -> float:
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross3(a: Point3D, b: Point3D) -> Point3D:
    return (
        a[1] * b[2] - a[2] * b[1],
        a[2] * b[0] - a[0] * b[2],
        a[0] * b[1] - a[1] * b[0],
    )


def _shape_solids(shape: Any, mods: dict[str, Any]) -> tuple[Any, ...]:
    solids: list[Any] = []
    explorer = mods["TopExp"].TopExp_Explorer(shape, mods["TopAbs"].TopAbs_SOLID)
    while explorer.More():
        solids.append(_topods_cast(mods, explorer.Current(), "Solid"))
        explorer.Next()
    return tuple(solids)


def _brep_tools_api(mods: dict[str, Any]) -> Any:
    btools = mods["BRepTools"]
    btools_class = getattr(btools, "BRepTools", None)
    if btools_class is not None:
        return btools_class
    return btools


def _read_shape_from_brep(mods: dict[str, Any], brep_path: Path) -> Any:
    if not brep_path.exists():
        raise FileNotFoundError(brep_path)

    shape_cls = getattr(mods["TopoDS"], "TopoDS_Shape", None)
    builder_cls = getattr(mods["BRep"], "BRep_Builder", None)
    if shape_cls is None or builder_cls is None:
        raise RuntimeError("OpenCascade BREP read API unavailable")

    shape = shape_cls()
    builder = builder_cls()
    btools = _brep_tools_api(mods)
    reader = getattr(btools, "Read_s", None)
    if not callable(reader):
        reader = getattr(btools, "Read", None)
    if not callable(reader):
        raise RuntimeError("OpenCascade BREP read API unavailable")

    read_result = reader(shape, str(brep_path), builder)
    if isinstance(read_result, bool) and not read_result:
        raise ValueError(f"failed to read BREP shape from {brep_path}")

    is_null = getattr(shape, "IsNull", None)
    if callable(is_null) and is_null():
        raise ValueError(f"BREP shape is null: {brep_path}")
    return shape


def _write_shape_to_brep(mods: dict[str, Any], shape: Any, brep_path: Path) -> None:
    brep_path.parent.mkdir(parents=True, exist_ok=True)

    btools = _brep_tools_api(mods)
    writer = getattr(btools, "Write_s", None)
    if not callable(writer):
        writer = getattr(btools, "Write", None)
    if not callable(writer):
        raise RuntimeError("OpenCascade BREP write API unavailable")

    write_result = writer(shape, str(brep_path))
    if isinstance(write_result, bool) and not write_result:
        raise ValueError(f"failed to write BREP shape to {brep_path}")


def load_brep_shape_3d(brep_path: str | Path) -> Any:
    """Load one OpenCascade shape from a BREP file path."""

    mods = _ocp_modules_3d()
    return _read_shape_from_brep(mods, Path(brep_path))


def load_brep_solids(brep_path: str | Path) -> tuple[Any, ...]:
    """Load all solids from one BREP file."""

    mods = _ocp_modules_3d()
    shape = _read_shape_from_brep(mods, Path(brep_path))
    solids = _shape_solids(shape, mods)
    if not solids:
        raise ValueError("BREP shape has no solids")
    return solids


def load_brep_solid(brep_path: str | Path) -> Any:
    """Load one solid from BREP and enforce single-solid topology."""

    solids = load_brep_solids(brep_path)
    if len(solids) != 1:
        raise ValueError(f"expected exactly one solid in BREP, got {len(solids)}")
    return solids[0]


def write_brep_shape_3d(shape: Any, *, brep_path: str | Path) -> Path:
    """Write one OpenCascade shape to a BREP file path."""

    mods = _ocp_modules_3d()
    path = Path(brep_path)
    _write_shape_to_brep(mods, shape, path)
    return path


def _surface_adaptor(face: Any, mods: dict[str, Any]) -> Any:
    adaptor_cls = getattr(mods["BRepAdaptor"], "BRepAdaptor_Surface", None)
    if adaptor_cls is None:
        raise RuntimeError("OpenCascade BRepAdaptor_Surface API unavailable")
    try:
        return adaptor_cls(face, True)
    except TypeError:
        return adaptor_cls(face)


def _surface_uv_bounds(adaptor: Any) -> tuple[float, float, float, float]:
    first_u = getattr(adaptor, "FirstUParameter", None)
    last_u = getattr(adaptor, "LastUParameter", None)
    first_v = getattr(adaptor, "FirstVParameter", None)
    last_v = getattr(adaptor, "LastVParameter", None)
    if not (
        callable(first_u)
        and callable(last_u)
        and callable(first_v)
        and callable(last_v)
    ):
        raise RuntimeError("OpenCascade surface parameter bounds API unavailable")
    umin = float(first_u())
    umax = float(last_u())
    vmin = float(first_v())
    vmax = float(last_v())
    if not (umin < umax and vmin < vmax):
        raise ValueError("invalid CAD face parameter bounds")
    return umin, umax, vmin, vmax


def _surface_value(
    adaptor: Any, *, u: float, v: float, mods: dict[str, Any]
) -> Point3D:
    value = getattr(adaptor, "Value", None)
    if callable(value):
        point = value(float(u), float(v))
        return (float(point.X()), float(point.Y()), float(point.Z()))

    d0 = getattr(adaptor, "D0", None)
    gp_mod = mods.get("gp")
    gp_point_cls = getattr(gp_mod, "gp_Pnt", None) if gp_mod is not None else None
    if callable(d0) and gp_point_cls is not None:
        point = gp_point_cls()
        d0(float(u), float(v), point)
        return (float(point.X()), float(point.Y()), float(point.Z()))

    raise RuntimeError("OpenCascade surface point evaluation API unavailable")


def _finite_tangent(
    adaptor: Any,
    *,
    u: float,
    v: float,
    axis: Literal["u", "v"],
    umin: float,
    umax: float,
    vmin: float,
    vmax: float,
    mods: dict[str, Any],
) -> Point3D:
    u_span = max(umax - umin, 1.0)
    v_span = max(vmax - vmin, 1.0)
    h = 1.0e-6 * (u_span if axis == "u" else v_span)
    h = max(h, 1.0e-10)

    if axis == "u":
        low = max(umin, u - h)
        high = min(umax, u + h)
        if high <= low:
            return (0.0, 0.0, 0.0)
        p0 = _surface_value(adaptor, u=low, v=v, mods=mods)
        p1 = _surface_value(adaptor, u=high, v=v, mods=mods)
        inv = 1.0 / (high - low)
        return _scale3(inv, _sub3(p1, p0))

    low = max(vmin, v - h)
    high = min(vmax, v + h)
    if high <= low:
        return (0.0, 0.0, 0.0)
    p0 = _surface_value(adaptor, u=u, v=low, mods=mods)
    p1 = _surface_value(adaptor, u=u, v=high, mods=mods)
    inv = 1.0 / (high - low)
    return _scale3(inv, _sub3(p1, p0))


def _face_classifier(face: Any, *, tol: float, mods: dict[str, Any]) -> Any:
    classifier_cls = getattr(mods["BRepTopAdaptor"], "BRepTopAdaptor_FClass2d", None)
    if classifier_cls is None:
        raise RuntimeError("OpenCascade trimmed-face classifier API unavailable")
    try:
        return classifier_cls(face, float(tol))
    except Exception as exc:
        raise RuntimeError(
            "failed to construct OpenCascade trimmed-face classifier"
        ) from exc


def _classify_uv_inside(
    classifier: Any, *, u: float, v: float, mods: dict[str, Any]
) -> bool:
    perform = getattr(classifier, "Perform", None)
    if not callable(perform):
        raise RuntimeError(
            "OpenCascade trimmed-face classifier Perform API unavailable"
        )

    gp_mod = mods.get("gp")
    point2d_cls = getattr(gp_mod, "gp_Pnt2d", None) if gp_mod is not None else None
    if point2d_cls is None:
        raise RuntimeError("OpenCascade gp_Pnt2d API unavailable")

    try:
        state = perform(point2d_cls(float(u), float(v)))
    except Exception as exc:
        raise RuntimeError("OpenCascade trimmed-face classification failed") from exc

    topabs = mods["TopAbs"]
    in_state = getattr(topabs, "TopAbs_IN", None)
    on_state = getattr(topabs, "TopAbs_ON", None)
    if state == in_state or state == on_state:
        return True
    return False


def _solid_has_non_null_faces(solid: Any, *, mods: dict[str, Any]) -> bool:
    for face in _shape_faces(solid, mods):
        is_null = getattr(face, "IsNull", None)
        if callable(is_null):
            try:
                if bool(is_null()):
                    continue
            except Exception:
                pass
        return True
    return False


def _resolve_seed_from_points(
    points: tuple[Point3D, ...], *, seed: SeedInput3D
) -> Point3D:
    if isinstance(seed, tuple):
        return (float(seed[0]), float(seed[1]), float(seed[2]))

    if seed == "jplus":
        return (1.0, 1.0, 1.0)

    if not points:
        return (0.0, 0.0, 0.0)

    if seed == "centroid":
        scale = 1.0 / len(points)
        return (
            scale * sum(point[0] for point in points),
            scale * sum(point[1] for point in points),
            scale * sum(point[2] for point in points),
        )

    if seed != "grid-best":
        raise ValueError(f"unsupported seed mode: {seed!r}")

    xs = tuple(point[0] for point in points)
    ys = tuple(point[1] for point in points)
    zs = tuple(point[2] for point in points)
    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    if xmax <= xmin:
        xmax = xmin + 1.0
    if ymax <= ymin:
        ymax = ymin + 1.0
    if zmax <= zmin:
        zmax = zmin + 1.0

    candidates: list[Point3D] = []
    for i in range(3):
        x = xmin + (xmax - xmin) * (i / 2.0)
        for j in range(3):
            y = ymin + (ymax - ymin) * (j / 2.0)
            for k in range(3):
                z = zmin + (zmax - zmin) * (k / 2.0)
                candidates.append((x, y, z))

    def _closest_distance_sq(candidate: Point3D) -> float:
        return min(
            (candidate[0] - px) ** 2
            + (candidate[1] - py) ** 2
            + (candidate[2] - pz) ** 2
            for px, py, pz in points
        )

    return max(candidates, key=_closest_distance_sq)


def solid_to_surface_quadrature_3d(
    solid: Any,
    *,
    order: int,
    tol: float = 1.0e-12,
) -> SurfaceQuadratureRule3D:
    """Build oriented surface quadrature over CAD boundary faces without meshing."""

    if order < 1:
        raise ValueError("order must be positive")

    mods = _ocp_modules_3d()
    if not _solid_has_non_null_faces(solid, mods=mods):
        raise ValueError("solid has no boundary faces")

    nodes, weights = gauss_legendre_01(order)
    reversed_flag = getattr(mods["TopAbs"], "TopAbs_REVERSED", None)

    points: list[Point3D] = []
    weighted_normals: list[Point3D] = []

    for face in _shape_faces(solid, mods):
        adaptor = _surface_adaptor(face, mods)
        umin, umax, vmin, vmax = _surface_uv_bounds(adaptor)
        classifier = _face_classifier(face, tol=tol, mods=mods)

        orient_sign = 1.0
        if (
            reversed_flag is not None
            and hasattr(face, "Orientation")
            and face.Orientation() == reversed_flag
        ):
            orient_sign = -1.0

        u_scale = umax - umin
        v_scale = vmax - vmin

        for u_ref, wu_ref in zip(nodes, weights, strict=True):
            u = umin + u_scale * float(u_ref)
            wu = u_scale * float(wu_ref)
            for v_ref, wv_ref in zip(nodes, weights, strict=True):
                v = vmin + v_scale * float(v_ref)
                if not _classify_uv_inside(classifier, u=u, v=v, mods=mods):
                    continue

                point = _surface_value(adaptor, u=u, v=v, mods=mods)
                tangent_u = _finite_tangent(
                    adaptor,
                    u=u,
                    v=v,
                    axis="u",
                    umin=umin,
                    umax=umax,
                    vmin=vmin,
                    vmax=vmax,
                    mods=mods,
                )
                tangent_v = _finite_tangent(
                    adaptor,
                    u=u,
                    v=v,
                    axis="v",
                    umin=umin,
                    umax=umax,
                    vmin=vmin,
                    vmax=vmax,
                    mods=mods,
                )
                area_vector = _cross3(tangent_u, tangent_v)
                weighted = _scale3(
                    orient_sign * wu * v_scale * float(wv_ref),
                    area_vector,
                )

                if abs(weighted[0]) + abs(weighted[1]) + abs(weighted[2]) <= 1.0e-18:
                    continue

                points.append(point)
                weighted_normals.append(weighted)

    if not points:
        raise ValueError("solid boundary face quadrature produced no samples")

    return SurfaceQuadratureRule3D(
        points=tuple(points),
        weighted_normals=tuple(weighted_normals),
    )


def solid_to_folded_quadrature_rule_3d(
    solid: Any,
    *,
    seed: SeedInput3D,
    order: int,
    surface_order: int | None = None,
    tol: float = 1.0e-12,
) -> FoldedSolidQuadrature3D:
    """Build folded volume quadrature for one CAD solid without triangulation."""

    if order < 1:
        raise ValueError("order must be positive")
    if surface_order is None:
        surface_order = order
    if surface_order < 1:
        raise ValueError("surface_order must be positive")

    surface_rule = solid_to_surface_quadrature_3d(
        solid,
        order=surface_order,
        tol=tol,
    )
    selected_seed = _resolve_seed_from_points(surface_rule.points, seed=seed)

    radial_nodes, radial_weights = gauss_legendre_01(order)
    points: list[Point3D] = []
    weights: list[float] = []
    for point, weighted_normal in zip(
        surface_rule.points,
        surface_rule.weighted_normals,
        strict=True,
    ):
        delta = _sub3(point, selected_seed)
        signed_measure = _dot3(delta, weighted_normal)
        for radial, radial_weight in zip(radial_nodes, radial_weights, strict=True):
            radial_value = float(radial)
            folded_point = _add3(selected_seed, _scale3(radial_value, delta))
            points.append(folded_point)
            weights.append(
                signed_measure * radial_value * radial_value * float(radial_weight)
            )

    return FoldedSolidQuadrature3D(
        seed=selected_seed,
        rule=QuadratureRule3D(points=tuple(points), weights=tuple(weights)),
    )


def integrate_general_over_solid_folded_3d(
    solid: Any,
    *,
    seed: SeedInput3D,
    order: int,
    integrand: Any,
    surface_order: int | None = None,
    tol: float = 1.0e-12,
) -> float:
    """Integrate a scalar field over a solid via folded CAD face quadrature."""

    folded = solid_to_folded_quadrature_rule_3d(
        solid,
        seed=seed,
        order=order,
        surface_order=surface_order,
        tol=tol,
    )

    total = 0.0
    for point, weight in zip(folded.rule.points, folded.rule.weights, strict=True):
        total += float(integrand(point[0], point[1], point[2])) * float(weight)
    return total


def solid_has_boundary_faces_3d(
    solid: Any,
    *,
    order: int = 2,
    tol: float = 1.0e-12,
) -> bool:
    """Return whether a solid has boundary faces by topology inspection."""

    _ = (order, tol)
    mods = _ocp_modules_3d()
    return _solid_has_non_null_faces(solid, mods=mods)


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
