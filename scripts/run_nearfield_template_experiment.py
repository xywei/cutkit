#!/usr/bin/env python3
"""Run the folded fan near-field template experiment."""

from __future__ import annotations

import argparse

from cutkit.evals import run_nearfield_template_experiment


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--order",
        type=int,
        default=12,
        help="Gauss-Legendre order for the target template coordinates.",
    )
    parser.add_argument(
        "--scale-factor",
        type=float,
        default=1.75,
        help="Positive geometry scale factor for the log-kernel scale-law check.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    result = run_nearfield_template_experiment(
        order=args.order,
        scale_factor=args.scale_factor,
    )

    print("field | value")
    print("--- | ---")
    print(f"order | {result.order}")
    print(f"source_order | {result.source_order}")
    print(f"near_point_target | {result.near_point_target}")
    print(f"point_target_reference | {result.point_target_reference:.16e}")
    print(f"point_target_low_order | {result.point_target_low_order:.16e}")
    print(f"point_target_abs_error | {result.point_target_abs_error:.16e}")
    print(f"signed_area | {result.signed_area:.16e}")
    print(f"self_interaction | {result.self_interaction:.16e}")
    print(f"scale_factor | {result.scale_factor:.16e}")
    print(f"scaled_self_interaction | {result.scaled_self_interaction:.16e}")
    print(
        f"expected_scaled_self_interaction | {result.expected_scaled_self_interaction:.16e}"
    )
    print(f"scaled_abs_error | {result.scaled_abs_error:.16e}")
    print("")
    print("delta | physical_distance | model_distance | remainder")
    print("--- | --- | --- | ---")
    for sample in result.diagonal_remainders:
        print(
            f"{sample.delta:.1e} | {sample.physical_distance:.16e} | "
            f"{sample.model_distance:.16e} | {sample.remainder:.16e}"
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
