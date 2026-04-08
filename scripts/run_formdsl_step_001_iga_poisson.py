#!/usr/bin/env python3
"""Step-001: end-to-end FormDSL IGA Poisson simulation."""

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


def _form_payload() -> dict[str, object]:
    return {
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "source": pg.default_poisson_source},
        ],
        "boundary_conditions": [{"kind": "essential", "boundary": "all", "value": 0.0}],
        "metadata": {"geometry_map": "bspline"},
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Step-001 tutorial style run: solve a trimmed Poisson problem "
            "through FormDSL -> IGA assembly -> CG solve"
        )
    )
    parser.add_argument("--resolution", type=_positive_int, default=16)
    parser.add_argument("--spline-degree", type=_positive_int, default=2)
    parser.add_argument("--quadrature-order", type=_positive_int, default=4)
    parser.add_argument("--reference-quadrature-order", type=_positive_int, default=6)
    parser.add_argument(
        "--backend-mode",
        choices=("jplus", "folded"),
        default="folded",
        help="quadrature mode used for FormDSL IGA assembly",
    )
    parser.add_argument("--sample-count", type=_positive_int, default=256)
    parser.add_argument("--cg-tolerance", type=_positive_float, default=1.0e-10)
    parser.add_argument("--max-abs-error", type=_positive_float, default=2.0e-4)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path(".artifacts/formdsl-step-001"),
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
        help="always exit zero even when accuracy check fails",
    )
    args = parser.parse_args()

    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=args.sample_count)
    assembled = assemble_form(
        _form_payload(),
        backend="iga",
        panel=panel,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        quadrature_order=args.quadrature_order,
        backend_mode=args.backend_mode,
    )
    payload = cast(IGAAssemblyResult, assembled.payload)

    coefficients, cg_iterations, residual_norm = pg._conjugate_gradient(
        list(payload.matrix_rows),
        list(payload.rhs),
        tolerance=args.cg_tolerance,
        max_iterations=None,
    )
    sampled_solution = pg._sample_solution_on_grid(
        coefficients,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        bounds=payload.bounds,
    )
    reference = pg.solve_trimmed_poisson_galerkin(
        panel,
        resolution=args.resolution,
        spline_degree=args.spline_degree,
        quadrature_order=args.reference_quadrature_order,
        backend_mode="jplus",
        bounds=payload.bounds,
    )
    free_indices = pg._free_indices_for_compare(
        panel,
        resolution=args.resolution,
        bounds=payload.bounds,
    )
    max_abs_error = max(
        (
            abs(sampled_solution[index] - reference.solution[index])
            for index in free_indices
        ),
        default=0.0,
    )
    passed = max_abs_error <= args.max_abs_error

    plot_artifacts: tuple[Path, ...] = ()
    if not args.skip_plots:
        snapshot = pg.build_poisson_galerkin_geometry_snapshot(
            panel,
            resolution=args.resolution,
            bounds=payload.bounds,
        )
        artifacts = write_poisson_galerkin_figure_pack(
            snapshot,
            solutions={
                "step001": sampled_solution,
                "reference": reference.solution,
            },
            output_dir=args.artifact_dir,
            prefix="formdsl-step-001",
        )
        plot_artifacts = tuple(artifact.file_path for artifact in artifacts)

    print("step = 001")
    print("problem = poisson_dirichlet")
    print("pipeline = formdsl -> iga -> cg")
    print(f"resolution = {args.resolution}")
    print(f"spline_degree = {args.spline_degree}")
    print(f"quadrature_order = {args.quadrature_order}")
    print(f"reference_quadrature_order = {args.reference_quadrature_order}")
    print(f"backend_mode = {args.backend_mode}")
    print(f"dof_count = {len(coefficients)}")
    print(f"free_dof_count = {len(free_indices)}")
    print(f"cg_iterations = {cg_iterations}")
    print(f"residual_norm = {residual_norm:.6e}")
    print(f"max_abs_error = {max_abs_error:.6e}")
    print(f"error_threshold = {args.max_abs_error:.6e}")
    if plot_artifacts:
        for artifact_path in plot_artifacts:
            print(f"plot = {artifact_path}")
    print(f"passed = {passed}")

    if args.manifest_path is not None:
        data = {
            "step": "001",
            "problem": "poisson_dirichlet",
            "pipeline": "formdsl -> iga -> cg",
            "resolution": args.resolution,
            "spline_degree": args.spline_degree,
            "quadrature_order": args.quadrature_order,
            "reference_quadrature_order": args.reference_quadrature_order,
            "backend_mode": args.backend_mode,
            "cg_tolerance": args.cg_tolerance,
            "max_abs_error_threshold": args.max_abs_error,
            "dof_count": len(coefficients),
            "free_dof_count": len(free_indices),
            "cg_iterations": cg_iterations,
            "residual_norm": residual_norm,
            "max_abs_error": max_abs_error,
            "passed": passed,
            "plot_artifacts": [str(path) for path in plot_artifacts],
            "assembly_diagnostics": [
                {
                    "code": diagnostic.code,
                    "backend": diagnostic.backend,
                    "detail": diagnostic.detail,
                    "alternatives": diagnostic.alternatives,
                }
                for diagnostic in assembled.diagnostics
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
