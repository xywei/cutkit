#!/usr/bin/env python3
"""Reproduce Section 6 2D experiments with paper-style protocols."""

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
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    grid_resolution: int,
    seed_grid_size: int,
    reference_order: int,
) -> None:
    if label == "6.1.1":
        panel = build_section_6_1_1_bspline_panel(sample_count=sample_count)
    else:
        panel = build_section_6_1_2_rational_panel(sample_count=sample_count)

    result = run_polynomial_experiment(
        panel,
        label=label,
        degrees=degrees,
        orders=orders,
        grid_resolution=grid_resolution,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
    )

    print(f"Section {label} polynomial protocol")
    print("degree | order | folded_abs_eq18 | jplus_abs_eq18 | folded_rel | jplus_rel")
    print("--- | --- | --- | --- | --- | ---")
    for degree_result in result.degree_results:
        for idx, order in enumerate(degree_result.orders):
            print(
                f"{degree_result.degree} | {order} | "
                f"{degree_result.folded_abs_error[idx]:.3e} | "
                f"{degree_result.jplus_abs_error[idx]:.3e} | "
                f"{degree_result.folded_rel_error[idx]:.3e} | "
                f"{degree_result.jplus_rel_error[idx]:.3e}"
            )
    print()


def _print_general_function_result(
    *,
    sample_count: int,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...],
    reference_grid_resolution: int,
    reference_order: int,
) -> None:
    panel = build_section_6_1_1_bspline_panel(sample_count=sample_count)
    result = run_general_function_experiment(
        panel,
        orders=orders,
        grid_resolutions=grid_resolutions,
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
        folded_anchor_mode="cell-origin",
    )

    print("Section 6.2 general-function protocol (2D)")
    print("reference_value =", f"{result.reference_value:.15e}")
    for order_result in result.order_results:
        print()
        print(f"n = {order_result.order}")
        print("grid | h | folded_abs | jplus_abs | folded_rel | jplus_rel")
        print("--- | --- | --- | --- | --- | ---")
        for idx, resolution in enumerate(order_result.grid_resolutions):
            print(
                f"{resolution} | {order_result.h_values[idx]:.6f} | "
                f"{order_result.folded_abs_error[idx]:.3e} | "
                f"{order_result.jplus_abs_error[idx]:.3e} | "
                f"{order_result.folded_rel_error[idx]:.3e} | "
                f"{order_result.jplus_rel_error[idx]:.3e}"
            )


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Reproduce 2D Section 6 protocols from folded decomposition paper"
    )
    parser.add_argument(
        "--paper",
        action="store_true",
        help="use paper-level protocol parameters (slower)",
    )
    args = parser.parse_args()

    if args.paper:
        sample_count = 192
        sec61_grid_resolution = 8
        sec61_seed_grid_size = 11
        sec61_reference_order = 64
        sec61_1_degrees = tuple(range(1, 11))
        sec61_2_degrees = (2, 4, 6)
        sec61_orders = tuple(range(1, 13))

        sec62_orders = (1, 2, 3, 4, 5)
        sec62_grids = (2, 4, 8, 16, 32, 64, 128)
        sec62_reference_grid = 128
        sec62_reference_order = 64
    else:
        sample_count = 128
        sec61_grid_resolution = 8
        sec61_seed_grid_size = 5
        sec61_reference_order = 24
        sec61_1_degrees = (1, 2)
        sec61_2_degrees = (2,)
        sec61_orders = (2, 4)

        sec62_orders = (1, 2)
        sec62_grids = (2, 4, 8)
        sec62_reference_grid = 16
        sec62_reference_order = 24

    print("Using sample_count =", sample_count)
    print("Section 6.1 grid resolution =", sec61_grid_resolution)
    print("Section 6.1 seed grid size =", sec61_seed_grid_size)
    print("Section 6.1 reference order =", sec61_reference_order)
    print(
        "Section 6.2 reference grid/order =",
        sec62_reference_grid,
        sec62_reference_order,
    )
    print()

    _print_polynomial_result(
        "6.1.1",
        sample_count=sample_count,
        degrees=sec61_1_degrees,
        orders=sec61_orders,
        grid_resolution=sec61_grid_resolution,
        seed_grid_size=sec61_seed_grid_size,
        reference_order=sec61_reference_order,
    )
    _print_polynomial_result(
        "6.1.2",
        sample_count=sample_count,
        degrees=sec61_2_degrees,
        orders=sec61_orders,
        grid_resolution=sec61_grid_resolution,
        seed_grid_size=sec61_seed_grid_size,
        reference_order=sec61_reference_order,
    )
    _print_general_function_result(
        sample_count=sample_count,
        orders=sec62_orders,
        grid_resolutions=sec62_grids,
        reference_grid_resolution=sec62_reference_grid,
        reference_order=sec62_reference_order,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
