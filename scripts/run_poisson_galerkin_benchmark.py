#!/usr/bin/env python3
"""Run immersed Poisson Galerkin solver-level benchmark profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.evals import run_poisson_galerkin_benchmark


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CUTKIT immersed Poisson Galerkin benchmarks"
    )
    parser.add_argument(
        "--profile",
        choices=("quick", "dense"),
        default="quick",
        help="solver benchmark profile to run",
    )
    parser.add_argument(
        "--backend-mode",
        choices=("jplus", "folded"),
        default="jplus",
        help="quadrature backend mode used for assembly",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="optional JSON output path for solver benchmark manifest",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="always exit zero even when benchmark tolerances fail",
    )
    args = parser.parse_args()

    result = run_poisson_galerkin_benchmark(
        profile_name=args.profile,
        backend_mode=args.backend_mode,
    )

    print(f"profile = {result.profile}")
    print(f"backend = {result.backend_mode}")
    print(f"spline_degree = {result.spline_degree}")
    print(f"reference_quadrature_order = {result.reference_quadrature_order}")

    print("\nSolver rows")
    print(
        "resolution | order | abs_error | rel_error | threshold | residual | cg_iters | free_dofs"
    )
    print("--- | --- | --- | --- | --- | --- | --- | ---")
    for row in result.rows:
        print(
            f"{row.resolution} | {row.quadrature_order} | {row.abs_error:.3e} "
            f"| {row.rel_error:.3e} | {row.threshold:.3e} | {row.residual_norm:.3e} "
            f"| {row.cg_iterations} | {row.free_dof_count}"
        )

    print("\noverall_passed =", result.passed)

    if args.manifest_path is not None:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(result.to_manifest(), indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest: {args.manifest_path}")

    if result.passed or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
