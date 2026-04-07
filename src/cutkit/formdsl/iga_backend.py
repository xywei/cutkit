"""IR-to-IGA lowering and assembly using trimmed quadrature."""

from __future__ import annotations

from dataclasses import dataclass
from math import hypot, isclose, isfinite
from typing import Callable

from cutkit.evals import antolin_wei_buffa_2022_2d as awb2d
from cutkit.evals import poisson_galerkin as pg
from cutkit.geometry import Point2D, TrimmedPanel2D

from .ir import MultipatchInterfaceDescriptor, SourceComponent, SourceValue, WeakFormIR

_BOUNDARY_SELECTORS = {"all", "left", "right", "bottom", "top"}


@dataclass(frozen=True)
class IGAAssemblyResult:
    """Assembled linear system and effective integration bounds."""

    matrix_rows: tuple[dict[int, float], ...]
    rhs: tuple[float, ...]
    bounds: tuple[float, float, float, float]
    geometry_map: str
    execution_path: str
    interface_lowering: tuple["IGAInterfaceLowering", ...] = ()


@dataclass(frozen=True)
class IGAInterfaceLowering:
    """Deterministic multipatch interface lowering metadata."""

    plus_patch: str
    minus_patch: str
    plus_boundary: str
    minus_boundary: str
    orientation: str
    orientation_sign: int


def _term_scalar(form_ir: WeakFormIR, kind: str) -> float:
    value = 0.0
    for term in form_ir.terms:
        if term.kind == kind:
            value += term.coefficient
    return value


def _scalar_source_component(term_source: SourceValue) -> SourceComponent:
    if isinstance(term_source, tuple):
        return term_source[0] if term_source else None
    return term_source


def _orientation_sign(orientation: str) -> int:
    if orientation == "aligned":
        return 1
    if orientation == "reversed":
        return -1
    raise ValueError(f"unsupported multipatch interface orientation: {orientation!r}")


def _interface_canonical_key(
    interface: MultipatchInterfaceDescriptor,
) -> tuple[str, str, str, str, str]:
    if interface.plus_patch <= interface.minus_patch:
        return (
            interface.plus_patch,
            interface.minus_patch,
            interface.plus_boundary,
            interface.minus_boundary,
            interface.orientation,
        )
    return (
        interface.minus_patch,
        interface.plus_patch,
        interface.minus_boundary,
        interface.plus_boundary,
        interface.orientation,
    )


def _lower_multipatch_interfaces(
    form_ir: WeakFormIR,
) -> tuple[IGAInterfaceLowering, ...]:
    multipatch = form_ir.multipatch
    if multipatch is None:
        return ()

    lowered: list[tuple[tuple[str, str, str, str, str], IGAInterfaceLowering]] = []
    for interface in multipatch.interfaces:
        key = _interface_canonical_key(interface)
        lowered.append(
            (
                key,
                IGAInterfaceLowering(
                    plus_patch=interface.plus_patch,
                    minus_patch=interface.minus_patch,
                    plus_boundary=interface.plus_boundary,
                    minus_boundary=interface.minus_boundary,
                    orientation=interface.orientation,
                    orientation_sign=_orientation_sign(interface.orientation),
                ),
            )
        )

    lowered.sort(key=lambda item: item[0])
    canonical_keys = [key for key, _entry in lowered]
    for index in range(1, len(canonical_keys)):
        if canonical_keys[index] != canonical_keys[index - 1]:
            continue
        raise ValueError(
            "multipatch interfaces contain duplicate canonical descriptors"
        )

    return tuple(entry for _key, entry in lowered)


def _normalized_geometry_map(form_ir: WeakFormIR) -> str:
    raw_geometry_map = str(form_ir.metadata.get("geometry_map", "bspline")).strip()
    if not raw_geometry_map:
        return "bspline"
    return raw_geometry_map.lower()


def _execution_path_for_iga(*, geometry_map: str, has_multipatch: bool) -> str:
    if has_multipatch:
        if geometry_map == "nurbs":
            return "nurbs_rational_multipatch_interface"
        return "bspline_multipatch_interface"
    if geometry_map == "nurbs":
        return "nurbs_rational_single_patch"
    return "bspline"


