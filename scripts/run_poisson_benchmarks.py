#!/usr/bin/env python3
"""Run Poisson-oriented trimmed-domain benchmark profiles."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.evals import run_poisson_benchmarks


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CUTKIT Poisson-oriented benchmark profiles"
    )
    parser.add_argument(
        "--profile",
        choices=("quick", "dense"),
        default="quick",
        help="benchmark profile to run",
    )
    parser.add_argument(
        "--backend-mode",
        choices=("jplus", "folded"),
        default="jplus",
        help="quadrature backend mode",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="optional JSON output path for benchmark manifest",
    )
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="always exit zero even when benchmark tolerances fail",
    )
    args = parser.parse_args()

    result = run_poisson_benchmarks(
        profile_name=args.profile,
        backend_mode=args.backend_mode,
    )

    print(f"profile = {result.profile}")
    print(f"backend = {result.planar.backend_mode}")

    print("\nPlanar benchmark")
    print("order | abs_error | rel_error")
    print("--- | --- | ---")
    for row in result.planar.order_results:
        print(f"{row.order} | {row.abs_error:.3e} | {row.rel_error:.3e}")
    print("passed =", result.planar.passed)

    print("\nVolume benchmark")
    print("order | abs_error | rel_error")
    print("--- | --- | ---")
    for row in result.volume.order_results:
        print(f"{row.order} | {row.abs_error:.3e} | {row.rel_error:.3e}")
    print("passed =", result.volume.passed)

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
