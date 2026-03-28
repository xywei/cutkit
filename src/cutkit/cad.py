"""Consumer-facing CAD facade for load/clip/folded integration workflows.

This module provides a high-level interface that composes existing CUTKIT
OpenCascade IO adapters and folded quadrature kernels.
"""

from __future__ import annotations

import importlib.util
from dataclasses import dataclass
from math import isfinite, prod
from pathlib import Path
from typing import Any, Callable, Literal, Sequence, cast

from cutkit.geometry import (
    BoundaryTriangulation3D,
    CurveTrimmedPanel2D,
    Point2D,
    Point3D,
)
from cutkit.io import (
    clip_solid_with_axis_aligned_box,
    face_to_curve_panel,
    intersect_face_with_rectangle,
    load_brep_face,
    load_brep_solid,
    opencascade3d_status,
    opencascade_status,
    solid_to_boundary_triangulation,
    solid_to_oriented_boundary_triangles,
)
from cutkit.quadrature import (
    folded_curve_quadrature_rule,
    integrate_general_over_boundary_3d,
    seed_grid_3d,
)

if importlib.util.find_spec("numpy") is not None:
    import numpy as _np  # type: ignore[import-not-found]
else:
    _np = None

BatchStatus = Literal["ok", "empty", "invalid_box", "backend_error"]
SeedMode3D = Literal["jplus", "centroid", "grid-best"]
SeedInput3D = Point3D | SeedMode3D


@dataclass(frozen=True)
class Box2D:
    """One axis-aligned 2D clipping box."""

    x0: float
    x1: float
    y0: float
    y1: float

    def __post_init__(self) -> None:
        x0 = _coerce_finite(self.x0, name="x0")
        x1 = _coerce_finite(self.x1, name="x1")
        y0 = _coerce_finite(self.y0, name="y0")
        y1 = _coerce_finite(self.y1, name="y1")
        if x1 <= x0:
            raise ValueError("box bounds must satisfy x1>x0")
        if y1 <= y0:
            raise ValueError("box bounds must satisfy y1>y0")
        object.__setattr__(self, "x0", x0)
        object.__setattr__(self, "x1", x1)
        object.__setattr__(self, "y0", y0)
        object.__setattr__(self, "y1", y1)


@dataclass(frozen=True)
class Box3D:
    """One axis-aligned 3D clipping box."""

    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float

    def __post_init__(self) -> None:
        x0 = _coerce_finite(self.x0, name="x0")
        x1 = _coerce_finite(self.x1, name="x1")
        y0 = _coerce_finite(self.y0, name="y0")
        y1 = _coerce_finite(self.y1, name="y1")
        z0 = _coerce_finite(self.z0, name="z0")
        z1 = _coerce_finite(self.z1, name="z1")
        if x1 <= x0:
            raise ValueError("box bounds must satisfy x1>x0")
        if y1 <= y0:
            raise ValueError("box bounds must satisfy y1>y0")
        if z1 <= z0:
            raise ValueError("box bounds must satisfy z1>z0")
        object.__setattr__(self, "x0", x0)
        object.__setattr__(self, "x1", x1)
        object.__setattr__(self, "y0", y0)
        object.__setattr__(self, "y1", y1)
        object.__setattr__(self, "z0", z0)
        object.__setattr__(self, "z1", z1)


@dataclass(frozen=True)
class Box2DArray:
    """Array-mode container for many 2D clip boxes."""

    x0: Any
    x1: Any
    y0: Any
    y1: Any


@dataclass(frozen=True)
class Box3DArray:
    """Array-mode container for many 3D clip boxes."""

    x0: Any
    x1: Any
    y0: Any
    y1: Any
    z0: Any
    z1: Any


@dataclass(frozen=True)
class CadBatchClip2D:
    """Batch clipping output for 2D CAD faces."""

    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float], ...]
    statuses: tuple[BatchStatus, ...]
    panels: tuple[tuple[CurveTrimmedPanel2D, ...], ...]
    errors: tuple[str | None, ...]

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def panels_shaped(self) -> Any:
        return _reshape_flat(self.panels, self.shape)


