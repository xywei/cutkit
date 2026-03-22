from __future__ import annotations

import json
from pathlib import Path

import pytest

from cutkit.evals import compare_manifest_to_fixture, format_parity_report


def test_compare_manifest_to_fixture_passes_within_tolerance() -> None:
    current = {
        "schema_version": 1,
        "cad_available": False,
        "requires_cad": False,
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
    text = format_parity_report(report)
    assert "PARITY FAIL" in text
    assert "abs_tol=" in text
    assert "rel_tol=" in text
    assert "bound=" in text


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


def test_compare_manifest_to_fixture_fails_on_metadata_mismatch() -> None:
    current = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "cad-native",
        "numpy_acceleration": False,
        "sections": {"2d": {"value": 1.0}},
    }
    fixture = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "polygonized",
        "numpy_acceleration": False,
        "sections": {"2d": {"value": 1.0}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert not report.passed
    assert report.checked_keys == 0
    text = format_parity_report(report)
    assert "meta.geometry_mode" in text


def test_compare_manifest_to_fixture_ignores_numpy_availability_metadata() -> None:
    current = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "polygonized",
        "numpy_acceleration": True,
        "sections": {"2d": {"value": 1.0}},
    }
    fixture = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "polygonized",
        "numpy_acceleration": False,
        "sections": {"2d": {"value": 1.0}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert report.passed
    assert report.checked_keys == 1


def test_compare_manifest_to_fixture_allows_superset_metrics_for_2d_only() -> None:
    current = {
        "schema_version": 1,
        "profile": "antolin-paper",
        "geometry_mode": "polygonized",
        "numpy_acceleration": True,
        "sections": {
            "2d": {"value": 1.0},
            "3d": {"value": 2.0},
        },
    }
    fixture = {
        "schema_version": 1,
        "profile": "antolin-paper",
        "geometry_mode": "polygonized",
        "numpy_acceleration": True,
        "scope": "2d-only",
        "sections": {
            "2d": {"value": 1.0},
        },
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert report.passed
    assert report.checked_keys == 1


def test_compare_manifest_to_fixture_rejects_truncated_full_scope() -> None:
    current = {
        "schema_version": 1,
        "profile": "antolin-paper",
        "geometry_mode": "polygonized",
        "sections": {
            "2d": {"value": 1.0},
            "3d": {"value": 2.0},
        },
    }
    fixture = {
        "schema_version": 1,
        "profile": "antolin-paper",
        "geometry_mode": "polygonized",
        "scope": "full",
        "sections": {
            "2d": {"value": 1.0},
        },
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert not report.passed
    assert report.checked_keys == 1
    assert any(
        failure.key.endswith("sections.3d.value") and failure.detail is not None
        for failure in report.failures
    )


def test_compare_manifest_to_fixture_skips_placeholder_without_numeric_metrics() -> (
    None
):
    current = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "cad-native",
        "requires_cad": True,
        "cad_available": True,
        "sections": {"2d": {"value": 1.0}},
    }
    fixture = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "cad-native",
        "requires_cad": True,
        "placeholder": True,
        "sections": {"2d": {"status": "unavailable"}},
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


def test_compare_manifest_to_fixture_fails_empty_non_placeholder_fixture() -> None:
    current = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "polygonized",
        "sections": {"2d": {"value": 1.0}},
    }
    fixture = {
        "schema_version": 1,
        "profile": "quick",
        "geometry_mode": "polygonized",
        "sections": {"2d": {"status": "missing"}},
    }

    report = compare_manifest_to_fixture(
        current,
        fixture,
        abs_tol=1.0e-12,
        rel_tol=1.0e-12,
    )
    assert not report.passed
    assert report.checked_keys == 0
    text = format_parity_report(report)
    assert "sections.2d.value" in text


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


@pytest.mark.parametrize(
    "fixture_name",
    (
        "quick-polygonized-full.json",
        "quick-cad-native-full.json",
        "antolin-paper-polygonized-2d-only.json",
        "antolin-paper-cad-native-2d-only.json",
    ),
)
def test_mode_profile_fixtures_exist(fixture_name: str) -> None:
    fixture_path = (
        Path(__file__).resolve().parents[1]
        / "fixtures"
        / "antolin-section6"
        / fixture_name
    )
    assert fixture_path.exists()
