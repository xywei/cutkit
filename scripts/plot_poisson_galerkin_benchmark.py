#!/usr/bin/env python3
"""Generate paper-style convergence plots for immersed Poisson Galerkin runs."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.diagnostics import write_poisson_galerkin_error_plots
from cutkit.evals import run_poisson_galerkin_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Generate SVG convergence plots for Poisson Galerkin benchmarks"
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
        default=Path(".artifacts") / "poisson-galerkin-plots",
        help="directory for generated SVG plots",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="optional JSON output path for benchmark + plot metadata",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="always exit zero even when benchmark tolerances fail",
    )
    args = parser.parse_args()

    jplus = run_poisson_galerkin_benchmark(
        profile_name=args.profile, backend_mode="jplus"
    )
    folded = run_poisson_galerkin_benchmark(
        profile_name=args.profile,
        backend_mode="folded",
    )

    artifacts = write_poisson_galerkin_error_plots(
        {
            "jplus": jplus,
            "folded": folded,
        },
        output_dir=args.output_dir,
    )

    print(f"profile = {args.profile}")
    for benchmark in (jplus, folded):
        print(f"{benchmark.backend_mode}_passed = {benchmark.passed}")
    for artifact in artifacts:
        print(f"{artifact.metric}_plot = {artifact.file_path}")

    if args.manifest_path is not None:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        manifest = {
            "schema_version": 1,
            "profile": args.profile,
            "plots": {
                artifact.metric: str(artifact.file_path) for artifact in artifacts
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
