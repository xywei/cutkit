#!/usr/bin/env python3
"""Run the default cut-panel evaluation suite."""

from __future__ import annotations

from cutkit.evals import run_default_eval


def main() -> int:
    results = run_default_eval()
    failures = []

    print("name | area | cut_fraction | status")
    print("--- | --- | --- | ---")
    for result in results:
        metrics = result.metrics
        status = "PASS" if not result.errors else "FAIL"
        print(
            f"{metrics.name} | {metrics.area:.6f} | {metrics.cut_fraction:.6f} | {status}"
        )
        if result.errors:
            failures.append(result)

    if not failures:
        print("Cut-panel evaluation passed.")
        return 0

    print("Cut-panel evaluation failed:")
    for result in failures:
        print(f"- {result.metrics.name}")
        for error in result.errors:
            print(f"  - {error}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
