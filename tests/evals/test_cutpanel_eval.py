from __future__ import annotations

import pytest

from cutkit.evals import (
    CutPanelCase,
    default_cases,
    evaluate_case,
    run_default_eval,
    validate_case,
)


def test_default_eval_cases_pass() -> None:
    results = run_default_eval()
    assert results
    assert all(not result.errors for result in results)


def test_square_with_hole_metrics() -> None:
    case = next(case for case in default_cases() if case.name == "square-with-hole")
    metrics = evaluate_case(case)

    assert metrics.area == pytest.approx(0.75)
    assert metrics.cut_fraction == pytest.approx(0.75)
    assert metrics.outer_orientation == "ccw"
    assert metrics.hole_orientations == ("cw",)
    assert metrics.folded_triangle_abs_error is not None
    assert metrics.folded_rule_abs_error is not None
    assert metrics.folded_max_moment_abs_error is not None
    assert metrics.folded_triangle_abs_error < 1.0e-12
    assert metrics.folded_rule_abs_error < 1.0e-12
    assert metrics.folded_max_moment_abs_error < 1.0e-10


def test_orientation_violations_are_reported() -> None:
    case = CutPanelCase(
        name="bad-hole-orientation",
        outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        holes=(((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)),),
    )

    errors = validate_case(case)
    assert any("Hole loop" in error for error in errors)


def test_validate_case_reports_invalid_area_without_raising() -> None:
    case = CutPanelCase(
        name="zero-area-hole-cancel",
        outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        holes=(((0.0, 1.0), (1.0, 1.0), (1.0, 0.0), (0.0, 0.0)),),
    )

    errors = validate_case(case)
    assert "Panel area must be positive." in errors