@dataclass(frozen=True)
class CadBatchClip3D:
    """Batch clipping output for 3D CAD solids."""

    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float, float, float], ...]
    statuses: tuple[BatchStatus, ...]
    solids: tuple[CadSolid3D | None, ...]
    errors: tuple[str | None, ...]

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def solids_shaped(self) -> Any:
        return _reshape_flat(self.solids, self.shape)


@dataclass(frozen=True)
class CadBatchIntegral2D:
    """Batch folded-integration output for 2D CAD workflows."""

    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float], ...]
    statuses: tuple[BatchStatus, ...]
    values: tuple[float | None, ...]
    errors: tuple[str | None, ...]

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def values_shaped(self) -> Any:
        return _reshape_flat(self.values, self.shape)


@dataclass(frozen=True)
class CadBatchIntegral3D:
    """Batch folded-integration output for 3D CAD workflows."""

    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float, float, float], ...]
    statuses: tuple[BatchStatus, ...]
    values: tuple[float | None, ...]
    errors: tuple[str | None, ...]

    def statuses_shaped(self) -> Any:
        return _reshape_flat(self.statuses, self.shape)

    def values_shaped(self) -> Any:
        return _reshape_flat(self.values, self.shape)


@dataclass(frozen=True)
class CadSession:
    """Backend session for consumer-facing CAD workflows."""

    backend: Literal["opencascade"] = "opencascade"

    @staticmethod
    def opencascade() -> CadSession:
        """Create an OpenCascade-backed CAD session."""

        return CadSession(backend="opencascade")

    def load_face(self, brep_path: str | Path) -> CadFace2D:
        """Load a single-face BREP as a CAD 2D face handle."""

        status = opencascade_status()
        if not status.available:
            raise RuntimeError(status.reason or "OpenCascade 2D backend unavailable")
        return CadFace2D.from_face(load_brep_face(brep_path), session=self)

    def load_solid(self, brep_path: str | Path) -> CadSolid3D:
        """Load a single-solid BREP as a CAD 3D solid handle."""

        status = opencascade3d_status()
        if not status.available:
            raise RuntimeError(status.reason or "OpenCascade 3D backend unavailable")
        return CadSolid3D.from_solid(load_brep_solid(brep_path), session=self)


