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
import json
from pathlib import Path
from typing import Any

from cutkit.evals import (
    NUMPY_ACCELERATION_ENABLED,
    OPENCASCADE_CAD_AVAILABLE,
    compare_manifest_to_fixture,
    format_parity_report,
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment_3d_grid,
    run_general_function_experiment_cad,
    run_general_function_experiment,
    run_polynomial_experiment_3d,
    run_polynomial_experiment_cad,
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
) -> Any:
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
    return result


def _print_general_function_result(
    *,
    sample_count: int,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...],
    reference_grid_resolution: int,
    reference_order: int,
) -> Any:
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
    return result


def _print_polynomial_result_cad(
    label: str,
    *,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    grid_resolution: int,
    seed_grid_size: int,
    reference_order: int,
) -> Any:
    result = run_polynomial_experiment_cad(
        label=label,
        degrees=degrees,
        orders=orders,
        grid_resolution=grid_resolution,
        reference_order=reference_order,
        seed_grid_size=seed_grid_size,
    )

    print(f"Section {label} polynomial protocol (CAD-native OpenCascade)")
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
    return result


def _print_general_function_result_cad(
    *,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...],
    reference_grid_resolution: int,
    reference_order: int,
) -> Any:
    result = run_general_function_experiment_cad(
        label="6.1.1",
        orders=orders,
        grid_resolutions=grid_resolutions,
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
        folded_anchor_mode="cell-origin",
    )

    print("Section 6.2 general-function protocol (2D CAD-native OpenCascade)")
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
    return result


def _print_polynomial_result_3d(
    *,
    degrees: tuple[int, ...],
    orders: tuple[int, ...],
    seed_grid_size: int,
    surface_resolution: int,
    reference_order: int,
) -> Any:
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
    return result


def _print_general_result_3d(
    *,
    orders: tuple[int, ...],
    grid_resolutions: tuple[int, ...],
    reference_grid_resolution: int,
    reference_order: int,
) -> Any:
    result = run_general_function_experiment_3d_grid(
        orders=orders,
        grid_resolutions=grid_resolutions,
        reference_grid_resolution=reference_grid_resolution,
        reference_order=reference_order,
    )

    print("Section 6.2 general-function protocol (3D Cartesian cut-cell refinement)")
    print("note: CUTKIT-adapted protocol; monitor per-row monotonic diagnostics")
    print("reference_value =", f"{result.reference_value:.15e}")
    for order_result in result.order_results:
        print()
        print(f"n = {order_result.order}")
        if order_result.monotone_nonincreasing:
            print("monotonicity: non-increasing")
        else:
            print(
                "monotonicity: non-monotone at pair indices",
                order_result.monotonicity_violation_indices,
            )
        print("grid | h | folded_abs | folded_rel")
        print("--- | --- | --- | ---")
        for i, resolution in enumerate(order_result.grid_resolutions):
            print(
                f"{resolution} | {order_result.h_values[i]:.6f} | "
                f"{order_result.folded_abs_error[i]:.3e} | "
                f"{order_result.folded_rel_error[i]:.3e}"
            )
    print()
    return result


def _serialize_polynomial_result(result: Any) -> dict[str, Any]:
    return {
        "label": result.label,
        "grid_resolution": result.grid_resolution,
        "reference_order": result.reference_order,
        "seed_grid_size": result.seed_grid_size,
        "degree_results": [
            {
                "degree": degree_result.degree,
                "orders": list(degree_result.orders),
                "trimmed_cell_count": degree_result.trimmed_cell_count,
                "folded_abs_error": list(degree_result.folded_abs_error),
                "jplus_abs_error": list(degree_result.jplus_abs_error),
                "folded_rel_error": list(degree_result.folded_rel_error),
                "jplus_rel_error": list(degree_result.jplus_rel_error),
                "folded_reference_scale": degree_result.folded_reference_scale,
                "jplus_reference_scale": degree_result.jplus_reference_scale,
            }
            for degree_result in result.degree_results
        ],
    }


