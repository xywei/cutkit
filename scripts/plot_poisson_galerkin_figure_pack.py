#!/usr/bin/env python3
"""Generate paper-style Poisson Galerkin figure pack (geometry + convergence)."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.diagnostics import (
    write_poisson_galerkin_error_plots,
    write_poisson_galerkin_figure_pack,
)
from cutkit.evals import (
    GALERKIN_PROFILES,
    build_poisson_galerkin_geometry_snapshot,
    build_section_6_1_1_bspline_panel,
    run_poisson_galerkin_benchmark,
    solve_trimmed_poisson_galerkin,
)


def _artifact_name(artifact: object) -> str:
    if hasattr(artifact, "kind"):
        return str(getattr(artifact, "kind"))
    return str(getattr(artifact, "metric"))


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate geometry/solution/error figures for Poisson Galerkin benchmarks"
    )
    parser.add_argument(
        "--profile",
        choices=("quick", "dense"),
        default="quick",
        help="benchmark profile",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=Path(".artifacts") / "poisson-galerkin-figures",
        help="directory for generated figure artifacts",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="optional JSON output path for figure + benchmark metadata",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="always exit zero even if benchmark tolerances fail",
    )
    args = parser.parse_args()

    profile = GALERKIN_PROFILES[args.profile]
    panel = build_section_6_1_1_bspline_panel(sample_count=256)

    jplus = run_poisson_galerkin_benchmark(
        profile_name=args.profile, backend_mode="jplus"
    )
    folded = run_poisson_galerkin_benchmark(
        profile_name=args.profile, backend_mode="folded"
    )

    figure_resolution = profile.grid_resolutions[-1]
    geometry_snapshot = build_poisson_galerkin_geometry_snapshot(
        panel,
        resolution=figure_resolution,
    )
    jplus_solve = solve_trimmed_poisson_galerkin(
        panel,
        resolution=figure_resolution,
        spline_degree=profile.spline_degree,
        quadrature_order=profile.quadrature_order,
        backend_mode="jplus",
    )
    folded_solve = solve_trimmed_poisson_galerkin(
        panel,
        resolution=figure_resolution,
        spline_degree=profile.spline_degree,
        quadrature_order=profile.quadrature_order,
        backend_mode="folded",
    )

    args.output_dir.mkdir(parents=True, exist_ok=True)
    geometry_artifacts = write_poisson_galerkin_figure_pack(
        geometry_snapshot,
        solutions={
            "jplus": jplus_solve.solution,
            "folded": folded_solve.solution,
        },
        output_dir=args.output_dir,
        prefix="poisson-galerkin",
    )
    error_artifacts = write_poisson_galerkin_error_plots(
        {
            "jplus": jplus,
            "folded": folded,
        },
        output_dir=args.output_dir,
        prefix="poisson-galerkin",
    )

    print(f"profile = {args.profile}")
    print(f"jplus_passed = {jplus.passed}")
    print(f"folded_passed = {folded.passed}")
    print(f"spline_degree = {profile.spline_degree}")
    print(f"figure_resolution = {figure_resolution}")
    for artifact in (*geometry_artifacts, *error_artifacts):
        name = _artifact_name(artifact)
        print(f"{name} = {artifact.file_path}")

    if args.manifest_path is not None:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": 1,
            "profile": args.profile,
            "spline_degree": profile.spline_degree,
            "figure_resolution": figure_resolution,
            "artifacts": {
                _artifact_name(artifact): str(artifact.file_path)
                for artifact in (*geometry_artifacts, *error_artifacts)
            },
            "benchmarks": {
                "jplus": jplus.to_manifest(),
                "folded": folded.to_manifest(),
            },
        }
        args.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest: {args.manifest_path}")

    if (jplus.passed and folded.passed) or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