@dataclass(frozen=True)
class CadFace2D:
    """Consumer-facing handle for one CAD 2D face."""

    _face: Any
    _session: CadSession

    @classmethod
    def from_face(cls, face: Any, *, session: CadSession | None = None) -> CadFace2D:
        if session is None:
            session = CadSession.opencascade()
        return cls(_face=face, _session=session)

    @property
    def face(self) -> Any:
        return self._face

    @property
    def session(self) -> CadSession:
        return self._session

    def to_curve_panel(self) -> CurveTrimmedPanel2D:
        """Convert the CAD face boundary to one curve-trimmed panel."""

        return face_to_curve_panel(self._face)

    def clip_box(self, box: Box2D) -> tuple[CurveTrimmedPanel2D, ...]:
        """Clip this face with one axis-aligned box and return resulting panels."""

        return intersect_face_with_rectangle(
            self._face,
            x0=box.x0,
            x1=box.x1,
            y0=box.y0,
            y1=box.y1,
        )

    def clip_boxes(
        self,
        boxes: Box2D | Sequence[Box2D] | Box2DArray | None = None,
        *,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        strict: bool = True,
    ) -> CadBatchClip2D:
        """Clip this face by one or many boxes (object mode or array mode)."""

        normalized = _normalize_boxes2d_inputs(
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
        )

        statuses: list[BatchStatus] = []
        clipped_panels: list[tuple[CurveTrimmedPanel2D, ...]] = []
        errors: list[str | None] = []

        for bounds in normalized.box_bounds:
            try:
                box = Box2D(*bounds)
            except (ValueError, TypeError, OverflowError) as exc:
                if strict:
                    raise
                statuses.append("invalid_box")
                clipped_panels.append(())
                errors.append(str(exc))
                continue

            try:
                panels = self.clip_box(box)
            except Exception as exc:
                if strict:
                    raise
                statuses.append("backend_error")
                clipped_panels.append(())
                errors.append(str(exc))
                continue

            if panels:
                statuses.append("ok")
                errors.append(None)
            else:
                statuses.append("empty")
                errors.append(None)
            clipped_panels.append(panels)

        return CadBatchClip2D(
            shape=normalized.shape,
            box_bounds=normalized.box_bounds,
            statuses=tuple(statuses),
            panels=tuple(clipped_panels),
            errors=tuple(errors),
        )

    def integrate_folded(
        self,
        integrand: Callable[[Any, Any], Any],
        *,
        order: int,
        anchor: Point2D | Literal["auto"] = "auto",
        require_interior_anchor: bool = True,
        anchor_sample_points: int = 48,
    ) -> float:
        """Integrate over this face boundary using folded curve quadrature."""

        panel = self.to_curve_panel()
        return _integrate_curve_panel(
            panel,
            integrand=integrand,
            order=order,
            anchor=anchor,
            require_interior_anchor=require_interior_anchor,
            anchor_sample_points=anchor_sample_points,
        )

    def integrate_over_boxes(
        self,
        integrand: Callable[[Any, Any], Any],
        *,
        order: int,
        boxes: Box2D | Sequence[Box2D] | Box2DArray | None = None,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        anchor: Point2D | Literal["auto"] = "auto",
        require_interior_anchor: bool = True,
        anchor_sample_points: int = 48,
        strict: bool = True,
    ) -> CadBatchIntegral2D:
        """Run folded integration over one or many clipped 2D boxes."""

        clip_batch = self.clip_boxes(
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            strict=strict,
        )

        statuses: list[BatchStatus] = []
        values: list[float | None] = []
        errors: list[str | None] = []

        for status, panels, error in zip(
            clip_batch.statuses,
            clip_batch.panels,
            clip_batch.errors,
            strict=True,
        ):
            if status != "ok":
                statuses.append(status)
                values.append(None)
                errors.append(error)
                continue

            try:
                value = sum(
                    _integrate_curve_panel(
                        panel,
                        integrand=integrand,
                        order=order,
                        anchor=anchor,
                        require_interior_anchor=require_interior_anchor,
                        anchor_sample_points=anchor_sample_points,
                    )
                    for panel in panels
                )
            except Exception as exc:
                if strict:
                    raise
                statuses.append("backend_error")
                values.append(None)
                errors.append(str(exc))
                continue

            statuses.append("ok")
            values.append(float(value))
            errors.append(None)

        return CadBatchIntegral2D(
            shape=clip_batch.shape,
            box_bounds=clip_batch.box_bounds,
            statuses=tuple(statuses),
            values=tuple(values),
            errors=tuple(errors),
        )

    def source_cloud_over_boxes(
        self,
        density: Callable[[Any, Any], Any],
        *,
        order: int,
        boxes: Box2D | Sequence[Box2D] | Box2DArray | None = None,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        backend_mode: Literal["jplus", "folded"] = "folded",
        strict: bool = True,
    ) -> Any:
        """Build a scaffolded far-field source cloud over one or many boxes."""

        from cutkit.potentials import source_cloud_over_boxes_2d

        return source_cloud_over_boxes_2d(
            self,
            density,
            boxes=boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            order=order,
            backend_mode=backend_mode,
            strict=strict,
        )


