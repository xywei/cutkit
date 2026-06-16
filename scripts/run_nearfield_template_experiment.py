#!/usr/bin/env python3
"""Run the folded fan near-field template experiment."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path

from cutkit.evals import (
    DmkSplitExperimentReport,
    run_dmk_split_nearfield_experiment,
    run_nearfield_template_experiment,
)


def _parse_int_tuple(value: str) -> tuple[int, ...]:
    items = tuple(int(item.strip()) for item in value.split(",") if item.strip())
    if not items:
        raise argparse.ArgumentTypeError("expected at least one integer")
    return items


def _parse_float_tuple(value: str) -> tuple[float, ...]:
    items = tuple(float(item.strip()) for item in value.split(",") if item.strip())
    if not items:
        raise argparse.ArgumentTypeError("expected at least one float")
    return items


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
    parser.add_argument(
        "--dmk-split-report",
        action="store_true",
        help="Run the DMK-style smooth/local split experiment instead of the baseline.",
    )
    parser.add_argument(
        "--orders",
        type=_parse_int_tuple,
        default=(4, 6, 8, 10, 14, 18),
        help="Comma-separated quadrature orders for --dmk-split-report.",
    )
    parser.add_argument(
        "--sigmas",
        type=_parse_float_tuple,
        default=(0.08, 0.16, 0.32),
        help="Comma-separated Ewald split widths for --dmk-split-report.",
    )
    parser.add_argument(
        "--reference-order",
        type=int,
        default=96,
        help="Reference quadrature order for --dmk-split-report.",
    )
    parser.add_argument(
        "--json-output",
        type=Path,
        help="Optional JSON output path for --dmk-split-report.",
    )
    parser.add_argument(
        "--markdown-output",
        type=Path,
        help="Optional Markdown output path for --dmk-split-report.",
    )
    return parser.parse_args()


def _format_dmk_split_report(report: DmkSplitExperimentReport) -> str:
    lines: list[str] = []
    lines.append("# DMK-Style Near-Field Split Report")
    lines.append("")
    lines.append(f"reference_order: `{report.reference_order}`")
    lines.append(f"orders: `{', '.join(str(order) for order in report.orders)}`")
    lines.append(f"sigmas: `{', '.join(f'{sigma:g}' for sigma in report.sigmas)}`")
    lines.append("")
    lines.append("## Seed Quality")
    lines.append("")
    lines.append(
        "fixture | seed_mode | seed | min_det | det_ratio | min_edge_distance | edge_distance_ratio"
    )
    lines.append("--- | --- | --- | --- | --- | --- | ---")
    for sample in report.seed_quality:
        lines.append(
            f"{sample.fixture} | {sample.seed_mode} | {sample.seed} | "
            f"{sample.min_abs_boundary_det:.6e} | "
            f"{sample.max_to_min_abs_boundary_det:.6e} | "
            f"{sample.min_edge_distance:.6e} | "
            f"{sample.max_to_min_edge_distance:.6e}"
        )

    lines.append("")
    lines.append("## Highest-Order Error Summary")
    lines.append("")
    lines.append(
        "fixture | seed_mode | target | sigma | full_error | smooth_error | local_error | analytic_local_error | reconstructed_error | analytic_reconstructed_error | smooth_improvement | local_to_full"
    )
    lines.append(
        "--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---"
    )
    max_order = max(report.orders)
    for sample in report.samples:
        if sample.order != max_order:
            continue
        improvement = sample.full_abs_error / max(sample.smooth_abs_error, 1.0e-300)
        lines.append(
            f"{sample.fixture} | {sample.seed_mode} | {sample.target_label} | "
            f"{sample.sigma:.3g} | {sample.full_abs_error:.6e} | "
            f"{sample.smooth_abs_error:.6e} | {sample.local_abs_error:.6e} | "
            f"{sample.analytic_local_abs_error:.6e} | "
            f"{sample.reconstructed_abs_error:.6e} | "
            f"{sample.analytic_reconstructed_abs_error:.6e} | "
            f"{improvement:.6e} | "
            f"{sample.local_to_full_ratio:.6e}"
        )

    lines.append("")
    lines.append("## Error By Order")
    lines.append("")
    lines.append(
        "fixture | seed_mode | target | sigma | order | full_error | smooth_error | local_error | analytic_local_error | reconstructed_error | analytic_reconstructed_error | smooth_improvement"
    )
    lines.append(
        "--- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | ---"
    )
    for sample in report.samples:
        improvement = sample.full_abs_error / max(sample.smooth_abs_error, 1.0e-300)
        lines.append(
            f"{sample.fixture} | {sample.seed_mode} | {sample.target_label} | "
            f"{sample.sigma:.3g} | {sample.order} | {sample.full_abs_error:.6e} | "
            f"{sample.smooth_abs_error:.6e} | {sample.local_abs_error:.6e} | "
            f"{sample.analytic_local_abs_error:.6e} | "
            f"{sample.reconstructed_abs_error:.6e} | "
            f"{sample.analytic_reconstructed_abs_error:.6e} | {improvement:.6e}"
        )
    lines.append("")
    return "\n".join(lines)


def _run_dmk_split_report(args: argparse.Namespace) -> int:
    report = run_dmk_split_nearfield_experiment(
        orders=args.orders,
        sigmas=args.sigmas,
        reference_order=args.reference_order,
    )
    markdown = _format_dmk_split_report(report)
    if args.json_output is not None:
        args.json_output.parent.mkdir(parents=True, exist_ok=True)
        args.json_output.write_text(json.dumps(asdict(report), indent=2) + "\n")
    if args.markdown_output is not None:
        args.markdown_output.parent.mkdir(parents=True, exist_ok=True)
        args.markdown_output.write_text(markdown)
    print(markdown)
    return 0


def main() -> int:
    args = _parse_args()
    if args.dmk_split_report:
        return _run_dmk_split_report(args)

    result = run_nearfield_template_experiment(
        order=args.order,
        scale_factor=args.scale_factor,
    )

    print("field | value")
    print("--- | ---")
    print(f"order | {result.order}")
    print(f"near_point_target | {result.near_point_target}")
    print(f"point_target_reference | {result.point_target_reference:.16e}")
    print(f"point_target_low_order | {result.point_target_low_order:.16e}")
    print(f"point_target_abs_error | {result.point_target_abs_error:.16e}")
    print(f"signed_area | {result.signed_area:.16e}")
    print(f"density_mass | {result.density_mass:.16e}")
    print(f"scale_factor | {result.scale_factor:.16e}")
    print(f"scaled_near_point_target | {result.scaled_near_point_target}")
    print(
        f"scaled_point_target_potential | {result.scaled_point_target_potential:.16e}"
    )
    print(
        "expected_scaled_point_target_potential | "
        f"{result.expected_scaled_point_target_potential:.16e}"
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