def _serialize_general_result(result: Any) -> dict[str, Any]:
    return {
        "reference_value": result.reference_value,
        "reference_grid_resolution": result.reference_grid_resolution,
        "reference_order": result.reference_order,
        "order_results": [
            {
                "order": order_result.order,
                "grid_resolutions": list(order_result.grid_resolutions),
                "h_values": list(order_result.h_values),
                "folded_abs_error": list(order_result.folded_abs_error),
                "jplus_abs_error": list(order_result.jplus_abs_error),
                "folded_rel_error": list(order_result.folded_rel_error),
                "jplus_rel_error": list(order_result.jplus_rel_error),
            }
            for order_result in result.order_results
        ],
    }


def _serialize_polynomial_result_3d(result: Any) -> dict[str, Any]:
    return {
        "seed_grid_size": result.seed_grid_size,
        "surface_resolution": result.surface_resolution,
        "reference_order": result.reference_order,
        "jplus_seed": list(result.jplus_seed),
        "domain_volume": result.domain_volume,
        "degree_results": [
            {
                "degree": degree_result.degree,
                "orders": list(degree_result.orders),
                "folded_worst_abs_error": list(degree_result.folded_worst_abs_error),
                "folded_best_abs_error": list(degree_result.folded_best_abs_error),
                "jplus_abs_error": list(degree_result.jplus_abs_error),
            }
            for degree_result in result.degree_results
        ],
    }


