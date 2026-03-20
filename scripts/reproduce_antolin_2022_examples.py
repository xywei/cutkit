#!/usr/bin/env python3
"""Reproduce Section 6 experiments from Antolin-Wei-Buffa (2022).

Source and credit:
- Pablo Antolin, Xiaodong Wei, Annalisa Buffa.
- "Robust Numerical Integration on Curved Polyhedra Based on Folded Decompositions".
- Computer Methods in Applied Mechanics and Engineering, 2022.
- DOI: 10.1016/j.cma.2022.114948
- arXiv: https://arxiv.org/abs/2109.03734
"""

from __future__ import annotations

import argparse

from cutkit.evals import (
    NUMPY_ACCELERATION_ENABLED,
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment_3d,
    run_general_function_experiment,
    run_polynomial_experiment_3d,
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


def _print_polynomial_result_3d(
    *,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    seed_grid_size: int,
    surface_resolution: int,
    reference_order: int,
) -> None:
    result = run_polynomial_experiment_3d(
        degrees=degrees,
        orders=orders,
        seed_grid_size=seed_grid_size,
        surface_resolution=surface_resolution,
        reference_order=reference_order,
    )

    print("Section 6.1.3 polynomial protocol (3D)")
    print("domain_volume =", f"{result.domain_volume:.15e}")
    print("degree | order | folded_worst_abs | folded_best_abs | jplus_abs")
    print("--- | --- | --- | --- | ---")
    for degree_result in result.degree_results:
        for idx, order in enumerate(degree_result.orders):
            print(
                f"{degree_result.degree} | {order} | "
                f"{degree_result.folded_worst_abs_error[idx]:.3e} | "
                f"{degree_result.folded_best_abs_error[idx]:.3e} | "
                f"{degree_result.jplus_abs_error[idx]:.3e}"
            )
    print()


def _print_general_result_3d(
    *,
    orders: tuple[int, ...],
    seed_grid_size: int,
    surface_resolution: int,
    reference_order: int,
) -> None:
    result = run_general_function_experiment_3d(
        orders=orders,
        seed_grid_size=seed_grid_size,
        surface_resolution=surface_resolution,
        reference_order=reference_order,
    )

    print("Section 6.2-style general-function protocol (3D single-cell)")
    print("reference_value =", f"{result.reference_value:.15e}")
    print("order | folded_worst_abs | folded_best_abs | jplus_abs")
    print("--- | --- | --- | ---")
    for order_result in result.orders:
        print(
            f"{order_result.order} | "
            f"{order_result.folded_worst_abs_error:.3e} | "
            f"{order_result.folded_best_abs_error:.3e} | "
            f"{order_result.jplus_abs_error:.3e}"
        )
    print()


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Reproduce 2D Section 6 protocols from "
            "Antolin-Wei-Buffa (CMAME 2022, DOI 10.1016/j.cma.2022.114948)"
        )
    )
    parser.add_argument(
        "--antolin-paper",
        action="store_true",
        help="use denser Antolin-Wei-Buffa 2022 protocol parameters (slower)",
    )
    parser.add_argument(
        "--skip-3d",
        action="store_true",
        help="skip Section 6 3D reproductions",
    )
    args = parser.parse_args()

    if args.antolin_paper:
        sample_count = 160
        sec61_grid_resolution = 8
        sec61_seed_grid_size = 7
        sec61_reference_order = 48
        sec61_1_degrees = tuple(range(1, 7))
        sec61_2_degrees = (2, 4, 6)
        sec61_orders = (2, 4, 6, 8, 10)

        sec62_orders = (1, 2, 3, 4, 5)
        sec62_grids = (2, 4, 8, 16, 32, 64)
        sec62_reference_grid = 64
        sec62_reference_order = 48

        sec613_degrees = (3, 6, 9)
        sec613_orders = (3, 5, 7, 9)
        sec613_seed_grid = 5
        sec613_surface_resolution = 8
        sec613_reference_order = 11

        sec623d_orders = (2, 3, 4, 5)
        sec623d_seed_grid = 5
        sec623d_surface_resolution = 8
        sec623d_reference_order = 11
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

        sec613_degrees = (3,)
        sec613_orders = (3, 5)
        sec613_seed_grid = 3
        sec613_surface_resolution = 5
        sec613_reference_order = 7

        sec623d_orders = (2, 3)
        sec623d_seed_grid = 3
        sec623d_surface_resolution = 5
        sec623d_reference_order = 7

    print("Using sample_count =", sample_count)
    print("Section 6.1 grid resolution =", sec61_grid_resolution)
    print("Section 6.1 seed grid size =", sec61_seed_grid_size)
    print("Section 6.1 reference order =", sec61_reference_order)
    print(
        "Section 6.2 reference grid/order =",
        sec62_reference_grid,
        sec62_reference_order,
    )
    print("NumPy acceleration enabled =", NUMPY_ACCELERATION_ENABLED)
    if not NUMPY_ACCELERATION_ENABLED:
        print(
            "Warning: this script without NumPy can be very slow. "
            "Install NumPy or run with a Python environment that has NumPy."
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

    if not args.skip_3d:
        _print_polynomial_result_3d(
            degrees=sec613_degrees,
            orders=sec613_orders,
            seed_grid_size=sec613_seed_grid,
            surface_resolution=sec613_surface_resolution,
            reference_order=sec613_reference_order,
        )
        _print_general_result_3d(
            orders=sec623d_orders,
            seed_grid_size=sec623d_seed_grid,
            surface_resolution=sec623d_surface_resolution,
            reference_order=sec623d_reference_order,
        )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
