from __future__ import annotations

import json
from pathlib import Path

import pytest

import cutkit.evals.cutpanel as cutpanel_module
from cutkit.evals import (
    CutPanelCase,
    CutPanelEvaluation,
    CutPanelMetrics,
    default_cases,
    evaluate_case,
    export_failure_artifacts,
    fuzz_derived_cases,
    imported_production_cases,
    run_default_eval,
    validate_case,
)
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.topology import validate_panel


def test_default_eval_cases_pass() -> None:
    results = run_default_eval()
    assert results
    assert all(not result.errors for result in results)


def test_default_cases_include_seam_and_near_degenerate_entries() -> None:
    names = {case.name for case in default_cases()}
    assert "square-with-seam-adjacent-slot" in names
    assert "square-with-ultra-thin-frame" in names


def test_default_cases_include_imported_and_fuzz_entries() -> None:
    sources = {case.source for case in default_cases()}
    assert "imported-production" in sources
    assert "fuzz-derived" in sources


def test_imported_and_fuzz_case_groups_are_non_empty() -> None:
    assert imported_production_cases()
    assert fuzz_derived_cases()


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


@pytest.mark.parametrize(
    ("case_name", "expected_area"),
    (
        ("square-with-seam-adjacent-slot", 0.9982),
        ("square-with-ultra-thin-frame", 0.011964),
    ),
)
def test_expanded_corpus_case_metrics(case_name: str, expected_area: float) -> None:
    case = next(case for case in default_cases() if case.name == case_name)
    metrics = evaluate_case(case)

    assert metrics.area == pytest.approx(expected_area, rel=1.0e-12, abs=1.0e-12)
    assert metrics.outer_orientation == "ccw"
    assert metrics.hole_orientations == ("cw",)
    assert metrics.folded_rule_abs_error is not None
    assert metrics.folded_max_moment_abs_error is not None
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


def test_validate_case_rejects_hole_outside_outer_topology() -> None:
    case = CutPanelCase(
        name="hole-outside",
        outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        holes=(((2.0, 2.2), (2.2, 2.2), (2.2, 2.0), (2.0, 2.0)),),
    )

    errors = validate_case(case)
    assert any("Topology:" in error for error in errors)
    assert any(
        "hole 0 must lie strictly inside outer loop" in error for error in errors
    )


def test_validate_case_rejects_hole_touching_outer_seam() -> None:
    case = CutPanelCase(
        name="hole-touching-seam",
        outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        holes=(((0.95, 0.8), (1.0, 0.8), (1.0, 0.2), (0.95, 0.2)),),
    )

    errors = validate_case(case)
    assert any("Topology:" in error for error in errors)
    assert any(
        "hole 0 must lie strictly inside outer loop" in error for error in errors
    )
    assert any("hole 0 intersects outer loop boundary" in error for error in errors)


def test_export_failure_artifacts_include_topology_diagnostics(
    tmp_path: Path,
) -> None:
    case = CutPanelCase(
        name="artifact-export-invalid-hole-orientation",
        outer=((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)),
        holes=(((0.2, 0.2), (0.8, 0.2), (0.8, 0.8), (0.2, 0.8)),),
        source="unit-test",
        tags=("artifact",),
    )
    metrics = evaluate_case(case)
    errors = validate_case(case)
    topology = validate_panel(
        TrimmedPanel2D(
            outer=PanelLoop2D(case.outer),
            holes=tuple(PanelLoop2D(hole) for hole in case.holes),
        )
    )

    evaluation = CutPanelEvaluation(
        case=case,
        metrics=metrics,
        errors=errors,
        topology=topology,
    )
    artifacts = export_failure_artifacts(
        (evaluation,),
        output_dir=tmp_path / "cutpanel-artifacts",
    )

    assert len(artifacts) == 1
    payload = json.loads(artifacts[0].read_text(encoding="utf-8"))
    assert payload["case"]["name"] == case.name
    assert payload["case"]["source"] == "unit-test"
    assert payload["errors"]
    assert payload["topology"]["diagnostics"]["outer"]["orientation"] == "ccw"


def test_fixture_case_payload_rejects_degenerate_outer_loop() -> None:
    payload = {
        "name": "degenerate-loop",
        "outer": [[0.0, 0.0], [0.5, 0.5], [1.0, 1.0]],
        "holes": [],
        "tags": [],
    }

    with pytest.raises(ValueError, match="non-degenerate"):
        cutpanel_module._case_from_payload(payload, source="unit-test")


def test_run_default_eval_does_not_call_evaluate_for_topology_invalid_case(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = CutPanelCase(
        name="degenerate-topology-only",
        outer=((0.0, 0.0), (0.5, 0.5), (1.0, 1.0)),
        source="unit-test",
    )

    monkeypatch.setattr(cutpanel_module, "default_cases", lambda: (case,))

    def _should_not_run(*_args: object, **_kwargs: object) -> CutPanelMetrics:
        raise AssertionError("evaluate_case should not run for topology-invalid case")

    monkeypatch.setattr(cutpanel_module, "evaluate_case", _should_not_run)

    results = cutpanel_module.run_default_eval()
    assert len(results) == 1
    assert results[0].errors
    assert any("Topology:" in error for error in results[0].errors)