def _parse_nurbs_weights(
    metadata: dict[str, str], *, dof_count: int
) -> tuple[float, ...]:
    raw_weights = metadata.get("nurbs_weights")
    if raw_weights is None:
        return tuple(1.0 for _ in range(dof_count))

    cleaned = raw_weights.strip().replace("[", "").replace("]", "")
    if not cleaned:
        raise ValueError("nurbs_weights metadata is empty")

    values: list[float] = []
    for token in cleaned.split(","):
        token = token.strip()
        if not token:
            continue
        try:
            value = float(token)
        except ValueError as error:
            raise ValueError(f"nurbs_weights entry {token!r} is not numeric") from error
        if not isfinite(value):
            raise ValueError("nurbs_weights entries must be finite")
        if value <= 0.0:
            raise ValueError("nurbs_weights entries must be positive")
        values.append(value)

    if len(values) != dof_count:
        raise ValueError(
            f"nurbs_weights length {len(values)} does not match dof count {dof_count}"
        )
    return tuple(values)


def _parse_multipatch_penalty(metadata: dict[str, str]) -> float:
    raw_penalty = metadata.get("multipatch_penalty")
    if raw_penalty is None:
        return 1.0
    try:
        penalty = float(raw_penalty)
    except ValueError as error:
        raise ValueError("multipatch_penalty metadata must be numeric") from error
    if not isfinite(penalty) or penalty <= 0.0:
        raise ValueError("multipatch_penalty metadata must be finite and positive")
    return penalty


def _basis_terms_at_point_for_geometry_map(
    *,
    x: float,
    y: float,
    resolution: int,
    spline_degree: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
    geometry_map: str,
    nurbs_weights: tuple[float, ...],
) -> tuple[tuple[int, float, float, float], ...]:
    if geometry_map == "nurbs":
        return _basis_terms_at_point_rational(
            x=x,
            y=y,
            resolution=resolution,
            spline_degree=spline_degree,
            n_basis_axis=n_basis_axis,
            knots_x=knots_x,
            knots_y=knots_y,
            bounds=bounds,
            weights=nurbs_weights,
        )
    return pg._basis_terms_at_point(
        x=x,
        y=y,
        resolution=resolution,
        spline_degree=spline_degree,
        n_basis_axis=n_basis_axis,
        knots_x=knots_x,
        knots_y=knots_y,
        bounds=bounds,
    )


