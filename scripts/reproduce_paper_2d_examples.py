#!/usr/bin/env python3
"""Reproduce the 2D folded-decomposition examples from Antolin-Wei-Buffa.

This script follows the paper's Section 6 setup in a CUTKIT-adapted way:
- Section 6.1.1: polynomial integration on a B-rep with a quadratic B-spline edge
- Section 6.1.2: polynomial integration on a B-rep with a quarter-circle edge
- Section 6.2: non-polynomial integrand in 2D
"""

from __future__ import annotations

import argparse

from cutkit.evals import (
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment,
    run_polynomial_experiment,
)


def _print_polynomial_result(
    label: str,
    *,
    sample_count: int,
    seed_grid_size: int,
    reference_order: int,
    full: bool,
) -> None:
    if label == "6.1.1":
        panel = build_section_6_1_1_bspline_panel(sample_count=sample_count)
        degrees = (1, 2, 3, 4) if full else (1, 2, 3)
        orders = (2, 4, 6, 8, 10) if full else (2, 4, 6, 8)
    else:
        panel = build_section_6_1_2_rational_panel(sample_count=sample_count)
        degrees = (2, 4, 6) if full else (2, 4)
        orders = (3, 5, 7, 9) if full else (3, 5, 7, 9)

    result = run_polynomial_experiment(
        panel,
        label=label,
        degrees=degrees,
        orders=orders,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
    )

    print(f"Section {label} polynomial experiment")
    print("degree | order | folded_worst_err | jplus_err")
    print("--- | --- | --- | ---")
    for degree_result in result.degree_results:
        for idx, order in enumerate(degree_result.orders):
            print(
                f"{degree_result.degree} | {order} | "
                f"{degree_result.folded_worst_error[idx]:.3e} | "
                f"{degree_result.jplus_error[idx]:.3e}"
            )
    print()


def _print_general_function_result(
    *,
    sample_count: int,
    seed_grid_size: int,
    reference_order: int,
    full: bool,
) -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=sample_count)
    orders = (1, 2, 3, 4, 5) if full else (1, 2, 3, 4)
    result = run_general_function_experiment(
        panel,
        orders=orders,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
    )
    print("Section 6.2 general-function experiment (2D)")
    print("order | folded_worst_err | jplus_err")
    print("--- | --- | ---")
    for i, order in enumerate(result.orders):
        print(
            f"{order} | {result.folded_worst_error[i]:.3e} | "
            f"{result.jplus_error[i]:.3e}"
        )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce 2D examples from the folded decomposition paper"
    )
    parser.add_argument(
        "--full",
        action="store_true",
        help="run denser settings closer to the paper setup",
    )
    args = parser.parse_args()

    if args.full:
        sample_count = 160
        seed_grid_size = 7
        reference_order = 28
    else:
        sample_count = 128
        seed_grid_size = 5
        reference_order = 24

    print("Using curve sample_count =", sample_count)
    print("Using seed grid size =", seed_grid_size)
    print("Using reference order =", reference_order)
    print()
    _print_polynomial_result(
        "6.1.1",
        sample_count=sample_count,
        seed_grid_size=seed_grid_size,
        reference_order=reference_order,
        full=args.full,
    )
    _print_polynomial_result(
        "6.1.2",
        sample_count=sample_count,
        seed_grid_size=seed_grid_size,
        reference_order=reference_order,
        full=args.full,
    )
    _print_general_function_result(
        sample_count=sample_count,
        seed_grid_size=seed_grid_size,
        reference_order=reference_order,
        full=args.full,
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
