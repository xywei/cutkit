"""Manifest and parity helpers for Antolin Section 6 reproductions."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any


@dataclass(frozen=True)
class ParityFailure:
    """One out-of-tolerance parity mismatch."""

    key: str
    current: float
    expected: float
    abs_diff: float
    rel_diff: float
    abs_tol: float
    rel_tol: float
    tolerance_bound: float


@dataclass(frozen=True)
class ParityReport:
    """Parity check result across all comparable manifest metrics."""

    passed: bool
    failures: tuple[ParityFailure, ...]
    checked_keys: int
    skipped_reason: str | None = None


def _collect_numeric_metrics(obj: Any, *, prefix: str = "") -> dict[str, float]:
    metrics: dict[str, float] = {}

    if isinstance(obj, dict):
        for key in sorted(obj):
            value = obj[key]
            if key in {"schema_version", "cad_available", "requires_cad"}:
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            metrics.update(_collect_numeric_metrics(value, prefix=child_prefix))
        return metrics

    if isinstance(obj, list):
        for index, value in enumerate(obj):
            child_prefix = f"{prefix}[{index}]"
            metrics.update(_collect_numeric_metrics(value, prefix=child_prefix))
        return metrics

    if isinstance(obj, bool):
        return metrics

    if isinstance(obj, (int, float)):
        value = float(obj)
        if isfinite(value):
            metrics[prefix] = value
        return metrics

    return metrics


def compare_manifest_to_fixture(
    current: dict[str, Any],
    fixture: dict[str, Any],
    *,
    abs_tol: float,
    rel_tol: float,
) -> ParityReport:
    """Compare numeric metrics in `current` against `fixture`."""

    requires_cad = bool(fixture.get("requires_cad", False))
    if requires_cad and not bool(current.get("cad_available", False)):
        return ParityReport(
            passed=True,
            failures=(),
            checked_keys=0,
            skipped_reason=(
                "fixture requires CAD-native mode but OpenCascade is unavailable"
            ),
        )

    current_metrics = _collect_numeric_metrics(current)
    fixture_metrics = _collect_numeric_metrics(fixture)

    failures: list[ParityFailure] = []

    for key in sorted(fixture_metrics):
        if key not in current_metrics:
            failures.append(
                ParityFailure(
                    key=key,
                    current=float("nan"),
                    expected=fixture_metrics[key],
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=abs_tol,
                    rel_tol=rel_tol,
                    tolerance_bound=float("inf"),
                )
            )
            continue

        current_value = current_metrics[key]
        expected_value = fixture_metrics[key]
        abs_diff = abs(current_value - expected_value)
        scale = max(abs(expected_value), abs(current_value), 1.0)
        rel_diff = abs_diff / scale
        tolerance = max(abs_tol, rel_tol * scale)
        if abs_diff > tolerance:
            failures.append(
                ParityFailure(
                    key=key,
                    current=current_value,
                    expected=expected_value,
                    abs_diff=abs_diff,
                    rel_diff=rel_diff,
                    abs_tol=abs_tol,
                    rel_tol=rel_tol,
                    tolerance_bound=tolerance,
                )
            )

    for key in sorted(current_metrics):
        if key not in fixture_metrics:
            failures.append(
                ParityFailure(
                    key=key,
                    current=current_metrics[key],
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=abs_tol,
                    rel_tol=rel_tol,
                    tolerance_bound=float("inf"),
                )
            )

    return ParityReport(
        passed=not failures,
        failures=tuple(failures),
        checked_keys=len(set(current_metrics) & set(fixture_metrics)),
        skipped_reason=None,
    )


def format_parity_report(report: ParityReport) -> str:
    """Render a concise human-readable parity report."""

    if report.skipped_reason is not None:
        return f"PARITY SKIPPED: {report.skipped_reason}"

    if report.passed:
        return f"PARITY PASS: compared {report.checked_keys} numeric metrics"

    lines = [
        (
            "PARITY FAIL: "
            f"{len(report.failures)} mismatches across {report.checked_keys} checked metrics"
        )
    ]
    for failure in report.failures[:20]:
        lines.append(
            "- "
            f"{failure.key}: current={failure.current:.12e}, "
            f"expected={failure.expected:.12e}, "
            f"abs_diff={failure.abs_diff:.3e}, rel_diff={failure.rel_diff:.3e}, "
            f"bound={failure.tolerance_bound:.3e}, "
            f"abs_tol={failure.abs_tol:.3e}, rel_tol={failure.rel_tol:.3e}"
        )
    if len(report.failures) > 20:
        lines.append(f"- ... {len(report.failures) - 20} more mismatches")
    return "\n".join(lines)