@dataclass(frozen=True)
class CadSolid3D:
    """Consumer-facing handle for one CAD 3D solid."""

    _solid: Any
    _session: CadSession

    @classmethod
    def from_solid(cls, solid: Any, *, session: CadSession | None = None) -> CadSolid3D:
        if session is None:
            session = CadSession.opencascade()
        return cls(_solid=solid, _session=session)

    @property
    def solid(self) -> Any:
        return self._solid

    @property
    def session(self) -> CadSession:
        return self._session

    def clip_box(self, box: Box3D) -> CadSolid3D:
        """Clip this solid by one axis-aligned box and return a new handle."""

        clipped = clip_solid_with_axis_aligned_box(
            self._solid,
            x0=box.x0,
            x1=box.x1,
            y0=box.y0,
            y1=box.y1,
            z0=box.z0,
            z1=box.z1,
        )
        return CadSolid3D.from_solid(clipped, session=self._session)

    def clip_boxes(
        self,
        boxes: Box3D | Sequence[Box3D] | Box3DArray | None = None,
        *,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        z0: Any | None = None,
        z1: Any | None = None,
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
        strict: bool = True,
        validate_boundary: bool = True,
    ) -> CadBatchClip3D:
        """Clip this solid by one or many boxes (object mode or array mode)."""

        normalized = _normalize_boxes3d_inputs(
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
        )

        statuses: list[BatchStatus] = []
        clipped_solids: list[CadSolid3D | None] = []
        errors: list[str | None] = []

        for bounds in normalized.box_bounds:
            try:
                box = Box3D(*bounds)
            except (ValueError, TypeError, OverflowError) as exc:
                if strict:
                    raise
                statuses.append("invalid_box")
                clipped_solids.append(None)
                errors.append(str(exc))
                continue

            try:
                clipped = self.clip_box(box)
            except Exception as exc:
                if strict:
                    raise
                statuses.append("backend_error")
                clipped_solids.append(None)
                errors.append(str(exc))
                continue

            if _is_null_shape(clipped.solid):
                statuses.append("empty")
                clipped_solids.append(None)
                errors.append(None)
                continue

            if validate_boundary:
                try:
                    if not _has_extractable_boundary(
                        clipped.solid,
                        linear_deflection=linear_deflection,
                        angular_deflection=angular_deflection,
                        tol=tol,
                    ):
                        statuses.append("empty")
                        clipped_solids.append(None)
                        errors.append(None)
                        continue
                except Exception as exc:
                    if strict:
                        raise
                    statuses.append("backend_error")
                    clipped_solids.append(None)
                    errors.append(str(exc))
                    continue

            statuses.append("ok")
            clipped_solids.append(clipped)
            errors.append(None)

        return CadBatchClip3D(
            shape=normalized.shape,
            box_bounds=normalized.box_bounds,
            statuses=tuple(statuses),
            solids=tuple(clipped_solids),
            errors=tuple(errors),
        )

    def to_boundary_triangulation(
        self,
        *,
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
    ) -> BoundaryTriangulation3D:
        """Extract one oriented boundary triangulation for this solid."""

        return solid_to_boundary_triangulation(
            self._solid,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
        )

    def integrate_folded_boundary(
        self,
        integrand: Callable[[Any, Any, Any], Any],
        *,
        order: int,
        seed: SeedInput3D = "jplus",
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
    ) -> float:
        """Integrate over this solid via folded boundary decomposition."""

        boundary = solid_to_oriented_boundary_triangles(
            self._solid,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
        )
        selected_seed = _resolve_seed(boundary, seed=seed)
        return float(
            integrate_general_over_boundary_3d(
                boundary,
                seed=selected_seed,
                order=order,
                integrand=integrand,
            )
        )

    def integrate_over_boxes(
        self,
        integrand: Callable[[Any, Any, Any], Any],
        *,
        order: int,
        boxes: Box3D | Sequence[Box3D] | Box3DArray | None = None,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        z0: Any | None = None,
        z1: Any | None = None,
        seed: SeedInput3D = "jplus",
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
        strict: bool = True,
    ) -> CadBatchIntegral3D:
        """Run folded integration over one or many clipped 3D boxes."""

        clip_batch = self.clip_boxes(
            boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
            strict=strict,
            validate_boundary=False,
        )

        statuses: list[BatchStatus] = []
        values: list[float | None] = []
        errors: list[str | None] = []

        for status, clipped, error in zip(
            clip_batch.statuses,
            clip_batch.solids,
            clip_batch.errors,
            strict=True,
        ):
            if status != "ok":
                statuses.append(status)
                values.append(None)
                errors.append(error)
                continue

            if clipped is None:
                if strict:
                    raise RuntimeError("internal clip result is missing solid handle")
                statuses.append("backend_error")
                values.append(None)
                errors.append("internal clip result is missing solid handle")
                continue

            try:
                boundary = solid_to_oriented_boundary_triangles(
                    clipped.solid,
                    linear_deflection=linear_deflection,
                    angular_deflection=angular_deflection,
                    tol=tol,
                )
                selected_seed = _resolve_seed(boundary, seed=seed)
                value = float(
                    integrate_general_over_boundary_3d(
                        boundary,
                        seed=selected_seed,
                        order=order,
                        integrand=integrand,
                    )
                )
            except ValueError as exc:
                if _is_empty_boundary_error(exc):
                    statuses.append("empty")
                    values.append(None)
                    errors.append(None)
                    continue
                if strict:
                    raise
                statuses.append("backend_error")
                values.append(None)
                errors.append(str(exc))
                continue
            except Exception as exc:
                if strict:
                    raise
                statuses.append("backend_error")
                values.append(None)
                errors.append(str(exc))
                continue

            statuses.append("ok")
            values.append(value)
            errors.append(None)

        return CadBatchIntegral3D(
            shape=clip_batch.shape,
            box_bounds=clip_batch.box_bounds,
            statuses=tuple(statuses),
            values=tuple(values),
            errors=tuple(errors),
        )

    def source_cloud_over_boxes(
        self,
        density: Callable[[Any, Any, Any], Any],
        *,
        order: int,
        boxes: Box3D | Sequence[Box3D] | Box3DArray | None = None,
        x0: Any | None = None,
        x1: Any | None = None,
        y0: Any | None = None,
        y1: Any | None = None,
        z0: Any | None = None,
        z1: Any | None = None,
        seed: SeedInput3D = "grid-best",
        backend_mode: Literal["jplus", "folded"] = "folded",
        linear_deflection: float = 1.0e-3,
        angular_deflection: float = 0.5,
        tol: float = 1.0e-12,
        strict: bool = True,
    ) -> Any:
        """Build a scaffolded far-field source cloud over one or many boxes."""

        from cutkit.potentials import source_cloud_over_boxes_3d

        return source_cloud_over_boxes_3d(
            self,
            density,
            boxes=boxes,
            x0=x0,
            x1=x1,
            y0=y0,
            y1=y1,
            z0=z0,
            z1=z1,
            order=order,
            seed=seed,
            backend_mode=backend_mode,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
            strict=strict,
        )


