"""Manifest and parity helpers for Antolin Section 6 reproductions."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Any

_PARITY_METADATA_KEYS = (
    "schema_version",
    "profile",
    "geometry_mode",
    "requires_cad",
)
_NUMERIC_EXCLUDED_KEYS = set(_PARITY_METADATA_KEYS) | {
    "cad_available",
    "numpy_acceleration",
    "scope",
    "placeholder",
}
_EXACT_MATCH_KEYS = {
    "monotone_nonincreasing",
    "monotonicity_violation_indices",
}


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
    detail: str | None = None


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
            if key in _NUMERIC_EXCLUDED_KEYS:
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


def _metadata_failures(
    current: dict[str, Any], fixture: dict[str, Any]
) -> list[ParityFailure]:
    failures: list[ParityFailure] = []
    for key in _PARITY_METADATA_KEYS:
        if key not in fixture:
            continue
        if key not in current:
            failures.append(
                ParityFailure(
                    key=f"meta.{key}",
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail=(
                        f"missing key in current manifest; expected {key}={fixture[key]!r}"
                    ),
                )
            )
            continue
        if current[key] != fixture[key]:
            failures.append(
                ParityFailure(
                    key=f"meta.{key}",
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail=(
                        f"metadata mismatch: current={current[key]!r}, "
                        f"expected={fixture[key]!r}"
                    ),
                )
            )
    return failures


def _collect_exact_metrics(obj: Any, *, prefix: str = "") -> dict[str, Any]:
    metrics: dict[str, Any] = {}

    if isinstance(obj, dict):
        for key in sorted(obj):
            value = obj[key]
            if key in _NUMERIC_EXCLUDED_KEYS:
                continue
            child_prefix = f"{prefix}.{key}" if prefix else str(key)
            if key in _EXACT_MATCH_KEYS:
                metrics[child_prefix] = value
                continue
            metrics.update(_collect_exact_metrics(value, prefix=child_prefix))
        return metrics

    if isinstance(obj, list):
        for index, value in enumerate(obj):
            child_prefix = f"{prefix}[{index}]"
            metrics.update(_collect_exact_metrics(value, prefix=child_prefix))
        return metrics

    return metrics


def _normalize_exact_value(value: Any) -> Any:
    if isinstance(value, list):
        return tuple(_normalize_exact_value(item) for item in value)
    return value


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

    metadata_failures = _metadata_failures(current, fixture)
    if metadata_failures:
        return ParityReport(
            passed=False,
            failures=tuple(metadata_failures),
            checked_keys=0,
            skipped_reason=None,
        )

    current_metrics = _collect_numeric_metrics(current)
    fixture_metrics = _collect_numeric_metrics(fixture)
    current_exact_metrics = _collect_exact_metrics(current)
    fixture_exact_metrics = _collect_exact_metrics(fixture)
    fixture_scope = str(fixture.get("scope", "full"))
    is_placeholder = bool(fixture.get("placeholder", False))

    if fixture_scope not in {"full", "2d-only"}:
        return ParityReport(
            passed=False,
            failures=(
                ParityFailure(
                    key="meta.scope",
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail=f"invalid fixture scope: {fixture_scope!r}",
                ),
            ),
            checked_keys=0,
            skipped_reason=None,
        )

    failures: list[ParityFailure] = []

    if fixture_scope == "full" and not (
        is_placeholder and not fixture_metrics and not fixture_exact_metrics
    ):
        for key in sorted(current_metrics):
            if key in fixture_metrics:
                continue
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
                    detail="missing key in fixture for scope=full",
                )
            )
        for key in sorted(current_exact_metrics):
            if key in fixture_exact_metrics:
                continue
            failures.append(
                ParityFailure(
                    key=key,
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail="missing exact-match key in fixture for scope=full",
                )
            )

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
        scale = max(abs(expected_value), abs(current_value))
        rel_diff = abs_diff / scale if scale > 0.0 else 0.0
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

    for key in sorted(fixture_exact_metrics):
        if key not in current_exact_metrics:
            failures.append(
                ParityFailure(
                    key=key,
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail="missing key in current manifest",
                )
            )
            continue

        current_value = _normalize_exact_value(current_exact_metrics[key])
        expected_value = _normalize_exact_value(fixture_exact_metrics[key])
        if current_value != expected_value:
            failures.append(
                ParityFailure(
                    key=key,
                    current=float("nan"),
                    expected=float("nan"),
                    abs_diff=float("inf"),
                    rel_diff=float("inf"),
                    abs_tol=0.0,
                    rel_tol=0.0,
                    tolerance_bound=0.0,
                    detail=(
                        f"exact mismatch: current={current_value!r}, "
                        f"expected={expected_value!r}"
                    ),
                )
            )

    checked_keys = len(set(current_metrics) & set(fixture_metrics)) + len(
        set(current_exact_metrics) & set(fixture_exact_metrics)
    )
    if not failures and checked_keys == 0:
        if not bool(fixture.get("placeholder", False)):
            return ParityReport(
                passed=False,
                failures=(
                    ParityFailure(
                        key="meta.placeholder",
                        current=float("nan"),
                        expected=float("nan"),
                        abs_diff=float("inf"),
                        rel_diff=float("inf"),
                        abs_tol=0.0,
                        rel_tol=0.0,
                        tolerance_bound=0.0,
                        detail=(
                            "fixture contains no numeric metrics; set "
                            "placeholder=true only for intentional placeholder baselines"
                        ),
                    ),
                ),
                checked_keys=0,
                skipped_reason=None,
            )
        return ParityReport(
            passed=True,
            failures=(),
            checked_keys=0,
            skipped_reason=(
                "fixture contains no numeric metrics to compare; "
                "treating as placeholder baseline"
            ),
        )

    return ParityReport(
        passed=not failures,
        failures=tuple(failures),
        checked_keys=checked_keys,
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
        if failure.detail is not None:
            lines.append(f"- {failure.key}: {failure.detail}")
            continue
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
