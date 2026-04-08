#!/usr/bin/env python3
"""Step-003: end-to-end FormDSL DGSEM convection-diffusion prototype."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.diagnostics.poisson_galerkin_figures import (
    render_cell_classification_svg,
    render_trimmed_geometry_svg,
)
from cutkit.diagnostics.svg_plot import (
    SvgLineSeries,
    SvgLogLogChart,
    render_loglog_chart_svg,
)
from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.formdsl import FormSolveResult, PrerequisiteError, solve_form
from cutkit.io import (
    MeshmodeCutOverlay,
    MeshmodeOverlayElement,
    build_meshmode_cut_overlay,
)
from cutkit.quadrature import gauss_legendre_01


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


def _clip_rule_samples(
    clip: awb2d.CellClipResult,
    *,
    quadrature_order: int,
) -> tuple[tuple[tuple[float, float], ...], tuple[float, ...]]:
    if clip.kind == "outside":
        return (), ()

    if clip.kind == "inside":
        nodes, quad_weights = gauss_legendre_01(quadrature_order)
        points: list[tuple[float, float]] = []
        weights: list[float] = []
        for ux, wx in zip(nodes, quad_weights):
            x = clip.cell.x0 + ux * clip.cell.width
            for uy, wy in zip(nodes, quad_weights):
                y = clip.cell.y0 + uy * clip.cell.height
                points.append((x, y))
                weights.append(wx * wy * clip.cell.area)
        return tuple(points), tuple(weights)

    points, weights = awb2d._cached_rule(
        clip.polygon,
        quadrature_order,
        (clip.cell.x0, clip.cell.y0),
        False,
    )
    return (
        tuple((float(x), float(y)) for x, y in points),
        tuple(float(weight) for weight in weights),
    )


def _build_overlay_payload(
    *,
    resolution: int,
    sample_count: int = 256,
    quadrature_order: int = 2,
) -> tuple[MeshmodeCutOverlay, pg.PoissonGalerkinGeometrySnapshot]:
    panel = awb2d.build_section_6_1_1_bspline_panel(sample_count=sample_count)
    snapshot = pg.build_poisson_galerkin_geometry_snapshot(
        panel,
        resolution=resolution,
        bounds=(0.0, 0.0, 1.0, 1.0),
    )
    bounds = snapshot.bounds
    clipped = snapshot.clipped_cells

    target_ids: list[int] = []
    element_id_map: dict[int, int] = {}
    elements: list[MeshmodeOverlayElement] = []

    for target_id, clip in enumerate(clipped):
        source_id = target_id
        target_ids.append(target_id)
        element_id_map[source_id] = target_id

        points, weights = _clip_rule_samples(clip, quadrature_order=quadrature_order)
        cut_fraction = clip.area / clip.cell.area if clip.cell.area > 0.0 else 0.0
        status = "ok" if points else "empty"
        elements.append(
            MeshmodeOverlayElement(
                source_element_id=source_id,
                points=points,
                weights=weights,
                status=status,
                geometry_metadata={
                    "clip_kind": clip.kind,
                    "cell_ix": clip.cell.ix,
                    "cell_iy": clip.cell.iy,
                    "cell_area": clip.cell.area,
                    "clip_area": clip.area,
                    "cut_fraction": cut_fraction,
                    "bounds": f"{bounds[0]:.6g},{bounds[1]:.6g},{bounds[2]:.6g},{bounds[3]:.6g}",
                },
            )
        )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=tuple(target_ids),
        element_id_map=element_id_map,
        strict=True,
    )
    return overlay, snapshot


def _render_solution_profile_svg(result: FormSolveResult) -> str:
    eps = 1.0e-18
    x_values = tuple(float(index + 1) for index in range(result.dof_count))
    solution_magnitude = tuple(abs(value) + eps for value in result.solution)
    rhs_magnitude = tuple(abs(value) + eps for value in result.rhs)
    row_nnz = tuple(float(max(1, len(row))) for row in result.matrix_rows)

    chart = SvgLogLogChart(
        title="Step-003 DG Solve Profile",
        x_label="DOF Index",
        y_label="Magnitude / Row NNZ",
        series=(
            SvgLineSeries(
                label="|solution|",
                x_values=x_values,
                y_values=solution_magnitude,
                stroke="#f05a28",
            ),
            SvgLineSeries(
                label="|rhs|",
                x_values=x_values,
                y_values=rhs_magnitude,
                stroke="#2080d0",
            ),
            SvgLineSeries(
                label="row nnz",
                x_values=x_values,
                y_values=row_nnz,
                stroke="#39a96b",
            ),
        ),
    )
    return render_loglog_chart_svg(chart)


def _form_payload() -> dict[str, object]:
    return {
        "trial_space": "P1",
        "test_space": "P1",
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "convection", "coefficient": 0.35},
            {"kind": "reaction", "coefficient": 0.05},
            {"kind": "source", "coefficient": 1.0, "source": 1.0},
        ],
        "boundary_conditions": [
            {"kind": "essential", "boundary": "left", "value": 0.0},
            {"kind": "essential", "boundary": "right", "value": 0.0},
            {"kind": "natural", "boundary": "top", "value": 0.1},
        ],
        "metadata": {
            "dg_flux": "sipg",
            "dg_penalty": "1.0",
        },
    }


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Step-003 tutorial style run: solve a DGSEM grudge-backed "
            "convection-diffusion problem "
            "through FormDSL lowering and linear solve"
        )
    )
    parser.add_argument(
        "--resolution",
        type=_positive_int,
        default=24,
        help=(
            "background Cartesian resolution for CUTKIT clipped-cell overlay "
            "construction"
        ),
    )
    parser.add_argument(
        "--elements",
        type=_positive_int,
        default=None,
        help="deprecated alias for --resolution",
    )
    parser.add_argument("--sample-count", type=_positive_int, default=256)
    parser.add_argument("--overlay-quadrature-order", type=_positive_int, default=2)
    parser.add_argument(
        "--artifact-dir",
        type=Path,
        default=Path(".artifacts/formdsl-step-003"),
        help="directory for generated SVG plots",
    )
    parser.add_argument(
        "--skip-plots",
        action="store_true",
        help="disable SVG artifact generation",
    )
    parser.add_argument("--cg-tolerance", type=_positive_float, default=1.0e-10)
    parser.add_argument("--max-residual", type=_positive_float, default=1.0e-7)
    parser.add_argument("--manifest-path", type=Path, default=None)
    args = parser.parse_args()

    resolution = args.elements if args.elements is not None else args.resolution
    overlay_payload, overlay_snapshot = _build_overlay_payload(
        resolution=resolution,
        sample_count=args.sample_count,
        quadrature_order=args.overlay_quadrature_order,
    )
    overlay_ok = sum(1 for status in overlay_payload.statuses if status == "ok")
    overlay_empty = sum(1 for status in overlay_payload.statuses if status == "empty")
    plot_artifacts: list[Path] = []

    if not args.skip_plots:
        args.artifact_dir.mkdir(parents=True, exist_ok=True)

        geometry_path = args.artifact_dir / "formdsl-step-003-geometry.svg"
        geometry_path.write_text(
            render_trimmed_geometry_svg(
                overlay_snapshot,
                title="Step-003 Trimmed Overlay Geometry",
            ),
            encoding="utf-8",
        )
        plot_artifacts.append(geometry_path)

        cells_path = args.artifact_dir / "formdsl-step-003-cell-classification.svg"
        cells_path.write_text(
            render_cell_classification_svg(
                overlay_snapshot,
                title="Step-003 Overlay Cell Classification",
            ),
            encoding="utf-8",
        )
        plot_artifacts.append(cells_path)

    try:
        result = solve_form(
            _form_payload(),
            backend="dgsem",
            strict=False,
            overlay_payload=overlay_payload,
            cg_tolerance=args.cg_tolerance,
            dgsem_execution_mode="grudge",
        )
    except PrerequisiteError as exc:
        print("step = 003")
        print("problem = convection_diffusion_dgsem_prototype")
        print("runtime = grudge")
        print("overlay_geometry = section_6_1_1_bspline_trimmed_panel")
        print(f"overlay_resolution = {resolution}")
        print(f"overlay_target_elements = {len(overlay_payload.target_element_ids)}")
        print(f"overlay_ok_elements = {overlay_ok}")
        print(f"overlay_empty_elements = {overlay_empty}")
        print(f"overlay_point_count = {len(overlay_payload.point_coords)}")
        for artifact_path in plot_artifacts:
            print(f"plot = {artifact_path}")
        print(f"failed_prerequisite = {exc}")
        return 1

    if not args.skip_plots:
        profile_path = args.artifact_dir / "formdsl-step-003-solution-profile.svg"
        profile_path.write_text(
            _render_solution_profile_svg(result),
            encoding="utf-8",
        )
        plot_artifacts.append(profile_path)

    passed = result.residual_norm <= args.max_residual

    print("step = 003")
    print("problem = convection_diffusion_dgsem_prototype")
    print("runtime = grudge")
    print(
        f"pipeline = formdsl -> dgsem({result.execution_mode}) -> {result.linear_solver}"
    )
    print("overlay_geometry = section_6_1_1_bspline_trimmed_panel")
    print(f"overlay_resolution = {resolution}")
    print(f"overlay_target_elements = {len(overlay_payload.target_element_ids)}")
    print(f"overlay_ok_elements = {overlay_ok}")
    print(f"overlay_empty_elements = {overlay_empty}")
    print(f"overlay_point_count = {len(overlay_payload.point_coords)}")
    print(f"dof_count = {result.dof_count}")
    print(f"free_dof_count = {result.free_dof_count}")
    print(f"matrix_nnz = {result.matrix_nnz}")
    print(f"cg_iterations = {result.cg_iterations}")
    print(f"residual_norm = {result.residual_norm:.6e}")
    print(f"residual_threshold = {args.max_residual:.6e}")
    for artifact_path in plot_artifacts:
        print(f"plot = {artifact_path}")
    print(f"passed = {passed}")

    if args.manifest_path is not None:
        payload = {
            "step": "003",
            "problem": "convection_diffusion_dgsem_prototype",
            "runtime": "grudge",
            "execution_mode": result.execution_mode,
            "linear_solver": result.linear_solver,
            "overlay_geometry": "section_6_1_1_bspline_trimmed_panel",
            "overlay_resolution": resolution,
            "overlay_target_elements": len(overlay_payload.target_element_ids),
            "overlay_ok_elements": overlay_ok,
            "overlay_empty_elements": overlay_empty,
            "overlay_point_count": len(overlay_payload.point_coords),
            "overlay_quadrature_order": args.overlay_quadrature_order,
            "overlay_sample_count": args.sample_count,
            "dof_count": result.dof_count,
            "free_dof_count": result.free_dof_count,
            "matrix_nnz": result.matrix_nnz,
            "cg_iterations": result.cg_iterations,
            "residual_norm": result.residual_norm,
            "residual_threshold": args.max_residual,
            "passed": passed,
            "plot_artifacts": [str(path) for path in plot_artifacts],
            "assembly_diagnostics": [
                {
                    "code": diagnostic.code,
                    "backend": diagnostic.backend,
                    "detail": diagnostic.detail,
                    "alternatives": diagnostic.alternatives,
                }
                for diagnostic in result.assembly.diagnostics
            ],
        }
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(payload, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print(f"wrote manifest: {args.manifest_path}")

    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