@dataclass(frozen=True)
class _NormalizedBoxes2D:
    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float], ...]


@dataclass(frozen=True)
class _NormalizedBoxes3D:
    shape: tuple[int, ...]
    box_bounds: tuple[tuple[float, float, float, float, float, float], ...]


def _coerce_finite(value: Any, *, name: str) -> float:
    numeric = float(value)
    if not isfinite(numeric):
        raise ValueError(f"{name} must be finite")
    return numeric


def _reshape_flat(values: Sequence[Any], shape: tuple[int, ...]) -> Any:
    if shape == ():
        if not values:
            raise ValueError("cannot reshape empty sequence to scalar shape")
        return values[0]
    if not shape:
        return tuple(values)
    if len(shape) == 1:
        return tuple(values)
    chunk = prod(shape[1:])
    return tuple(
        _reshape_flat(values[index * chunk : (index + 1) * chunk], shape[1:])
        for index in range(shape[0])
    )


def _is_scalar(value: Any) -> bool:
    return isinstance(value, (str, bytes)) or not isinstance(value, Sequence)


def _coerce_1d_sequence(name: str, value: Any) -> tuple[Any, ...]:
    if isinstance(value, (str, bytes)):
        raise TypeError(f"{name} must be numeric scalar or sequence")
    if not isinstance(value, Sequence):
        raise TypeError(f"{name} must be numeric scalar or sequence")
    out: list[Any] = []
    for item in value:
        if isinstance(item, Sequence) and not isinstance(item, (str, bytes)):
            raise TypeError(f"{name} without NumPy supports only 1D sequences")
        out.append(item)
    if not out:
        raise ValueError(f"{name} sequence must not be empty")
    return tuple(out)