def _serialize_general_result_3d(result: Any) -> dict[str, Any]:
    return {
        "reference_grid_resolution": result.reference_grid_resolution,
        "reference_order": result.reference_order,
        "reference_value": result.reference_value,
        "order_results": [
            {
                "order": order_result.order,
                "grid_resolutions": list(order_result.grid_resolutions),
                "h_values": list(order_result.h_values),
                "folded_abs_error": list(order_result.folded_abs_error),
                "folded_rel_error": list(order_result.folded_rel_error),
                "monotone_nonincreasing": order_result.monotone_nonincreasing,
                "monotonicity_violation_indices": list(
                    order_result.monotonicity_violation_indices
                ),
            }
            for order_result in result.order_results
        ],
    }


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
    parser.add_argument(
        "--geometry-mode",
        choices=("auto", "polygonized", "cad-native"),
        default="auto",
        help=(
            "2D geometry backend: auto picks CAD-native when OpenCascade is available "
            "and otherwise falls back to polygonized MVP"
        ),
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="write a machine-readable Section 6 manifest to this path",
    )
    parser.add_argument(
        "--parity-fixture",
        type=Path,
        default=None,
        help="compare current manifest against this fixture JSON",
    )
    parser.add_argument(
        "--write-parity-fixture",
        action="store_true",
        help="write current manifest to --parity-fixture and skip comparison",
    )
    parser.add_argument(
        "--parity-abs-tol",
        type=float,
        default=1.0e-10,
        help="absolute tolerance for parity metric comparisons",
    )
    parser.add_argument(
        "--parity-rel-tol",
        type=float,
        default=1.0e-8,
        help="relative tolerance for parity metric comparisons",
    )
    args = parser.parse_args()

    if args.write_parity_fixture and args.parity_fixture is None:
        raise ValueError("--write-parity-fixture requires --parity-fixture")

    geometry_mode = args.geometry_mode
    if geometry_mode == "auto":
        geometry_mode = "cad-native" if OPENCASCADE_CAD_AVAILABLE else "polygonized"
    if geometry_mode == "cad-native" and not OPENCASCADE_CAD_AVAILABLE:
        raise RuntimeError(
            "`--geometry-mode cad-native` requested but OpenCascade is unavailable. "
            "Install with `uv sync --extra cad` and ensure libGL is present."
        )

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

        sec623d_orders = (2, 3, 4)
        sec623d_grids = (2, 4, 8, 16)
        sec623d_reference_grid = 32
        sec623d_reference_order = 24
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
        sec623d_grids = (2, 4)
        sec623d_reference_grid = 16
        sec623d_reference_order = 12

    print("Using sample_count =", sample_count)
    print("Section 6.1 grid resolution =", sec61_grid_resolution)
    print("Section 6.1 seed grid size =", sec61_seed_grid_size)
    print("Section 6.1 reference order =", sec61_reference_order)
    print(
        "Section 6.2 reference grid/order =",
        sec62_reference_grid,
        sec62_reference_order,
    )
    print("OpenCascade CAD backend available =", OPENCASCADE_CAD_AVAILABLE)
    print("2D geometry mode =", geometry_mode)
    print("NumPy acceleration enabled =", NUMPY_ACCELERATION_ENABLED)
    if not NUMPY_ACCELERATION_ENABLED:
        print(
            "Warning: this script without NumPy can be very slow. "
            "Install NumPy or run with a Python environment that has NumPy."
        )
    print()

    if geometry_mode == "cad-native":
        poly_611 = _print_polynomial_result_cad(
            "6.1.1",
            degrees=sec61_1_degrees,
            orders=sec61_orders,
            grid_resolution=sec61_grid_resolution,
            seed_grid_size=sec61_seed_grid_size,
            reference_order=sec61_reference_order,
        )
        poly_612 = _print_polynomial_result_cad(
            "6.1.2",
            degrees=sec61_2_degrees,
            orders=sec61_orders,
            grid_resolution=sec61_grid_resolution,
            seed_grid_size=sec61_seed_grid_size,
            reference_order=sec61_reference_order,
        )
        general_2d = _print_general_function_result_cad(
            orders=sec62_orders,
            grid_resolutions=sec62_grids,
            reference_grid_resolution=sec62_reference_grid,
            reference_order=sec62_reference_order,
        )
    else:
        poly_611 = _print_polynomial_result(
            "6.1.1",
            sample_count=sample_count,
            degrees=sec61_1_degrees,
            orders=sec61_orders,
            grid_resolution=sec61_grid_resolution,
            seed_grid_size=sec61_seed_grid_size,
            reference_order=sec61_reference_order,
        )
        poly_612 = _print_polynomial_result(
            "6.1.2",
            sample_count=sample_count,
            degrees=sec61_2_degrees,
            orders=sec61_orders,
            grid_resolution=sec61_grid_resolution,
            seed_grid_size=sec61_seed_grid_size,
            reference_order=sec61_reference_order,
        )
        general_2d = _print_general_function_result(
            sample_count=sample_count,
            orders=sec62_orders,
            grid_resolutions=sec62_grids,
            reference_grid_resolution=sec62_reference_grid,
            reference_order=sec62_reference_order,
        )

    manifest: dict[str, Any] = {
        "schema_version": 1,
        "profile": "antolin-paper" if args.antolin_paper else "quick",
        "geometry_mode": geometry_mode,
        "scope": "2d-only" if args.skip_3d else "full",
        "requires_cad": geometry_mode == "cad-native",
        "cad_available": OPENCASCADE_CAD_AVAILABLE,
        "numpy_acceleration": NUMPY_ACCELERATION_ENABLED,
        "sections": {
            "2d": {
                "polynomial": {
                    "6.1.1": _serialize_polynomial_result(poly_611),
                    "6.1.2": _serialize_polynomial_result(poly_612),
                },
                "general": _serialize_general_result(general_2d),
            }
        },
    }

    if not args.skip_3d:
        polynomial_3d = _print_polynomial_result_3d(
            degrees=sec613_degrees,
            orders=sec613_orders,
            seed_grid_size=sec613_seed_grid,
            surface_resolution=sec613_surface_resolution,
            reference_order=sec613_reference_order,
        )
        general_3d = _print_general_result_3d(
            orders=sec623d_orders,
            grid_resolutions=sec623d_grids,
            reference_grid_resolution=sec623d_reference_grid,
            reference_order=sec623d_reference_order,
        )
        manifest["sections"]["3d"] = {
            "polynomial": _serialize_polynomial_result_3d(polynomial_3d),
            "general": _serialize_general_result_3d(general_3d),
        }
    else:
        manifest["sections"]["3d"] = {"status": "skipped"}

    if args.manifest_path is not None:
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote manifest to {args.manifest_path}")

    if args.write_parity_fixture and args.parity_fixture is not None:
        args.parity_fixture.parent.mkdir(parents=True, exist_ok=True)
        args.parity_fixture.write_text(
            json.dumps(manifest, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"Wrote parity fixture to {args.parity_fixture}")

    if args.parity_fixture is not None and not args.write_parity_fixture:
        fixture = json.loads(args.parity_fixture.read_text(encoding="utf-8"))
        report = compare_manifest_to_fixture(
            manifest,
            fixture,
            abs_tol=args.parity_abs_tol,
            rel_tol=args.parity_rel_tol,
        )
        print(format_parity_report(report))
        if not report.passed and report.skipped_reason is None:
            return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