def _basis_terms_at_point_rational(
    *,
    x: float,
    y: float,
    resolution: int,
    spline_degree: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
    weights: tuple[float, ...],
) -> tuple[tuple[int, float, float, float], ...]:
    bspline_terms = pg._basis_terms_at_point(
        x=x,
        y=y,
        resolution=resolution,
        spline_degree=spline_degree,
        n_basis_axis=n_basis_axis,
        knots_x=knots_x,
        knots_y=knots_y,
        bounds=bounds,
    )
    basis_terms: list[tuple[int, float, float, float]] = []
    weight_scale = 0.0
    for index, value, grad_x, grad_y in bspline_terms:
        basis_terms.append((index, value, grad_x, grad_y))
        weight_scale = max(weight_scale, abs(weights[index] * value))

    if weight_scale <= 0.0 or not isfinite(weight_scale):
        raise ValueError("nurbs basis weights are invalid")

    inv_weight_scale = 1.0 / weight_scale
    if not isfinite(inv_weight_scale):
        raise ValueError("nurbs basis weights are invalid")

    weighted_terms: list[tuple[int, float, float, float]] = []
    for index, value, grad_x, grad_y in basis_terms:
        scaled_weighted_value = (weights[index] * value) * inv_weight_scale
        if value != 0.0:
            scaled_weighted_grad_x = scaled_weighted_value * (grad_x / value)
            scaled_weighted_grad_y = scaled_weighted_value * (grad_y / value)
        else:
            scaled_weighted_grad_x = (weights[index] * grad_x) * inv_weight_scale
            scaled_weighted_grad_y = (weights[index] * grad_y) * inv_weight_scale
        weighted_terms.append(
            (
                index,
                scaled_weighted_value,
                scaled_weighted_grad_x,
                scaled_weighted_grad_y,
            )
        )

    denominator = 0.0
    grad_denominator_x = 0.0
    grad_denominator_y = 0.0
    for (
        _index,
        scaled_weighted_value,
        scaled_weighted_grad_x,
        scaled_weighted_grad_y,
    ) in weighted_terms:
        denominator += scaled_weighted_value
        grad_denominator_x += scaled_weighted_grad_x
        grad_denominator_y += scaled_weighted_grad_y

    if denominator <= 0.0 or not isfinite(denominator):
        raise ValueError("nurbs basis denominator is numerically zero")

    inv_denominator = 1.0 / denominator
    if not isfinite(inv_denominator):
        raise ValueError("nurbs basis denominator is numerically zero")

    rational_terms: list[tuple[int, float, float, float]] = []
    for (
        index,
        scaled_weighted_value,
        scaled_weighted_grad_x,
        scaled_weighted_grad_y,
    ) in weighted_terms:
        rational_value = scaled_weighted_value * inv_denominator
        rational_grad_x = (
            scaled_weighted_grad_x - rational_value * grad_denominator_x
        ) * inv_denominator
        rational_grad_y = (
            scaled_weighted_grad_y - rational_value * grad_denominator_y
        ) * inv_denominator
        if not (
            isfinite(rational_value)
            and isfinite(rational_grad_x)
            and isfinite(rational_grad_y)
        ):
            raise ValueError("nurbs rational basis terms are numerically unstable")
        rational_terms.append((index, rational_value, rational_grad_x, rational_grad_y))

    return tuple(rational_terms)


def _source_fn(form_ir: WeakFormIR) -> Callable[[float, float], float]:
    callable_sources: list[tuple[float, Callable[[float, float], float]]] = []
    constant_total = 0.0

    for term in form_ir.terms:
        if term.kind != "source" or isclose(term.coefficient, 0.0):
            continue
        source_component = _scalar_source_component(term.source)
        if callable(source_component):
            callable_sources.append((term.coefficient, source_component))
            continue
        if source_component is None:
            constant_total += term.coefficient
            continue
        constant_total += term.coefficient * float(source_component)

    if not callable_sources and isclose(constant_total, 0.0):
        return lambda _x, _y: 0.0

    def _composite_source(x: float, y: float) -> float:
        value = constant_total
        for coefficient, source in callable_sources:
            value += coefficient * source(x, y)
        return value

    return _composite_source


def _resolve_boundary_selector(boundary: str, *, metadata: dict[str, str]) -> str:
    if boundary in _BOUNDARY_SELECTORS:
        return boundary
    if not boundary.startswith("marker:"):
        raise ValueError(f"unknown boundary selector: {boundary!r}")

    marker = boundary.removeprefix("marker:").strip()
    if not marker:
        raise ValueError("boundary marker selector is missing marker id")

    metadata_key = f"boundary_marker:{marker}"
    resolved = metadata.get(metadata_key)
    if resolved is None:
        raise ValueError(
            f"boundary marker {marker!r} is missing selector mapping in metadata"
        )
    if resolved not in _BOUNDARY_SELECTORS:
        raise ValueError(
            f"boundary marker {marker!r} maps to unsupported selector {resolved!r}"
        )
    return resolved


def _resolve_interface_selector(
    *,
    patch_id: str,
    boundary: str,
    metadata: dict[str, str],
) -> str:
    patch_key = f"multipatch_boundary:{patch_id}:{boundary}"
    patch_selector = metadata.get(patch_key)
    if patch_selector is None:
        return _resolve_boundary_selector(boundary, metadata=metadata)

    normalized_selector = str(patch_selector).strip().lower()
    if normalized_selector not in _BOUNDARY_SELECTORS:
        raise ValueError(
            f"multipatch boundary metadata {patch_key!r} maps to unsupported selector {patch_selector!r}"
        )
    return normalized_selector