def _broadcast_coordinate_values(
    names: tuple[str, ...],
    values: tuple[Any, ...],
) -> tuple[tuple[int, ...], tuple[tuple[Any, ...], ...]]:
    if _np is not None:
        arrays: list[Any] = []
        for _name, value in zip(names, values, strict=True):
            arrays.append(cast(Any, _np).asarray(value))

        try:
            broadcasted = tuple(cast(Any, _np).broadcast_arrays(*arrays))
        except ValueError as exc:
            raise ValueError("box coordinate arrays could not broadcast") from exc

        shape = tuple(int(dim) for dim in broadcasted[0].shape)
        flat_values: list[tuple[Any, ...]] = []
        for arr in broadcasted:
            flat = cast(Any, arr).ravel(order="C")
            flat_values.append(tuple(item for item in flat))
        if not flat_values[0]:
            raise ValueError("at least one box is required")
        return shape, tuple(flat_values)

    scalar_flags: list[bool] = []
    normalized: list[tuple[Any, ...]] = []
    for name, value in zip(names, values, strict=True):
        if _is_scalar(value):
            scalar_flags.append(True)
            normalized.append((value,))
            continue
        scalar_flags.append(False)
        normalized.append(_coerce_1d_sequence(name, value))

    target_len = max(len(item) for item in normalized)
    if target_len < 1:
        raise ValueError("at least one box is required")

    expanded: list[tuple[Any, ...]] = []
    for name, item in zip(names, normalized, strict=True):
        if len(item) == target_len:
            expanded.append(item)
            continue
        if len(item) == 1:
            expanded.append(tuple(item[0] for _ in range(target_len)))
            continue
        raise ValueError(
            f"{name} length {len(item)} cannot broadcast to batch length {target_len}"
        )

    shape = () if all(scalar_flags) else (target_len,)
    return shape, tuple(expanded)


def _normalize_boxes2d_inputs(
    boxes: Box2D | Sequence[Box2D] | Box2DArray | None,
    *,
    x0: Any | None,
    x1: Any | None,
    y0: Any | None,
    y1: Any | None,
) -> _NormalizedBoxes2D:
    coords_provided = any(value is not None for value in (x0, x1, y0, y1))

    if boxes is not None and coords_provided:
        raise ValueError("provide either boxes=... or coordinate arrays, not both")

    if boxes is None and not coords_provided:
        raise ValueError("missing box inputs; provide boxes=... or coordinate arrays")

    if isinstance(boxes, Box2D):
        return _NormalizedBoxes2D(
            shape=(),
            box_bounds=((boxes.x0, boxes.x1, boxes.y0, boxes.y1),),
        )

    if isinstance(boxes, Box2DArray):
        shape, arrays = _broadcast_coordinate_values(
            ("x0", "x1", "y0", "y1"),
            (boxes.x0, boxes.x1, boxes.y0, boxes.y1),
        )
    elif boxes is None:
        if x0 is None or x1 is None or y0 is None or y1 is None:
            raise ValueError("x0/x1/y0/y1 must all be provided in array mode")
        shape, arrays = _broadcast_coordinate_values(
            ("x0", "x1", "y0", "y1"),
            (x0, x1, y0, y1),
        )
    else:
        if isinstance(boxes, (str, bytes)):
            raise TypeError("boxes must be Box2D or sequence of Box2D")
        if not isinstance(boxes, Sequence):
            raise TypeError("boxes must be Box2D or sequence of Box2D")
        bounds: list[tuple[float, float, float, float]] = []
        for item in boxes:
            if not isinstance(item, Box2D):
                raise TypeError("boxes sequence must contain only Box2D values")
            bounds.append((item.x0, item.x1, item.y0, item.y1))
        if not bounds:
            raise ValueError("boxes sequence must not be empty")
        return _NormalizedBoxes2D(shape=(len(bounds),), box_bounds=tuple(bounds))

    box_bounds = tuple(
        (arrays[0][idx], arrays[1][idx], arrays[2][idx], arrays[3][idx])
        for idx in range(len(arrays[0]))
    )
    return _NormalizedBoxes2D(shape=shape, box_bounds=box_bounds)


