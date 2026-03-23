"""Cut-panel evaluation harness for baseline geometric invariants."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib.resources import files
import math
from pathlib import Path
import re

from cutkit.diagnostics import area_consistency, moment_report
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.quadrature import folded_quadrature_rule
from cutkit.topology import (
    PanelValidationResult,
    point_in_loop,
    point_in_panel,
    validate_panel,
)

Point = tuple[float, float]
Loop = tuple[Point, ...]
_AREA_TOL = 1.0e-14
_VISUAL_SNAPSHOT_WIDTH = 32
_VISUAL_SNAPSHOT_HEIGHT = 16


@dataclass(frozen=True)
class CutPanelCase:
    """Parametric-space cut-panel case with one outer loop and optional holes."""

    name: str
    outer: Loop
    holes: tuple[Loop, ...] = ()
    source: str = "baseline"
    tags: tuple[str, ...] = ()


@dataclass(frozen=True)
class CutPanelMetrics:
    """Computed metrics for one cut-panel case."""

    name: str
    source: str
    tags: tuple[str, ...]
    area: float
    bbox_area: float
    cut_fraction: float
    outer_orientation: str
    hole_orientations: tuple[str, ...]
    folded_triangle_area: float | None = None
    folded_rule_area: float | None = None
    folded_triangle_abs_error: float | None = None
    folded_rule_abs_error: float | None = None
    folded_max_moment_abs_error: float | None = None


@dataclass(frozen=True)
class CutPanelEvaluation:
    """Evaluation result with metrics and validation errors."""

    case: CutPanelCase
    metrics: CutPanelMetrics
    errors: tuple[str, ...]
    topology: PanelValidationResult | None = None


def _normalize_loop(loop: Loop) -> Loop:
    if len(loop) >= 2 and loop[0] == loop[-1]:
        return loop[:-1]
    return loop


def signed_area(loop: Loop) -> float:
    """Return signed area from the shoelace formula."""

    normalized = _normalize_loop(loop)
    if len(normalized) < 3:
        return 0.0

    accum = 0.0
    for idx, (x0, y0) in enumerate(normalized):
        x1, y1 = normalized[(idx + 1) % len(normalized)]
        accum += x0 * y1 - x1 * y0
    return 0.5 * accum


def orientation(loop: Loop) -> str:
    """Return orientation label for one loop."""

    area = signed_area(loop)
    if area > 0.0:
        return "ccw"
    if area < 0.0:
        return "cw"
    return "degenerate"


def _bbox_area_from_loops(loops: tuple[Loop, ...]) -> float:
    bbox = _bbox_from_loops(loops)
    if bbox is None:
        return 0.0

    xmin, ymin, xmax, ymax = bbox
    return (xmax - xmin) * (ymax - ymin)


def _bbox_from_loops(
    loops: tuple[Loop, ...],
) -> tuple[float, float, float, float] | None:
    xmin = float("inf")
    ymin = float("inf")
    xmax = float("-inf")
    ymax = float("-inf")

    for loop in loops:
        for x, y in _normalize_loop(loop):
            xmin = min(xmin, x)
            ymin = min(ymin, y)
            xmax = max(xmax, x)
            ymax = max(ymax, y)

    if xmin == float("inf"):
        return None

    return (xmin, ymin, xmax, ymax)


def _to_trimmed_panel(case: CutPanelCase) -> TrimmedPanel2D:
    return TrimmedPanel2D(
        outer=PanelLoop2D(case.outer),
        holes=tuple(PanelLoop2D(hole) for hole in case.holes),
    )


def _loop_from_raw(raw_loop: object) -> Loop:
    if not isinstance(raw_loop, list):
        raise ValueError("loop must be a list of points")

    points: list[Point] = []
    for raw_point in raw_loop:
        if not isinstance(raw_point, list) or len(raw_point) != 2:
            raise ValueError("point must be a 2-item list")
        points.append((float(raw_point[0]), float(raw_point[1])))

    loop = PanelLoop2D(tuple(points)).points
    if abs(signed_area(loop)) <= _AREA_TOL:
        raise ValueError("loop must be non-degenerate")
    return loop


def _case_from_payload(payload: object, *, source: str) -> CutPanelCase:
    if not isinstance(payload, dict):
        raise ValueError("case payload must be an object")

    name_value = payload.get("name")
    if not isinstance(name_value, str) or not name_value:
        raise ValueError("case name must be a non-empty string")

    outer = _loop_from_raw(payload.get("outer"))
    holes_raw = payload.get("holes", [])
    if not isinstance(holes_raw, list):
        raise ValueError("holes must be a list")

    tags_raw = payload.get("tags", [])
    if not isinstance(tags_raw, list) or not all(
        isinstance(tag, str) for tag in tags_raw
    ):
        raise ValueError("tags must be a list of strings")

    holes = tuple(tuple(reversed(_loop_from_raw(raw_hole))) for raw_hole in holes_raw)
    return CutPanelCase(
        name=name_value,
        outer=outer,
        holes=holes,
        source=source,
        tags=tuple(tags_raw),
    )


def cases_from_fixture_payload(payload: object) -> tuple[CutPanelCase, ...]:
    """Parse fixture payload into cut-panel cases."""

    if not isinstance(payload, dict):
        raise ValueError("fixture payload must be an object")

    source_value = payload.get("source")
    if not isinstance(source_value, str) or not source_value:
        raise ValueError("fixture payload must define source")

    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list):
        raise ValueError("fixture payload must define cases list")

    return tuple(
        _case_from_payload(case_payload, source=source_value)
        for case_payload in cases_raw
    )


def case_to_fixture_payload(case: CutPanelCase) -> dict[str, object]:
    """Serialize one case to fixture-compatible payload."""

    return {
        "name": case.name,
        "tags": list(case.tags),
        "outer": _loop_to_json(case.outer),
        "holes": [_loop_to_json(tuple(reversed(hole))) for hole in case.holes],
    }


@lru_cache(maxsize=1)
def _load_fixture_cases(filename: str) -> tuple[CutPanelCase, ...]:
    fixture_path = files("cutkit.evals").joinpath("fixtures", filename)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    try:
        return cases_from_fixture_payload(payload)
    except ValueError as exc:
        raise ValueError(f"invalid fixture payload in {filename}: {exc}") from exc


def imported_production_cases() -> tuple[CutPanelCase, ...]:
    """Return imported-production cut-panel cases from fixture definitions."""

    return _load_fixture_cases("cutpanel-production-imported.json")


def fuzz_derived_cases() -> tuple[CutPanelCase, ...]:
    """Return deterministic fuzz-derived cut-panel cases from fixtures."""

    return _load_fixture_cases("cutpanel-fuzz-derived.json")


def _base_metrics(case: CutPanelCase) -> CutPanelMetrics:
    outer_area_abs = abs(signed_area(case.outer))
    hole_areas_abs = tuple(abs(signed_area(hole)) for hole in case.holes)
    area = outer_area_abs - sum(hole_areas_abs)

    bbox_area = _bbox_area_from_loops((case.outer, *case.holes))
    cut_fraction = area / bbox_area if bbox_area > 0.0 else 0.0

    return CutPanelMetrics(
        name=case.name,
        source=case.source,
        tags=case.tags,
        area=area,
        bbox_area=bbox_area,
        cut_fraction=cut_fraction,
        outer_orientation=orientation(case.outer),
        hole_orientations=tuple(orientation(hole) for hole in case.holes),
    )


def evaluate_case(case: CutPanelCase, *, folded_order: int = 6) -> CutPanelMetrics:
    """Compute baseline geometric metrics for one cut-panel case."""

    metrics = _base_metrics(case)

    folded = folded_quadrature_rule(_to_trimmed_panel(case), order=folded_order)
    area_diag = area_consistency(folded.panel, folded.triangles, folded.rule)
    moments = moment_report(folded.triangles, folded.rule)

    return CutPanelMetrics(
        name=metrics.name,
        source=metrics.source,
        tags=metrics.tags,
        area=metrics.area,
        bbox_area=metrics.bbox_area,
        cut_fraction=metrics.cut_fraction,
        outer_orientation=metrics.outer_orientation,
        hole_orientations=metrics.hole_orientations,
        folded_triangle_area=area_diag.triangle_area,
        folded_rule_area=area_diag.rule_area,
        folded_triangle_abs_error=area_diag.triangle_abs_error,
        folded_rule_abs_error=area_diag.rule_abs_error,
        folded_max_moment_abs_error=moments.max_abs_error,
    )


def _validate_case_with_topology(
    case: CutPanelCase,
    *,
    folded_area_tol: float = 1.0e-12,
    folded_moment_tol: float = 1.0e-10,
) -> tuple[tuple[str, ...], PanelValidationResult | None, CutPanelMetrics | None]:
    base_metrics = _base_metrics(case)

    errors: list[str] = []

    if base_metrics.outer_orientation != "ccw":
        errors.append("Outer loop must be oriented ccw.")

    for idx, hole_orientation in enumerate(base_metrics.hole_orientations):
        if hole_orientation != "cw":
            errors.append(f"Hole loop {idx} must be oriented cw.")

    if base_metrics.area <= 0.0:
        errors.append("Panel area must be positive.")

    if base_metrics.cut_fraction <= 0.0 or base_metrics.cut_fraction > 1.0:
        errors.append("Cut fraction must be in the interval (0, 1].")

    try:
        topology_report = validate_panel(_to_trimmed_panel(case))
    except ValueError as exc:
        errors.append(f"Topology: {exc}")
        return tuple(errors), None, None

    for topology_error in topology_report.errors:
        errors.append(f"Topology: {topology_error}")
    if topology_report.errors:
        return tuple(errors), topology_report, None

    try:
        metrics = evaluate_case(case)
    except ValueError:
        if not errors:
            errors.append("Folded diagnostics failed for panel geometry.")
        return tuple(errors), topology_report, None

    if metrics.folded_triangle_abs_error is None:
        errors.append("Folded triangle area diagnostics were not computed.")
    elif metrics.folded_triangle_abs_error > folded_area_tol:
        errors.append("Folded triangle area reconstruction error exceeds tolerance.")

    if metrics.folded_rule_abs_error is None:
        errors.append("Folded quadrature area diagnostics were not computed.")
    elif metrics.folded_rule_abs_error > folded_area_tol:
        errors.append("Folded quadrature area error exceeds tolerance.")

    if metrics.folded_max_moment_abs_error is None:
        errors.append("Folded moment diagnostics were not computed.")
    elif metrics.folded_max_moment_abs_error > folded_moment_tol:
        errors.append("Folded moment error exceeds tolerance.")

    return tuple(errors), topology_report, metrics


def validate_case(
    case: CutPanelCase,
    *,
    folded_area_tol: float = 1.0e-12,
    folded_moment_tol: float = 1.0e-10,
) -> tuple[str, ...]:
    """Validate one case against orientation and positivity invariants."""

    errors, _, _ = _validate_case_with_topology(
        case,
        folded_area_tol=folded_area_tol,
        folded_moment_tol=folded_moment_tol,
    )
    return errors


def default_cases() -> tuple[CutPanelCase, ...]:
    """Return baseline cut-panel cases used by CI and local evals."""

    hole_ccw: Loop = ((0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75))
    notch_hole_ccw: Loop = ((0.9, 0.45), (1.1, 0.45), (1.1, 0.55), (0.9, 0.55))
    seam_slot_hole_ccw: Loop = (
        (0.996, 0.2),
        (0.999, 0.2),
        (0.999, 0.8),
        (0.996, 0.8),
    )
    ultra_thin_frame_hole_ccw: Loop = (
        (0.003, 0.003),
        (0.997, 0.003),
        (0.997, 0.997),
        (0.003, 0.997),
    )

    base_cases = (
        CutPanelCase(
            name="unit-square",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            tags=("baseline",),
        ),
        CutPanelCase(
            name="square-with-hole",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(hole_ccw)),),
            tags=("baseline",),
        ),
        CutPanelCase(
            name="rect-with-thin-hole",
            outer=((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(notch_hole_ccw)),),
            tags=("baseline", "thin-feature"),
        ),
        CutPanelCase(
            name="square-with-seam-adjacent-slot",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(seam_slot_hole_ccw)),),
            tags=("baseline", "seam-adjacent"),
        ),
        CutPanelCase(
            name="square-with-ultra-thin-frame",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(ultra_thin_frame_hole_ccw)),),
            tags=("baseline", "near-degenerate"),
        ),
    )
    return (*base_cases, *imported_production_cases(), *fuzz_derived_cases())


def _quantized_point(point: Point, *, decimals: int = 6) -> Point:
    return (round(point[0], decimals), round(point[1], decimals))


def _canonicalize_loop(loop: Loop, *, decimals: int = 6) -> tuple[Point, ...]:
    normalized = tuple(_quantized_point(point, decimals=decimals) for point in loop)
    if not normalized:
        return ()

    def _rotations(points: tuple[Point, ...]) -> tuple[tuple[Point, ...], ...]:
        return tuple(points[index:] + points[:index] for index in range(len(points)))

    forward = _rotations(normalized)
    reversed_loop = tuple(reversed(normalized))
    backward = _rotations(reversed_loop)
    return min((*forward, *backward))


def _geometry_signature(case: CutPanelCase, *, decimals: int = 6) -> tuple[object, ...]:
    outer_sig = _canonicalize_loop(case.outer, decimals=decimals)
    holes_sig = tuple(
        sorted(_canonicalize_loop(hole, decimals=decimals) for hole in case.holes)
    )
    return (outer_sig, holes_sig)


def _loop_min_edge_length(loop: Loop) -> float:
    normalized = _normalize_loop(loop)
    if len(normalized) < 2:
        return 0.0
    return min(
        math.hypot(x1 - x0, y1 - y0)
        for (x0, y0), (x1, y1) in zip(normalized, normalized[1:] + normalized[:1])
    )


def _case_minimization_sort_key(
    case: CutPanelCase,
) -> tuple[float, float, float, float, str]:
    loops = (case.outer, *case.holes)
    total_vertices = sum(len(_normalize_loop(loop)) for loop in loops)
    min_edge = min(_loop_min_edge_length(loop) for loop in loops)
    cut_fraction = _base_metrics(case).cut_fraction
    return (
        -float(len(case.holes)),
        -float(total_vertices),
        min_edge,
        -abs(cut_fraction - 0.5),
        case.name,
    )


def minimize_fuzz_cases(
    cases: tuple[CutPanelCase, ...],
    *,
    max_cases: int,
    decimals: int = 6,
) -> tuple[CutPanelCase, ...]:
    """Return deterministic minimized subset from fuzz-derived cases."""

    if max_cases <= 0:
        raise ValueError("max_cases must be positive")
    if decimals < 0:
        raise ValueError("decimals must be non-negative")

    ranked_cases = sorted(cases, key=_case_minimization_sort_key)
    deduplicated: dict[tuple[object, ...], CutPanelCase] = {}
    for case in ranked_cases:
        signature = _geometry_signature(case, decimals=decimals)
        deduplicated.setdefault(signature, case)

    selected = list(deduplicated.values())[:max_cases]
    return tuple(sorted(selected, key=lambda case: case.name))


def _signed_region_membership(point: Point, case: CutPanelCase) -> bool:
    winding = 0

    outer_sign = orientation(case.outer)
    if outer_sign != "degenerate" and point_in_loop(
        point, case.outer, include_boundary=False
    ):
        winding += 1 if outer_sign == "ccw" else -1

    for hole in case.holes:
        hole_sign = orientation(hole)
        if hole_sign == "degenerate":
            continue
        if point_in_loop(point, hole, include_boundary=False):
            winding += 1 if hole_sign == "ccw" else -1

    return winding > 0


def _visual_diff_snapshot(
    case: CutPanelCase,
    *,
    width: int = _VISUAL_SNAPSHOT_WIDTH,
    height: int = _VISUAL_SNAPSHOT_HEIGHT,
) -> dict[str, object]:
    bbox = _bbox_from_loops((case.outer, *case.holes))
    if bbox is None:
        return {
            "grid": {"width": width, "height": height},
            "legend": {
                "#": "both-filled",
                ".": "both-empty",
                "+": "parity-only",
                "-": "signed-only",
            },
            "counts": {
                "both_filled": 0,
                "both_empty": width * height,
                "parity_only": 0,
                "signed_only": 0,
                "mismatch_total": 0,
            },
            "rows": tuple("." * width for _ in range(height)),
        }

    xmin, ymin, xmax, ymax = bbox
    if math.isclose(xmin, xmax):
        xmin -= 0.5
        xmax += 0.5
    if math.isclose(ymin, ymax):
        ymin -= 0.5
        ymax += 0.5

    panel = _to_trimmed_panel(case)
    x_step = (xmax - xmin) / float(width)
    y_step = (ymax - ymin) / float(height)

    both_filled = 0
    both_empty = 0
    parity_only = 0
    signed_only = 0
    rows: list[str] = []

    for y_index in reversed(range(height)):
        y_coord = ymin + (y_index + 0.5) * y_step
        chars: list[str] = []
        for x_index in range(width):
            x_coord = xmin + (x_index + 0.5) * x_step
            point = (x_coord, y_coord)

            parity_inside = point_in_panel(point, panel, include_boundary=False)
            signed_inside = _signed_region_membership(point, case)

            if parity_inside and signed_inside:
                chars.append("#")
                both_filled += 1
            elif not parity_inside and not signed_inside:
                chars.append(".")
                both_empty += 1
            elif parity_inside:
                chars.append("+")
                parity_only += 1
            else:
                chars.append("-")
                signed_only += 1
        rows.append("".join(chars))

    return {
        "grid": {"width": width, "height": height},
        "legend": {
            "#": "both-filled",
            ".": "both-empty",
            "+": "parity-only",
            "-": "signed-only",
        },
        "counts": {
            "both_filled": both_filled,
            "both_empty": both_empty,
            "parity_only": parity_only,
            "signed_only": signed_only,
            "mismatch_total": parity_only + signed_only,
        },
        "rows": tuple(rows),
    }


def _slugify_case_name(name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug or "case"


def _loop_to_json(loop: Loop) -> list[list[float]]:
    return [[x, y] for x, y in loop]


def _topology_to_json(
    topology: PanelValidationResult | None,
) -> dict[str, object] | None:
    if topology is None:
        return None

    return {
        "errors": list(topology.errors),
        "diagnostics": asdict(topology.diagnostics),
    }


def export_failure_artifacts(
    evaluations: tuple[CutPanelEvaluation, ...],
    *,
    output_dir: Path,
) -> tuple[Path, ...]:
    """Write JSON artifacts for each failed cut-panel evaluation case."""

    output_dir.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []

    for index, result in enumerate(evaluations):
        if not result.errors:
            continue

        payload = {
            "schema_version": 1,
            "case": {
                "name": result.case.name,
                "source": result.case.source,
                "tags": list(result.case.tags),
                "outer": _loop_to_json(result.case.outer),
                "holes": [_loop_to_json(hole) for hole in result.case.holes],
            },
            "metrics": asdict(result.metrics),
            "errors": list(result.errors),
            "topology": _topology_to_json(result.topology),
            "visual_diff": _visual_diff_snapshot(result.case),
        }

        artifact_name = f"{index:02d}-{_slugify_case_name(result.case.name)}.json"
        artifact_path = output_dir / artifact_name
        artifact_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        written.append(artifact_path)

    return tuple(written)


def run_default_eval() -> tuple[CutPanelEvaluation, ...]:
    """Evaluate all default cases and return metrics with error lists."""

    results: list[CutPanelEvaluation] = []
    for case in default_cases():
        errors, topology, metrics = _validate_case_with_topology(case)
        if metrics is None:
            metrics = _base_metrics(case)
        results.append(
            CutPanelEvaluation(
                case=case, metrics=metrics, errors=errors, topology=topology
            )
        )
    return tuple(results)