def _segment_matches_selector(
    start: Point2D,
    end: Point2D,
    *,
    selector: str,
    bounds: tuple[float, float, float, float],
    tol: float,
) -> bool:
    if selector == "all":
        return True

    x0, y0 = start
    x1, y1 = end
    xmin, ymin, xmax, ymax = bounds
    if selector == "left":
        return abs(x0 - xmin) <= tol and abs(x1 - xmin) <= tol
    if selector == "right":
        return abs(x0 - xmax) <= tol and abs(x1 - xmax) <= tol
    if selector == "bottom":
        return abs(y0 - ymin) <= tol and abs(y1 - ymin) <= tol
    if selector == "top":
        return abs(y0 - ymax) <= tol and abs(y1 - ymax) <= tol
    raise ValueError(f"unknown boundary selector: {selector!r}")


def _selected_boundary_segments(
    panel: TrimmedPanel2D,
    *,
    selector: str,
    bounds: tuple[float, float, float, float],
) -> tuple[tuple[Point2D, Point2D], ...]:
    xmin, ymin, xmax, ymax = bounds
    scale = max(abs(xmax - xmin), abs(ymax - ymin), 1.0)
    tol = 1.0e-12 * scale

    selected: list[tuple[Point2D, Point2D]] = []
    for loop in panel.loops():
        for start, end in loop.edges():
            if _segment_matches_selector(
                start,
                end,
                selector=selector,
                bounds=bounds,
                tol=tol,
            ):
                selected.append((start, end))
    return tuple(selected)


def _paired_interface_segments(
    *,
    panel: TrimmedPanel2D,
    bounds: tuple[float, float, float, float],
    plus_selector: str,
    minus_selector: str,
) -> tuple[tuple[Point2D, Point2D, Point2D, Point2D, float], ...]:
    plus_segments = _selected_boundary_segments(
        panel,
        selector=plus_selector,
        bounds=bounds,
    )
    minus_segments = _selected_boundary_segments(
        panel,
        selector=minus_selector,
        bounds=bounds,
    )
    if len(plus_segments) != len(minus_segments):
        raise ValueError(
            "multipatch interface segment count mismatch between plus and minus boundaries"
        )

    paired: list[tuple[Point2D, Point2D, Point2D, Point2D, float]] = []
    for (plus_start, plus_end), (minus_start, minus_end) in zip(
        plus_segments,
        minus_segments,
        strict=True,
    ):
        plus_length = hypot(plus_end[0] - plus_start[0], plus_end[1] - plus_start[1])
        minus_length = hypot(
            minus_end[0] - minus_start[0],
            minus_end[1] - minus_start[1],
        )

        if plus_length <= 1.0e-18 and minus_length <= 1.0e-18:
            continue
        if plus_length <= 1.0e-18 or minus_length <= 1.0e-18:
            raise ValueError(
                "multipatch interface segment pairing includes degenerate segment"
            )
        scale = max(plus_length, minus_length, 1.0)
        if abs(plus_length - minus_length) > 1.0e-9 * scale:
            raise ValueError(
                "multipatch interface segment length mismatch between plus and minus boundaries"
            )

        paired.append(
            (
                plus_start,
                plus_end,
                minus_start,
                minus_end,
                0.5 * (plus_length + minus_length),
            )
        )

    if not paired:
        raise ValueError("multipatch interface has no non-degenerate paired segments")
    return tuple(paired)