def _normalize_boxes3d_inputs(
    boxes: Box3D | Sequence[Box3D] | Box3DArray | None,
    *,
    x0: Any | None,
    x1: Any | None,
    y0: Any | None,
    y1: Any | None,
    z0: Any | None,
    z1: Any | None,
) -> _NormalizedBoxes3D:
    coords_provided = any(value is not None for value in (x0, x1, y0, y1, z0, z1))

    if boxes is not None and coords_provided:
        raise ValueError("provide either boxes=... or coordinate arrays, not both")

    if boxes is None and not coords_provided:
        raise ValueError("missing box inputs; provide boxes=... or coordinate arrays")

    if isinstance(boxes, Box3D):
        return _NormalizedBoxes3D(
            shape=(),
            box_bounds=((boxes.x0, boxes.x1, boxes.y0, boxes.y1, boxes.z0, boxes.z1),),
        )

    if isinstance(boxes, Box3DArray):
        shape, arrays = _broadcast_coordinate_values(
            ("x0", "x1", "y0", "y1", "z0", "z1"),
            (boxes.x0, boxes.x1, boxes.y0, boxes.y1, boxes.z0, boxes.z1),
        )
    elif boxes is None:
        if (
            x0 is None
            or x1 is None
            or y0 is None
            or y1 is None
            or z0 is None
            or z1 is None
        ):
            raise ValueError("x0/x1/y0/y1/z0/z1 must all be provided in array mode")
        shape, arrays = _broadcast_coordinate_values(
            ("x0", "x1", "y0", "y1", "z0", "z1"),
            (x0, x1, y0, y1, z0, z1),
        )
    else:
        if isinstance(boxes, (str, bytes)):
            raise TypeError("boxes must be Box3D or sequence of Box3D")
        if not isinstance(boxes, Sequence):
            raise TypeError("boxes must be Box3D or sequence of Box3D")
        bounds: list[tuple[float, float, float, float, float, float]] = []
        for item in boxes:
            if not isinstance(item, Box3D):
                raise TypeError("boxes sequence must contain only Box3D values")
            bounds.append((item.x0, item.x1, item.y0, item.y1, item.z0, item.z1))
        if not bounds:
            raise ValueError("boxes sequence must not be empty")
        return _NormalizedBoxes3D(shape=(len(bounds),), box_bounds=tuple(bounds))

    box_bounds = tuple(
        (
            arrays[0][idx],
            arrays[1][idx],
            arrays[2][idx],
            arrays[3][idx],
            arrays[4][idx],
            arrays[5][idx],
        )
        for idx in range(len(arrays[0]))
    )
    return _NormalizedBoxes3D(shape=shape, box_bounds=box_bounds)


def _integrate_curve_panel(
    panel: CurveTrimmedPanel2D,
    *,
    integrand: Callable[[Any, Any], Any],
    order: int,
    anchor: Point2D | Literal["auto"],
    require_interior_anchor: bool,
    anchor_sample_points: int,
) -> float:
    anchor_value: Point2D | None
    if anchor == "auto":
        anchor_value = None
    else:
        anchor_value = (
            _coerce_finite(anchor[0], name="anchor.x"),
            _coerce_finite(anchor[1], name="anchor.y"),
        )

    folded = folded_curve_quadrature_rule(
        panel,
        order=order,
        anchor=anchor_value,
        require_interior_anchor=require_interior_anchor,
        anchor_sample_points=anchor_sample_points,
    )
    total = 0.0
    for (x_coord, y_coord), weight in zip(
        folded.rule.points,
        folded.rule.weights,
        strict=True,
    ):
        total += float(integrand(x_coord, y_coord)) * weight
    return float(total)


