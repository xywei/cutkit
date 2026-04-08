#!/usr/bin/env python3
"""Step-002: end-to-end FormDSL IGA multipatch Poisson simulation."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import cast

from cutkit.diagnostics.poisson_galerkin_figures import (
    write_poisson_galerkin_figure_pack,
)
from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import assemble_form
from cutkit.formdsl.iga_backend import IGAAssemblyResult


def _positive_int(raw: str) -> int:
    try:
        value = int(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected positive integer") from exc
    if value <= 0:
        raise argparse.ArgumentTypeError("expected positive integer")
    return value


def _positive_float(raw: str) -> float:
    try:
        value = float(raw)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("expected positive float") from exc
    if value <= 0.0:
        raise argparse.ArgumentTypeError("expected positive float")
    return value


def _sparse_max_abs_diff(
    lhs: tuple[dict[int, float], ...],
    rhs: tuple[dict[int, float], ...],
) -> float:
    if len(lhs) != len(rhs):
        raise ValueError("sparse row counts must match")
    max_diff = 0.0
    for lhs_row, rhs_row in zip(lhs, rhs, strict=True):
        keys = set(lhs_row) | set(rhs_row)
        for key in keys:
            diff = abs(lhs_row.get(key, 0.0) - rhs_row.get(key, 0.0))
            if diff > max_diff:
                max_diff = diff
    return max_diff


def _vector_max_abs_diff(lhs: tuple[float, ...], rhs: tuple[float, ...]) -> float:
    if len(lhs) != len(rhs):
        raise ValueError("vector lengths must match")
    return max((abs(a - b) for a, b in zip(lhs, rhs, strict=True)), default=0.0)


def _form_payload() -> dict[str, object]:
    return {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "source": pg.default_poisson_source},
        ],
        "boundary_conditions": [{"kind": "essential", "boundary": "all", "value": 0.0}],
        "metadata": {
            "geometry_map": "bspline",
            "multipatch_penalty": "1.25",
            "multipatch_boundary:patch-b:marker:b-right": "right",
            "multipatch_boundary:patch-a:marker:a-top": "top",
            "multipatch_boundary:patch-c:marker:c-top": "top",
            "multipatch_boundary:patch-a:marker:a-right": "right",
        },
        "multipatch": {
            "patch_ids": ["patch-a", "patch-b", "patch-c"],
            "interfaces": [
                {
                    "plus_patch": "patch-b",
                    "minus_patch": "patch-a",
                    "plus_boundary": "marker:b-right",
                    "minus_boundary": "marker:a-top",
                    "orientation": "aligned",
                    "penalty": 0.75,
                },
                {
                    "plus_patch": "patch-c",
                    "minus_patch": "patch-a",
                    "plus_boundary": "marker:c-top",
                    "minus_boundary": "marker:a-right",
                    "orientation": "reversed",
                    "penalty": 1.5,
                },
            ],
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Step-002 tutorial style run: solve a multipatch trimmed Poisson "
            "problem with FormDSL IGA interface coupling"
        )
    )
    parser.add_argument("--resolution", type=_positive_int, default=8)
    parser.add_argument("--spline-degree", type=_positive_int, default=2)
    parser.add_argument("--quadrature-order", type=_positive_int, default=4)
    parser.add_argument("--sample-count", type=_positive_int, default=256)
    parser.add_argument("--cg-tolerance", type=_positive_float, default=1.0e-10)
    parser.add_argument("--max-residual", type=_positive_float, default=1.0e-8)
    parser.add_argument(
        "--max-repeat-coeff-diff",
        type=_positive_float,
        default=1.0e-10,
        help="determinism threshold between repeated assembled solves",
    )
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path(".artifacts/formdsl-step-002"),
        help="directory for generated SVG plots",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="disable SVG artifact generation",
    )
    parser.add_argument("--manifest-path", type=Path, default=None)
    parser.add_argument(
        "--allow-fail",
        action="store_true",
        help="always exit zero even when checks fail",
    )
    args = parser.parse_args()

    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=args.sample_count)
    first = assemble_form(
        _form_payload(),
        backend="iga",
        panel=panel,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        quadrature_order=args.quadrature_order,
        backend_mode="folded",
    )
    second = assemble_form(
        _form_payload(),
        backend="iga",
        panel=panel,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        quadrature_order=args.quadrature_order,
        backend_mode="folded",
    )
    first_payload = cast(IGAAssemblyResult, first.payload)
    second_payload = cast(IGAAssemblyResult, second.payload)

    coefficients, cg_iterations, residual_norm = pg._conjugate_gradient(
        list(first_payload.matrix_rows),
        list(first_payload.rhs),
        tolerance=args.cg_tolerance,
        max_iterations=None,
    )
    repeat_coefficients, _repeat_iterations, repeat_residual_norm = (
        pg._conjugate_gradient(
            list(second_payload.matrix_rows),
            list(second_payload.rhs),
            tolerance=args.cg_tolerance,
            max_iterations=None,
        )
    )

    matrix_repeat_diff = _sparse_max_abs_diff(
        first_payload.matrix_rows,
        second_payload.matrix_rows,
    )
    rhs_repeat_diff = _vector_max_abs_diff(first_payload.rhs, second_payload.rhs)
    coeff_repeat_diff = _vector_max_abs_diff(coefficients, repeat_coefficients)

    sampled_solution = pg._sample_solution_on_grid(
        coefficients,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        bounds=first_payload.bounds,
    )
    sampled_repeat_solution = pg._sample_solution_on_grid(
        repeat_coefficients,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        bounds=first_payload.bounds,
    )
    sampled_abs_delta = tuple(
        abs(a - b)
        for a, b in zip(sampled_solution, sampled_repeat_solution, strict=True)
    )

    passed = (
        residual_norm <= args.max_residual
        and repeat_residual_norm <= args.max_residual
        and coeff_repeat_diff <= args.max_repeat_coeff_diff
    )

    plot_artifacts: tuple[Path, ...] = ()
    if not args.skip_plots:
        snapshot = pg.build_poisson_galerkin_geometry_snapshot(
            panel,
            resolution=args.resolution,
            bounds=first_payload.bounds,
        )
        artifacts = write_poisson_galerkin_figure_pack(
            snapshot,
            solutions={
                "step002": sampled_solution,
                "repeat": sampled_repeat_solution,
                "repeat-delta": sampled_abs_delta,
            },
            output_dir=args.artifact_dir,
            prefix="formdsl-step-002",
        )
        plot_artifacts = tuple(artifact.file_path for artifact in artifacts)

    print("step = 002")
    print("problem = poisson_dirichlet_multipatch")
    print("pipeline = formdsl -> iga(multipatch) -> cg")
    print(f"resolution = {args.resolution}")
    print(f"spline_degree = {args.spline_degree}")
    print(f"quadrature_order = {args.quadrature_order}")
    print(f"execution_path = {first_payload.execution_path}")
    print(f"interface_count = {len(first_payload.interface_lowering)}")
    for index, interface in enumerate(first_payload.interface_lowering):
        print(
            f"interface[{index}] = "
            f"{interface.plus_patch}:{interface.plus_boundary} -> "
            f"{interface.minus_patch}:{interface.minus_boundary}; "
            f"orientation={interface.orientation}; "
            f"orientation_sign={interface.orientation_sign}; "
            f"penalty={interface.coupling_penalty:.6g}"
        )
    print(f"dof_count = {len(coefficients)}")
    print(f"cg_iterations = {cg_iterations}")
    print(f"residual_norm = {residual_norm:.6e}")
    print(f"repeat_residual_norm = {repeat_residual_norm:.6e}")
    print(f"repeat_matrix_max_abs_diff = {matrix_repeat_diff:.6e}")
    print(f"repeat_rhs_max_abs_diff = {rhs_repeat_diff:.6e}")
    print(f"repeat_coeff_max_abs_diff = {coeff_repeat_diff:.6e}")
    print(f"residual_threshold = {args.max_residual:.6e}")
    print(f"repeat_coeff_threshold = {args.max_repeat_coeff_diff:.6e}")
    if plot_artifacts:
        for artifact_path in plot_artifacts:
            print(f"plot = {artifact_path}")
    print(f"passed = {passed}")

    if args.manifest_path is not None:
        data = {
            "step": "002",
            "problem": "poisson_dirichlet_multipatch",
            "pipeline": "formdsl -> iga(multipatch) -> cg",
            "resolution": args.resolution,
            "spline_degree": args.spline_degree,
            "quadrature_order": args.quadrature_order,
            "cg_tolerance": args.cg_tolerance,
            "residual_threshold": args.max_residual,
            "repeat_coeff_threshold": args.max_repeat_coeff_diff,
            "execution_path": first_payload.execution_path,
            "interface_count": len(first_payload.interface_lowering),
            "interfaces": [
                {
                    "plus_patch": entry.plus_patch,
                    "minus_patch": entry.minus_patch,
                    "plus_boundary": entry.plus_boundary,
                    "minus_boundary": entry.minus_boundary,
                    "orientation": entry.orientation,
                    "orientation_sign": entry.orientation_sign,
                    "coupling_penalty": entry.coupling_penalty,
                }
                for entry in first_payload.interface_lowering
            ],
            "dof_count": len(coefficients),
            "cg_iterations": cg_iterations,
            "residual_norm": residual_norm,
            "repeat_residual_norm": repeat_residual_norm,
            "repeat_matrix_max_abs_diff": matrix_repeat_diff,
            "repeat_rhs_max_abs_diff": rhs_repeat_diff,
            "repeat_coeff_max_abs_diff": coeff_repeat_diff,
            "passed": passed,
            "plot_artifacts": [str(path) for path in plot_artifacts],
            "first_assembly_diagnostics": [
                {
                    "code": diagnostic.code,
                    "backend": diagnostic.backend,
                    "detail": diagnostic.detail,
                    "alternatives": diagnostic.alternatives,
                }
                for diagnostic in first.diagnostics
            ],
            "second_assembly_diagnostics": [
                {
                    "code": diagnostic.code,
                    "backend": diagnostic.backend,
                    "detail": diagnostic.detail,
                    "alternatives": diagnostic.alternatives,
                }
                for diagnostic in second.diagnostics
            ],
        }
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest: {args.manifest_path}")

    if passed or args.allow_fail:
        return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