def _add_multipatch_interface_coupling(
    matrix_rows: list[dict[int, float]],
    *,
    form_ir: WeakFormIR,
    panel: TrimmedPanel2D,
    resolution: int,
    spline_degree: int,
    quadrature_order: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
    geometry_map: str,
    nurbs_weights: tuple[float, ...],
    interface_lowering: tuple[IGAInterfaceLowering, ...],
) -> None:
    if not interface_lowering:
        return

    penalty = _parse_multipatch_penalty(form_ir.metadata)
    nodes_1d, weights_1d = pg.gauss_legendre_01(
        max(quadrature_order, spline_degree + 1)
    )
    used_selector_pairs: set[tuple[str, str, str]] = set()

    for interface in interface_lowering:
        plus_selector = _resolve_interface_selector(
            patch_id=interface.plus_patch,
            boundary=interface.plus_boundary,
            metadata=form_ir.metadata,
        )
        minus_selector = _resolve_interface_selector(
            patch_id=interface.minus_patch,
            boundary=interface.minus_boundary,
            metadata=form_ir.metadata,
        )
        selector_pair = (plus_selector, minus_selector, interface.orientation)
        if selector_pair in used_selector_pairs:
            raise ValueError(
                "multipatch interfaces reuse resolved selector pair; provide patch-specific multipatch boundary mappings"
            )
        used_selector_pairs.add(selector_pair)

        paired_segments = _paired_interface_segments(
            panel=panel,
            bounds=bounds,
            plus_selector=plus_selector,
            minus_selector=minus_selector,
        )

        for (
            plus_start,
            plus_end,
            minus_start,
            minus_end,
            segment_length,
        ) in paired_segments:
            plus_dx = plus_end[0] - plus_start[0]
            plus_dy = plus_end[1] - plus_start[1]
            minus_dx = minus_end[0] - minus_start[0]
            minus_dy = minus_end[1] - minus_start[1]

            for t, weight_1d in zip(nodes_1d, weights_1d, strict=True):
                minus_t = t if interface.orientation_sign > 0 else 1.0 - t
                plus_x = plus_start[0] + t * plus_dx
                plus_y = plus_start[1] + t * plus_dy
                minus_x = minus_start[0] + minus_t * minus_dx
                minus_y = minus_start[1] + minus_t * minus_dy

                plus_terms = _basis_terms_at_point_for_geometry_map(
                    x=plus_x,
                    y=plus_y,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_basis_axis=n_basis_axis,
                    knots_x=knots_x,
                    knots_y=knots_y,
                    bounds=bounds,
                    geometry_map=geometry_map,
                    nurbs_weights=nurbs_weights,
                )
                minus_terms = _basis_terms_at_point_for_geometry_map(
                    x=minus_x,
                    y=minus_y,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_basis_axis=n_basis_axis,
                    knots_x=knots_x,
                    knots_y=knots_y,
                    bounds=bounds,
                    geometry_map=geometry_map,
                    nurbs_weights=nurbs_weights,
                )

                interface_weight = penalty * weight_1d * segment_length
                for row_index, row_value, _row_gx, _row_gy in plus_terms:
                    row = matrix_rows[row_index]
                    for col_index, col_value, _col_gx, _col_gy in plus_terms:
                        pg._add_to_sparse_row(
                            row,
                            col_index,
                            interface_weight * row_value * col_value,
                        )
                    for col_index, col_value, _col_gx, _col_gy in minus_terms:
                        pg._add_to_sparse_row(
                            row,
                            col_index,
                            -interface_weight * row_value * col_value,
                        )

                for row_index, row_value, _row_gx, _row_gy in minus_terms:
                    row = matrix_rows[row_index]
                    for col_index, col_value, _col_gx, _col_gy in plus_terms:
                        pg._add_to_sparse_row(
                            row,
                            col_index,
                            -interface_weight * row_value * col_value,
                        )
                    for col_index, col_value, _col_gx, _col_gy in minus_terms:
                        pg._add_to_sparse_row(
                            row,
                            col_index,
                            interface_weight * row_value * col_value,
                        )


def _is_boundary_dof(index: int, *, n_basis_axis: int, boundary: str) -> bool:
    ix = index % n_basis_axis
    iy = index // n_basis_axis
    if boundary == "all":
        return (
            ix == 0 or ix == (n_basis_axis - 1) or iy == 0 or iy == (n_basis_axis - 1)
        )
    if boundary == "left":
        return ix == 0
    if boundary == "right":
        return ix == (n_basis_axis - 1)
    if boundary == "bottom":
        return iy == 0
    if boundary == "top":
        return iy == (n_basis_axis - 1)
    raise ValueError(f"unknown boundary selector: {boundary!r}")


