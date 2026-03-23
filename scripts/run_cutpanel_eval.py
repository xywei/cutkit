#!/usr/bin/env python3
"""Run the default cut-panel evaluation suite."""

from __future__ import annotations

import argparse
from pathlib import Path

from cutkit.evals import export_failure_artifacts, run_default_eval


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=None,
        help="Write JSON artifacts for failing cases to this directory.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    results = run_default_eval()
    failures = []

    print("name | area | cut_fraction | area_err | max_moment_err | status")
    print("--- | --- | --- | --- | --- | ---")
    for result in results:
        metrics = result.metrics
        status = "PASS" if not result.errors else "FAIL"
        area_err = metrics.folded_rule_abs_error
        max_moment_err = metrics.folded_max_moment_abs_error
        print(
            f"{metrics.name} | {metrics.area:.6f} | {metrics.cut_fraction:.6f} | "
            f"{area_err:.3e} | {max_moment_err:.3e} | {status}"
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

        if result.topology is not None:
            diagnostics = result.topology.diagnostics
            print(
                "  - "
                f"topology.outer.orientation={diagnostics.outer.orientation}, "
                f"topology.outer.self_intersects={diagnostics.outer.self_intersects}, "
                f"topology.panel_area={diagnostics.panel_area:.6e}"
            )

    if args.artifact_dir is not None:
        artifact_paths = export_failure_artifacts(
            tuple(failures),
            output_dir=args.artifact_dir,
        )
        if artifact_paths:
            print(
                f"Wrote {len(artifact_paths)} failure artifacts to {args.artifact_dir}"
            )
            for path in artifact_paths:
                print(f"  - {path}")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