def _resolve_seed(
    boundary: tuple[tuple[Point3D, Point3D, Point3D], ...], *, seed: SeedInput3D
) -> Point3D:
    if isinstance(seed, str):
        if seed == "jplus":
            return (1.0, 1.0, 1.0)
        if seed == "centroid":
            vertices = tuple(vertex for tri in boundary for vertex in tri)
            scale = 1.0 / len(vertices)
            return (
                scale * sum(vertex[0] for vertex in vertices),
                scale * sum(vertex[1] for vertex in vertices),
                scale * sum(vertex[2] for vertex in vertices),
            )
        if seed == "grid-best":
            return _grid_best_seed(boundary)
        raise ValueError(f"unsupported seed mode: {seed!r}")

    return (
        _coerce_finite(seed[0], name="seed.x"),
        _coerce_finite(seed[1], name="seed.y"),
        _coerce_finite(seed[2], name="seed.z"),
    )


def _grid_best_seed(boundary: tuple[tuple[Point3D, Point3D, Point3D], ...]) -> Point3D:
    vertices = tuple(vertex for tri in boundary for vertex in tri)
    xs = tuple(vertex[0] for vertex in vertices)
    ys = tuple(vertex[1] for vertex in vertices)
    zs = tuple(vertex[2] for vertex in vertices)

    xmin, xmax = min(xs), max(xs)
    ymin, ymax = min(ys), max(ys)
    zmin, zmax = min(zs), max(zs)
    if xmax <= xmin:
        xmax = xmin + 1.0
    if ymax <= ymin:
        ymax = ymin + 1.0
    if zmax <= zmin:
        zmax = zmin + 1.0

    unit_grid = seed_grid_3d(3)
    candidates: tuple[Point3D, ...] = tuple(
        (
            xmin + (xmax - xmin) * seed[0],
            ymin + (ymax - ymin) * seed[1],
            zmin + (zmax - zmin) * seed[2],
        )
        for seed in unit_grid
    )

    def closest_vertex_distance_squared(candidate: Point3D) -> float:
        return min(
            (candidate[0] - vertex[0]) ** 2
            + (candidate[1] - vertex[1]) ** 2
            + (candidate[2] - vertex[2]) ** 2
            for vertex in vertices
        )

    return max(candidates, key=closest_vertex_distance_squared)


def _is_empty_boundary_error(exc: ValueError) -> bool:
    message = str(exc).lower()
    return (
        "no boundary triangles" in message or "no non-degenerate triangles" in message
    )


def _is_null_shape(shape: Any) -> bool:
    is_null = getattr(shape, "IsNull", None)
    if not callable(is_null):
        return False
    try:
        return bool(is_null())
    except Exception:
        return False


def _has_extractable_boundary(
    shape: Any,
    *,
    linear_deflection: float,
    angular_deflection: float,
    tol: float,
) -> bool:
    try:
        boundary = solid_to_oriented_boundary_triangles(
            shape,
            linear_deflection=linear_deflection,
            angular_deflection=angular_deflection,
            tol=tol,
        )
    except ValueError as exc:
        if _is_empty_boundary_error(exc):
            return False
        raise
    return bool(boundary)


__all__ = [
    "BatchStatus",
    "Box2D",
    "Box2DArray",
    "Box3D",
    "Box3DArray",
    "CadBatchClip2D",
    "CadBatchClip3D",
    "CadBatchIntegral2D",
    "CadBatchIntegral3D",
    "CadFace2D",
    "CadSession",
    "CadSolid3D",
    "SeedInput3D",
    "SeedMode3D",
]