def _apply_essential_values(
    matrix_rows: list[dict[int, float]],
    rhs: list[float],
    *,
    fixed_values: dict[int, float],
) -> None:
    for row_index, row in enumerate(matrix_rows):
        if row_index in fixed_values:
            continue
        adjustment = 0.0
        for fixed_index, fixed_value in fixed_values.items():
            if fixed_index not in row:
                continue
            adjustment += row[fixed_index] * fixed_value
            del row[fixed_index]
        rhs[row_index] -= adjustment

    for fixed_index, fixed_value in fixed_values.items():
        matrix_rows[fixed_index] = {fixed_index: 1.0}
        rhs[fixed_index] = fixed_value


def _add_natural_rhs(
    rhs: list[float],
    *,
    form_ir: WeakFormIR,
    panel: TrimmedPanel2D,
    resolution: int,
    spline_degree: int,
    n_basis_axis: int,
    knots_x: tuple[float, ...],
    knots_y: tuple[float, ...],
    bounds: tuple[float, float, float, float],
    geometry_map: str,
    nurbs_weights: tuple[float, ...],
) -> None:
    nodes_1d, weights_1d = pg.gauss_legendre_01(max(2, spline_degree + 1))

    for condition in form_ir.boundary_conditions:
        if condition.kind != "natural" or isclose(condition.value, 0.0):
            continue

        selector = _resolve_boundary_selector(
            condition.boundary,
            metadata=form_ir.metadata,
        )
        segments = _selected_boundary_segments(
            panel,
            selector=selector,
            bounds=bounds,
        )

        for start, end in segments:
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            segment_length = hypot(dx, dy)
            if segment_length <= 1.0e-18:
                continue

            for t, w in zip(nodes_1d, weights_1d, strict=True):
                sample_x = start[0] + t * dx
                sample_y = start[1] + t * dy
                terms = _basis_terms_at_point_for_geometry_map(
                    x=sample_x,
                    y=sample_y,
                    resolution=resolution,
                    spline_degree=spline_degree,
                    n_basis_axis=n_basis_axis,
                    knots_x=knots_x,
                    knots_y=knots_y,
                    bounds=bounds,
                    geometry_map=geometry_map,
                    nurbs_weights=nurbs_weights,
                )
                edge_weight = w * segment_length
                for index, value, _gx, _gy in terms:
                    rhs[index] += edge_weight * condition.value * value


