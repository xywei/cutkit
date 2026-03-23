"""Cut-panel evaluation harness for baseline geometric invariants."""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from functools import lru_cache
from importlib.resources import files
from pathlib import Path
import re

from cutkit.diagnostics import area_consistency, moment_report
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.quadrature import folded_quadrature_rule
from cutkit.topology import PanelValidationResult, validate_panel

Point = tuple[float, float]
Loop = tuple[Point, ...]


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
        return 0.0

    return (xmax - xmin) * (ymax - ymin)


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
    return tuple(points)


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


@lru_cache(maxsize=1)
def _load_fixture_cases(filename: str) -> tuple[CutPanelCase, ...]:
    fixture_path = files("cutkit.evals").joinpath("fixtures", filename)
    payload = json.loads(fixture_path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"invalid fixture payload in {filename}")

    source_value = payload.get("source")
    if not isinstance(source_value, str) or not source_value:
        raise ValueError(f"fixture {filename} must define source")

    cases_raw = payload.get("cases")
    if not isinstance(cases_raw, list):
        raise ValueError(f"fixture {filename} must define cases list")

    return tuple(
        _case_from_payload(case_payload, source=source_value)
        for case_payload in cases_raw
    )


def imported_production_cases() -> tuple[CutPanelCase, ...]:
    """Return imported-production cut-panel cases from fixture definitions."""

    return _load_fixture_cases("cutpanel-production-imported.json")


def fuzz_derived_cases() -> tuple[CutPanelCase, ...]:
    """Return deterministic fuzz-derived cut-panel cases from fixtures."""

    return _load_fixture_cases("cutpanel-fuzz-derived.json")


def evaluate_case(case: CutPanelCase, *, folded_order: int = 6) -> CutPanelMetrics:
    """Compute baseline geometric metrics for one cut-panel case."""

    outer_area_abs = abs(signed_area(case.outer))
    hole_areas_abs = tuple(abs(signed_area(hole)) for hole in case.holes)
    area = outer_area_abs - sum(hole_areas_abs)

    bbox_area = _bbox_area_from_loops((case.outer, *case.holes))
    cut_fraction = area / bbox_area if bbox_area > 0.0 else 0.0

    metrics = CutPanelMetrics(
        name=case.name,
        source=case.source,
        tags=case.tags,
        area=area,
        bbox_area=bbox_area,
        cut_fraction=cut_fraction,
        outer_orientation=orientation(case.outer),
        hole_orientations=tuple(orientation(hole) for hole in case.holes),
    )

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
) -> tuple[tuple[str, ...], PanelValidationResult]:
    outer_area_abs = abs(signed_area(case.outer))
    hole_areas_abs = tuple(abs(signed_area(hole)) for hole in case.holes)
    area = outer_area_abs - sum(hole_areas_abs)
    bbox_area = _bbox_area_from_loops((case.outer, *case.holes))
    cut_fraction = area / bbox_area if bbox_area > 0.0 else 0.0
    outer_orientation = orientation(case.outer)
    hole_orientations = tuple(orientation(hole) for hole in case.holes)

    errors: list[str] = []

    if outer_orientation != "ccw":
        errors.append("Outer loop must be oriented ccw.")

    for idx, hole_orientation in enumerate(hole_orientations):
        if hole_orientation != "cw":
            errors.append(f"Hole loop {idx} must be oriented cw.")

    if area <= 0.0:
        errors.append("Panel area must be positive.")

    if cut_fraction <= 0.0 or cut_fraction > 1.0:
        errors.append("Cut fraction must be in the interval (0, 1].")

    topology_report = validate_panel(_to_trimmed_panel(case))
    for topology_error in topology_report.errors:
        errors.append(f"Topology: {topology_error}")
    if topology_report.errors:
        return tuple(errors), topology_report

    try:
        metrics = evaluate_case(case)
    except ValueError:
        if not errors:
            errors.append("Folded diagnostics failed for panel geometry.")
        return tuple(errors), topology_report

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

    return tuple(errors), topology_report


def validate_case(
    case: CutPanelCase,
    *,
    folded_area_tol: float = 1.0e-12,
    folded_moment_tol: float = 1.0e-10,
) -> tuple[str, ...]:
    """Validate one case against orientation and positivity invariants."""

    errors, _ = _validate_case_with_topology(
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
        metrics = evaluate_case(case)
        errors, topology = _validate_case_with_topology(case)
        results.append(
            CutPanelEvaluation(
                case=case, metrics=metrics, errors=errors, topology=topology
            )
        )
    return tuple(results)
