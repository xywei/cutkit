#!/usr/bin/env python3
"""Run formdsl backend parity benchmark examples."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.evals import (
    run_formdsl_multipatch_stress_benchmark,
    run_formdsl_parity_benchmark,
)


def _parse_resolutions(raw: str) -> tuple[int, ...]:
    parts = [part.strip() for part in raw.split(",") if part.strip()]
    if not parts:
        raise argparse.ArgumentTypeError(
            "resolutions must include at least one integer"
        )

    values: list[int] = []
    for part in parts:
        try:
            value = int(part)
        except ValueError as exc:
            raise argparse.ArgumentTypeError(
                f"invalid resolution value {part!r}; expected integer"
            ) from exc
        if value <= 0:
            raise argparse.ArgumentTypeError(
                f"invalid resolution value {part!r}; expected positive integer"
            )
        values.append(value)
    return tuple(values)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Run CUTKIT formdsl iga/dgsem parity benchmark examples"
    )
    parser.add_argument(
        "--resolutions",
        type=_parse_resolutions,
        default=(8, 16),
        help="comma-separated IGA resolutions (for example: 8,16)",
    )
    parser.add_argument(
        "--max-iga-error",
        type=float,
        default=2.0e-4,
        help="maximum acceptable iga absolute error per row",
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
        help="always exit zero even when iga tolerance checks fail",
    )
    parser.add_argument(
        "--include-multipatch-stress",
        action="store_true",
        help="also run deterministic multipatch stress fixtures",
    )
    args = parser.parse_args()

    result = run_formdsl_parity_benchmark(resolutions=args.resolutions)
    passed = all(row.iga_abs_error <= args.max_iga_error for row in result.rows)
    multipatch_stress = (
        run_formdsl_multipatch_stress_benchmark()
        if args.include_multipatch_stress
        else None
    )

    print("resolutions =", ", ".join(str(row.resolution) for row in result.rows))
    print("max_iga_error =", f"{args.max_iga_error:.3e}")
    print()
    print("IGA parity rows")
    print("resolution | iga_abs_error")
    print("--- | ---")
    for row in result.rows:
        print(f"{row.resolution} | {row.iga_abs_error:.6e}")

    print()
    print("Shared IR term signature")
    for entry in result.shared_term_signature:
        print(f"- {entry}")
    print("Shared IR boundary signature")
    for entry in result.shared_boundary_signature:
        print(f"- {entry}")
    print("Shared IR metadata signature")
    for entry in result.shared_metadata_signature:
        print(f"- {entry}")

    print()
    print("DG-SEM lowering signature")
    for entry in result.dgsem_signature:
        print(f"- {entry}")
    print("DG-SEM flux signature")
    for entry in result.dgsem_flux_signature:
        print(f"- {entry}")
    if multipatch_stress is not None:
        print()
        print("IGA multipatch stress rows")
        print(
            "name | execution_path | interfaces | nnz | max_abs | repeat_matrix_diff | repeat_rhs_diff"
        )
        print("--- | --- | --- | --- | --- | --- | ---")
        for row in multipatch_stress.rows:
            print(
                f"{row.name} | {row.execution_path} | {row.interface_count} "
                f"| {row.matrix_nnz} | {row.matrix_max_abs:.6e} "
                f"| {row.repeat_matrix_max_abs_diff:.3e} "
                f"| {row.repeat_rhs_max_abs_diff:.3e}"
            )
        print(
            "orientation_delta_max_abs =",
            f"{multipatch_stress.orientation_delta_max_abs:.6e}",
        )
    print()
    print("passed =", passed)

    if args.manifest_path is not None:
        payload = {
            "rows": [
                {
                    "resolution": row.resolution,
                    "iga_abs_error": row.iga_abs_error,
                }
                for row in result.rows
            ],
            "shared_term_signature": result.shared_term_signature,
            "shared_boundary_signature": result.shared_boundary_signature,
            "shared_metadata_signature": result.shared_metadata_signature,
            "dgsem_signature": result.dgsem_signature,
            "dgsem_flux_signature": result.dgsem_flux_signature,
            "max_iga_error": args.max_iga_error,
            "multipatch_stress": (
                {
                    "rows": [
                        {
                            "name": row.name,
                            "resolution": row.resolution,
                            "execution_path": row.execution_path,
                            "interface_count": row.interface_count,
                            "matrix_nnz": row.matrix_nnz,
                            "matrix_max_abs": row.matrix_max_abs,
                            "rhs_max_abs": row.rhs_max_abs,
                            "repeat_matrix_max_abs_diff": row.repeat_matrix_max_abs_diff,
                            "repeat_rhs_max_abs_diff": row.repeat_rhs_max_abs_diff,
                        }
                        for row in multipatch_stress.rows
                    ],
                    "orientation_delta_max_abs": multipatch_stress.orientation_delta_max_abs,
                }
                if multipatch_stress is not None
                else None
            ),
            "passed": passed,
        }
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest: {args.manifest_path}")

    if passed or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