def assemble_iga(
    form_ir: WeakFormIR,
    *,
    panel: TrimmedPanel2D,
    resolution: int,
    spline_degree: int,
    quadrature_order: int,
    backend_mode: pg.BackendMode,
    bounds: tuple[float, float, float, float] | None,
) -> IGAAssemblyResult:
    """Assemble a scalar trimmed-domain system from the shared form IR."""

    if resolution < 1:
        raise ValueError("resolution must be positive")
    if spline_degree < 1:
        raise ValueError("spline_degree must be positive")
    if quadrature_order < 1:
        raise ValueError("quadrature_order must be positive")
    if backend_mode not in {"jplus", "folded"}:
        raise ValueError(
            f"unsupported backend_mode {backend_mode!r}; expected 'jplus' or 'folded'"
        )

    diffusion = _term_scalar(form_ir, "diffusion")
    mass = _term_scalar(form_ir, "mass")
    reaction = _term_scalar(form_ir, "reaction")
    source = _source_fn(form_ir)

    panel_polygon = awb2d._panel_polygon(panel)
    effective_bounds = awb2d._resolve_panel_bounds(panel, bounds)
    clipped = awb2d._cached_clipped_cells(panel_polygon, resolution, effective_bounds)

    n_basis_axis = resolution + spline_degree
    dof_count = n_basis_axis * n_basis_axis
    matrix_rows: list[dict[int, float]] = [dict() for _ in range(dof_count)]
    rhs = [0.0 for _ in range(dof_count)]
    active_mask = [False for _ in range(dof_count)]

    knots_x = pg._open_uniform_knots(num_elements=resolution, degree=spline_degree)
    knots_y = pg._open_uniform_knots(num_elements=resolution, degree=spline_degree)
    geometry_map = _normalized_geometry_map(form_ir)
    interface_lowering = _lower_multipatch_interfaces(form_ir)
    if geometry_map == "nurbs":
        nurbs_weights = _parse_nurbs_weights(form_ir.metadata, dof_count=dof_count)
    else:
        nurbs_weights = ()
    execution_path = _execution_path_for_iga(
        geometry_map=geometry_map,
        has_multipatch=bool(interface_lowering),
    )

    for clip in clipped:
        if clip.kind == "outside":
            continue

        ix = clip.cell.ix
        iy = clip.cell.iy
        for local_j in range(spline_degree + 1):
            global_j = iy + local_j
            if global_j < 0 or global_j >= n_basis_axis:
                continue
            row_base = global_j * n_basis_axis
            for local_i in range(spline_degree + 1):
                global_i = ix + local_i
                if global_i < 0 or global_i >= n_basis_axis:
                    continue
                active_mask[row_base + global_i] = True

        samples = pg._cell_rule_samples(
            clip,
            backend_mode=backend_mode,
            order=quadrature_order,
        )
        for x, y, weight in samples:
            terms = _basis_terms_at_point_for_geometry_map(
                x=x,
                y=y,
                resolution=resolution,
                spline_degree=spline_degree,
                n_basis_axis=n_basis_axis,
                knots_x=knots_x,
                knots_y=knots_y,
                bounds=effective_bounds,
                geometry_map=geometry_map,
                nurbs_weights=nurbs_weights,
            )
            source_value = source(x, y)

            for global_a, value_a, grad_ax, grad_ay in terms:
                rhs[global_a] += weight * source_value * value_a
                row = matrix_rows[global_a]
                for global_b, value_b, grad_bx, grad_by in terms:
                    stiffness = 0.0
                    if not isclose(diffusion, 0.0):
                        stiffness += diffusion * (grad_ax * grad_bx + grad_ay * grad_by)
                    if not isclose(mass, 0.0):
                        stiffness += mass * value_a * value_b
                    if not isclose(reaction, 0.0):
                        stiffness += reaction * value_a * value_b
                    stiffness *= weight
                    if abs(stiffness) <= 1.0e-20:
                        continue
                    pg._add_to_sparse_row(row, global_b, stiffness)

    _add_multipatch_interface_coupling(
        matrix_rows,
        form_ir=form_ir,
        panel=panel,
        resolution=resolution,
        spline_degree=spline_degree,
        quadrature_order=quadrature_order,
        n_basis_axis=n_basis_axis,
        knots_x=knots_x,
        knots_y=knots_y,
        bounds=effective_bounds,
        geometry_map=geometry_map,
        nurbs_weights=nurbs_weights,
        interface_lowering=interface_lowering,
    )

    _add_natural_rhs(
        rhs,
        form_ir=form_ir,
        panel=panel,
        resolution=resolution,
        spline_degree=spline_degree,
        n_basis_axis=n_basis_axis,
        knots_x=knots_x,
        knots_y=knots_y,
        bounds=effective_bounds,
        geometry_map=geometry_map,
        nurbs_weights=nurbs_weights,
    )

    fixed_values: dict[int, float] = {}
    for index, active in enumerate(active_mask):
        if not active:
            fixed_values[index] = 0.0

    for condition in form_ir.boundary_conditions:
        if condition.kind != "essential":
            continue
        selector = _resolve_boundary_selector(
            condition.boundary,
            metadata=form_ir.metadata,
        )
        for index in range(dof_count):
            if not active_mask[index]:
                continue
            if _is_boundary_dof(index, n_basis_axis=n_basis_axis, boundary=selector):
                fixed_values[index] = condition.value

    _apply_essential_values(matrix_rows, rhs, fixed_values=fixed_values)
    return IGAAssemblyResult(
        matrix_rows=tuple(matrix_rows),
        rhs=tuple(rhs),
        bounds=effective_bounds,
        geometry_map=geometry_map,
        execution_path=execution_path,
        interface_lowering=interface_lowering,
    )
