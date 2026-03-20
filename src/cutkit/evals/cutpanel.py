"""Cut-panel evaluation harness for baseline geometric invariants."""

from __future__ import annotations

from dataclasses import dataclass

from cutkit.diagnostics import area_consistency, moment_report
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.quadrature import folded_quadrature_rule

Point = tuple[float, float]
Loop = tuple[Point, ...]


@dataclass(frozen=True)
class CutPanelCase:
    """Parametric-space cut-panel case with one outer loop and optional holes."""

    name: str
    outer: Loop
    holes: tuple[Loop, ...] = ()


@dataclass(frozen=True)
class CutPanelMetrics:
    """Computed metrics for one cut-panel case."""

    name: str
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

    metrics: CutPanelMetrics
    errors: tuple[str, ...]


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


def evaluate_case(case: CutPanelCase, *, folded_order: int = 6) -> CutPanelMetrics:
    """Compute baseline geometric metrics for one cut-panel case."""

    outer_area_abs = abs(signed_area(case.outer))
    hole_areas_abs = tuple(abs(signed_area(hole)) for hole in case.holes)
    area = outer_area_abs - sum(hole_areas_abs)

    bbox_area = _bbox_area_from_loops((case.outer, *case.holes))
    cut_fraction = area / bbox_area if bbox_area > 0.0 else 0.0

    metrics = CutPanelMetrics(
        name=case.name,
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


def validate_case(
    case: CutPanelCase,
    *,
    folded_area_tol: float = 1.0e-12,
    folded_moment_tol: float = 1.0e-10,
) -> tuple[str, ...]:
    """Validate one case against orientation and positivity invariants."""

    metrics = evaluate_case(case)
    errors: list[str] = []

    if metrics.outer_orientation != "ccw":
        errors.append("Outer loop must be oriented ccw.")

    for idx, hole_orientation in enumerate(metrics.hole_orientations):
        if hole_orientation != "cw":
            errors.append(f"Hole loop {idx} must be oriented cw.")

    if metrics.area <= 0.0:
        errors.append("Panel area must be positive.")

    if metrics.cut_fraction <= 0.0 or metrics.cut_fraction > 1.0:
        errors.append("Cut fraction must be in the interval (0, 1].")

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

    return tuple(errors)


def default_cases() -> tuple[CutPanelCase, ...]:
    """Return baseline cut-panel cases used by CI and local evals."""

    hole_ccw: Loop = ((0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75))
    notch_hole_ccw: Loop = ((0.9, 0.45), (1.1, 0.45), (1.1, 0.55), (0.9, 0.55))

    return (
        CutPanelCase(
            name="unit-square",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        ),
        CutPanelCase(
            name="square-with-hole",
            outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(hole_ccw)),),
        ),
        CutPanelCase(
            name="rect-with-thin-hole",
            outer=((0.0, 0.0), (2.0, 0.0), (2.0, 1.0), (0.0, 1.0)),
            holes=(tuple(reversed(notch_hole_ccw)),),
        ),
    )


def run_default_eval() -> tuple[CutPanelEvaluation, ...]:
    """Evaluate all default cases and return metrics with error lists."""

    results: list[CutPanelEvaluation] = []
    for case in default_cases():
        metrics = evaluate_case(case)
        errors = validate_case(case)
        results.append(CutPanelEvaluation(metrics=metrics, errors=errors))
    return tuple(results)
