from __future__ import annotations

import json
from pathlib import Path

from cutkit.evals import compare_manifest_to_fixture, format_parity_report


def test_compare_manifest_to_fixture_passes_within_tolerance() -> None:
    current = {
        "schema_version": 1,
        "cad_available": False,
        "sections": {"2d": {"value": 1.0000000001}},
    }
    fixture = {
        "schema_version": 1,
        "requires_cad": False,
        "sections": {"2d": {"value": 1.0}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-9,
        rel_tol=1.0e-8,
    )
    assert report.passed
    assert report.failures == ()
    assert report.checked_keys == 1


def test_compare_manifest_to_fixture_reports_mismatches() -> None:
    current = {
        "sections": {"2d": {"value": 1.5}},
    }
    fixture = {
        "sections": {"2d": {"value": 1.0}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert not report.passed
    assert len(report.failures) == 1
    assert report.failures[0].key.endswith("sections.2d.value")
    assert "PARITY FAIL" in format_parity_report(report)


def test_compare_manifest_to_fixture_skips_unavailable_cad_mode() -> None:
    current = {
        "cad_available": False,
        "sections": {"2d": {"value": 1.0}},
    }
    fixture = {
        "requires_cad": True,
        "sections": {"2d": {"value": 1.0}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert report.passed
    assert report.checked_keys == 0
    assert report.skipped_reason is not None
    assert "PARITY SKIPPED" in format_parity_report(report)


def test_fixture_self_compare_passes() -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "antolin-section6"
        / "quick-polygonized-full.json"
    )
    fixture = json.loads(fixture_path.read_text(encoding="utf-8"))

    report = compare_manifest_to_fixture(
        fixture,
        fixture,
        abs_tol=1.0e-14,
        rel_tol=1.0e-14,
    )
    assert report.passed
