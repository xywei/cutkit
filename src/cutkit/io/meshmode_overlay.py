"""Meshmode-oriented cut-overlay contract and deterministic builders."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal, Mapping, Sequence

from cutkit.geometry import Point2D

ElementId = int | str
SourceOverlayStatus = Literal["ok", "empty", "invalid_box", "backend_error"]
OverlayStatus = Literal[
    "ok",
    "empty",
    "invalid_box",
    "backend_error",
    "mapping_mismatch",
    "orientation_mismatch",
]
OverlayDiagnosticCode = Literal[
    "duplicate_source",
    "target_unmapped",
    "target_ambiguous",
    "mapped_source_missing",
    "source_unmapped",
    "unknown_target",
    "orientation_mismatch",
]

_VALID_SOURCE_STATUSES = {"ok", "empty", "invalid_box", "backend_error"}
_VALID_OVERLAY_STATUSES = {
    "ok",
    "empty",
    "invalid_box",
    "backend_error",
    "mapping_mismatch",
    "orientation_mismatch",
}


def _coerce_element_id(value: ElementId, *, name: str) -> ElementId:
    if isinstance(value, bool):
        raise TypeError(f"{name} must be int|str, got bool")
    if isinstance(value, int):
        return value
    if isinstance(value, str):
        text = value.strip()
        if not text:
            raise ValueError(f"{name} must not be empty")
        return text
    raise TypeError(f"{name} must be int|str")


def _element_id_order_key(value: ElementId) -> tuple[int, str]:
    if isinstance(value, int):
        return (0, f"{value:020d}")
    return (1, value)


def _normalize_metadata(metadata: Mapping[str, object]) -> tuple[tuple[str, str], ...]:
    normalized: list[tuple[str, str]] = []
    for key, value in metadata.items():
        normalized.append((str(key), str(value)))
    normalized.sort(key=lambda item: item[0])
    return tuple(normalized)


@dataclass(frozen=True)
class MeshmodeOverlayDiagnostic:
    """One structured diagnostic emitted during overlay construction."""

    code: OverlayDiagnosticCode
    detail: str
    target_element_id: ElementId | None = None
    source_element_id: ElementId | None = None


class MeshmodeOverlayBuildError(ValueError):
    """Raised when strict overlay construction hits a blocking mismatch."""

    def __init__(self, diagnostic: MeshmodeOverlayDiagnostic) -> None:
        super().__init__(diagnostic.detail)
        self.diagnostic = diagnostic


@dataclass(frozen=True)
class MeshmodeOverlayElement:
    """CUTKIT-side element payload for meshmode overlay projection."""

    source_element_id: ElementId
    points: tuple[Point2D, ...] = ()
    weights: tuple[float, ...] = ()
    geometry_metadata: Mapping[str, object] = field(default_factory=dict)
    status: SourceOverlayStatus = "ok"
    orientation: int = 1

    def __post_init__(self) -> None:
        source_element_id = _coerce_element_id(
            self.source_element_id,
            name="source_element_id",
        )
        points = tuple((float(x), float(y)) for x, y in self.points)
        weights = tuple(float(weight) for weight in self.weights)
        if len(points) != len(weights):
            raise ValueError("points and weights length must match")
        if self.status not in _VALID_SOURCE_STATUSES:
            raise ValueError(f"unsupported source overlay status: {self.status!r}")
        if self.orientation not in {-1, 1}:
            raise ValueError("orientation must be +1 or -1")

        metadata = {str(key): value for key, value in self.geometry_metadata.items()}

        object.__setattr__(self, "source_element_id", source_element_id)
        object.__setattr__(self, "points", points)
        object.__setattr__(self, "weights", weights)
        object.__setattr__(self, "geometry_metadata", metadata)


@dataclass(frozen=True)
class MeshmodeCutOverlay:
    """Deterministic contract for meshmode cut-overlay consumption."""

    contract_version: int
    target_element_ids: tuple[ElementId, ...]
    source_element_ids: tuple[ElementId | None, ...]
    statuses: tuple[OverlayStatus, ...]
    diagnostics: tuple[MeshmodeOverlayDiagnostic, ...]
    point_indptr_by_element: tuple[int, ...]
    point_coords: tuple[Point2D, ...]
    point_weights: tuple[float, ...]
    geometry_metadata_by_element: tuple[tuple[tuple[str, str], ...], ...]

    def __post_init__(self) -> None:
        if self.contract_version < 1:
            raise ValueError("contract_version must be >= 1")
        element_count = len(self.target_element_ids)
        if len(self.source_element_ids) != element_count:
            raise ValueError("source_element_ids length must match target_element_ids")
        if len(self.statuses) != element_count:
            raise ValueError("statuses length must match target_element_ids")
        if len(self.geometry_metadata_by_element) != element_count:
            raise ValueError(
                "geometry_metadata_by_element length must match target_element_ids"
            )
        if len(self.point_indptr_by_element) != element_count + 1:
            raise ValueError("point_indptr_by_element length must be n_elements + 1")
        if len(self.point_coords) != len(self.point_weights):
            raise ValueError("point_coords and point_weights length must match")

        previous = 0
        for index, value in enumerate(self.point_indptr_by_element):
            if value < previous:
                raise ValueError(
                    f"point_indptr_by_element must be non-decreasing (index {index})"
                )
            previous = value
        if self.point_indptr_by_element[-1] != len(self.point_coords):
            raise ValueError(
                "final point_indptr_by_element entry must match point count"
            )

        for status in self.statuses:
            if status not in _VALID_OVERLAY_STATUSES:
                raise ValueError(f"unsupported overlay status: {status!r}")


def build_meshmode_cut_overlay(
    elements: Sequence[MeshmodeOverlayElement],
    *,
    target_element_ids: Sequence[ElementId],
    element_id_map: Mapping[ElementId, ElementId],
    expected_orientation_by_target: Mapping[ElementId, int] | None = None,
    strict: bool = True,
    contract_version: int = 1,
) -> MeshmodeCutOverlay:
    """Build one deterministic meshmode overlay payload from CUTKIT inputs."""

    if contract_version < 1:
        raise ValueError("contract_version must be >= 1")

    targets = tuple(
        _coerce_element_id(target_id, name="target_element_id")
        for target_id in target_element_ids
    )
    if len(set(targets)) != len(targets):
        raise ValueError("target_element_ids must be unique")

    expected_orientation: dict[ElementId, int] = {}
    if expected_orientation_by_target is not None:
        for raw_target, raw_orientation in expected_orientation_by_target.items():
            target_id = _coerce_element_id(raw_target, name="orientation target id")
            orientation = int(raw_orientation)
            if orientation not in {-1, 1}:
                raise ValueError("expected orientations must be +1 or -1")
            expected_orientation[target_id] = orientation

    diagnostics: list[MeshmodeOverlayDiagnostic] = []

    def _emit(diagnostic: MeshmodeOverlayDiagnostic) -> None:
        if strict:
            raise MeshmodeOverlayBuildError(diagnostic)
        diagnostics.append(diagnostic)

    elements_by_source: dict[ElementId, MeshmodeOverlayElement] = {}
    for element in elements:
        source_id = _coerce_element_id(
            element.source_element_id,
            name="source_element_id",
        )
        if source_id in elements_by_source:
            _emit(
                MeshmodeOverlayDiagnostic(
                    code="duplicate_source",
                    source_element_id=source_id,
                    detail=f"duplicate CUTKIT source element id {source_id!r}",
                )
            )
            continue
        elements_by_source[source_id] = element

    source_ids_by_target: dict[ElementId, list[ElementId]] = {}
    for raw_source, raw_target in sorted(
        element_id_map.items(),
        key=lambda item: (
            _element_id_order_key(_coerce_element_id(item[1], name="map target id")),
            _element_id_order_key(_coerce_element_id(item[0], name="map source id")),
        ),
    ):
        source_id = _coerce_element_id(raw_source, name="map source id")
        target_id = _coerce_element_id(raw_target, name="map target id")
        source_ids_by_target.setdefault(target_id, []).append(source_id)

    target_set = set(targets)
    for target_id in sorted(
        source_ids_by_target,
        key=_element_id_order_key,
    ):
        if target_id in target_set:
            continue
        _emit(
            MeshmodeOverlayDiagnostic(
                code="unknown_target",
                target_element_id=target_id,
                detail=f"element mapping references unknown target element {target_id!r}",
            )
        )

    mapped_sources = {
        source_id
        for source_ids in source_ids_by_target.values()
        for source_id in source_ids
    }
    for source_id in sorted(elements_by_source, key=_element_id_order_key):
        if source_id in mapped_sources:
            continue
        _emit(
            MeshmodeOverlayDiagnostic(
                code="source_unmapped",
                source_element_id=source_id,
                detail=f"CUTKIT source element {source_id!r} is not mapped to any target",
            )
        )

    source_element_ids: list[ElementId | None] = []
    statuses: list[OverlayStatus] = []
    metadata_by_element: list[tuple[tuple[str, str], ...]] = []
    point_indptr = [0]
    point_coords: list[Point2D] = []
    point_weights: list[float] = []

    for target_id in targets:
        source_ids = source_ids_by_target.get(target_id, [])
        if not source_ids:
            source_element_ids.append(None)
            statuses.append("mapping_mismatch")
            metadata_by_element.append(())
            point_indptr.append(len(point_coords))
            _emit(
                MeshmodeOverlayDiagnostic(
                    code="target_unmapped",
                    target_element_id=target_id,
                    detail=f"target element {target_id!r} has no mapping",
                )
            )
            continue

        if len(source_ids) > 1:
            source_element_ids.append(None)
            statuses.append("mapping_mismatch")
            metadata_by_element.append(())
            point_indptr.append(len(point_coords))
            _emit(
                MeshmodeOverlayDiagnostic(
                    code="target_ambiguous",
                    target_element_id=target_id,
                    detail=(
                        f"target element {target_id!r} maps to multiple CUTKIT sources"
                    ),
                )
            )
            continue

        source_id = source_ids[0]
        source_element_ids.append(source_id)
        mapped_element = elements_by_source.get(source_id)
        if mapped_element is None:
            statuses.append("mapping_mismatch")
            metadata_by_element.append(())
            point_indptr.append(len(point_coords))
            _emit(
                MeshmodeOverlayDiagnostic(
                    code="mapped_source_missing",
                    source_element_id=source_id,
                    target_element_id=target_id,
                    detail=(
                        f"mapped source element {source_id!r} is missing from CUTKIT payload"
                    ),
                )
            )
            continue

        expected = expected_orientation.get(target_id, 1)
        if mapped_element.orientation != expected:
            statuses.append("orientation_mismatch")
            metadata_by_element.append(())
            point_indptr.append(len(point_coords))
            _emit(
                MeshmodeOverlayDiagnostic(
                    code="orientation_mismatch",
                    target_element_id=target_id,
                    source_element_id=source_id,
                    detail=(
                        f"orientation mismatch for target {target_id!r}: "
                        f"expected {expected:+d}, got {mapped_element.orientation:+d}"
                    ),
                )
            )
            continue

        metadata_by_element.append(
            _normalize_metadata(mapped_element.geometry_metadata)
        )
        if mapped_element.status != "ok":
            statuses.append(mapped_element.status)
            point_indptr.append(len(point_coords))
            continue

        if not mapped_element.points:
            statuses.append("empty")
            point_indptr.append(len(point_coords))
            continue

        statuses.append("ok")
        point_coords.extend(mapped_element.points)
        point_weights.extend(mapped_element.weights)
        point_indptr.append(len(point_coords))

    return MeshmodeCutOverlay(
        contract_version=contract_version,
        target_element_ids=targets,
        source_element_ids=tuple(source_element_ids),
        statuses=tuple(statuses),
        diagnostics=tuple(diagnostics),
        point_indptr_by_element=tuple(point_indptr),
        point_coords=tuple(point_coords),
        point_weights=tuple(point_weights),
        geometry_metadata_by_element=tuple(metadata_by_element),
    )


__all__ = [
    "ElementId",
    "MeshmodeCutOverlay",
    "MeshmodeOverlayBuildError",
    "MeshmodeOverlayDiagnostic",
    "MeshmodeOverlayElement",
    "OverlayDiagnosticCode",
    "OverlayStatus",
    "SourceOverlayStatus",
    "build_meshmode_cut_overlay",
]
