"""Backend support matrix for form lowering."""

from __future__ import annotations

from .diagnostics import CapabilityDiagnostic, CapabilityError
from .ir import WeakFormIR

_SUPPORTED_TERM_KINDS: dict[str, tuple[str, ...]] = {
    "iga": ("diffusion", "mass", "reaction", "source"),
    "dgsem": ("diffusion", "mass", "reaction", "source"),
}
_SUPPORTED_BCS: dict[str, tuple[str, ...]] = {
    "iga": ("essential", "natural"),
    "dgsem": ("essential", "natural"),
}
_SUPPORTED_GEOMETRY_MAPS: dict[str, tuple[str, ...]] = {
    "iga": ("bspline", "nurbs"),
    "dgsem": ("bspline",),
}
_SUPPORTED_VALUE_SHAPES: dict[str, tuple[str, ...]] = {
    "iga": ("()",),
    "dgsem": ("()", "(N,)"),
}
_SUPPORTED_MULTIPATCH_INTERFACE: dict[str, bool] = {
    "iga": True,
    "dgsem": False,
}


def _is_supported_value_shape(value_shape: tuple[int, ...], *, backend: str) -> bool:
    if value_shape == ():
        return True
    return backend == "dgsem" and len(value_shape) == 1


def _normalized_geometry_map(form_ir: WeakFormIR) -> str:
    raw_geometry_map = str(form_ir.metadata.get("geometry_map", "bspline")).strip()
    if not raw_geometry_map:
        return "bspline"
    return raw_geometry_map.lower()


def capability_matrix() -> dict[str, dict[str, tuple[str, ...]]]:
    """Return the supported form subset by backend."""

    return {
        backend: {
            "terms": terms,
            "boundary_conditions": _SUPPORTED_BCS[backend],
            "geometry_maps": _SUPPORTED_GEOMETRY_MAPS[backend],
            "value_shapes": _SUPPORTED_VALUE_SHAPES[backend],
            "multipatch_interfaces": (
                ("descriptor",) if _SUPPORTED_MULTIPATCH_INTERFACE[backend] else ()
            ),
        }
        for backend, terms in _SUPPORTED_TERM_KINDS.items()
    }


def check_support(
    form_ir: WeakFormIR,
    *,
    backend: str,
    strict: bool,
) -> tuple[CapabilityDiagnostic, ...]:
    """Validate a form IR against backend capabilities."""

    diagnostics: list[CapabilityDiagnostic] = []
    supported_terms = _SUPPORTED_TERM_KINDS.get(backend)
    supported_bcs = _SUPPORTED_BCS.get(backend)
    supported_geometry_maps = _SUPPORTED_GEOMETRY_MAPS.get(backend)
    supported_value_shapes = _SUPPORTED_VALUE_SHAPES.get(backend)
    if (
        supported_terms is None
        or supported_bcs is None
        or supported_geometry_maps is None
        or supported_value_shapes is None
    ):
        raise CapabilityError(
            CapabilityDiagnostic(
                code="unsupported_backend",
                backend=backend,
                detail="backend is not supported",
                alternatives=tuple(sorted(_SUPPORTED_TERM_KINDS)),
            )
        )

    for term in form_ir.terms:
        if term.kind in supported_terms:
            continue
        diagnostics.append(
            CapabilityDiagnostic(
                code="unsupported_term",
                backend=backend,
                detail=f"term '{term.kind}' is not supported",
                alternatives=supported_terms,
            )
        )

    for condition in form_ir.boundary_conditions:
        if condition.kind in supported_bcs:
            continue
        diagnostics.append(
            CapabilityDiagnostic(
                code="unsupported_boundary_condition",
                backend=backend,
                detail=f"boundary condition '{condition.kind}' is not supported",
                alternatives=supported_bcs,
            )
        )

    geometry_map = _normalized_geometry_map(form_ir)
    if geometry_map not in supported_geometry_maps:
        diagnostics.append(
            CapabilityDiagnostic(
                code="unsupported_geometry_map",
                backend=backend,
                detail=(
                    f"geometry_map {geometry_map!r} is not supported "
                    f"for backend {backend!r}"
                ),
                alternatives=supported_geometry_maps,
            )
        )

    if not _is_supported_value_shape(form_ir.value_shape, backend=backend):
        diagnostics.append(
            CapabilityDiagnostic(
                code="unsupported_value_shape",
                backend=backend,
                detail=(
                    f"value_shape {form_ir.value_shape!r} is not supported "
                    f"for backend {backend!r}"
                ),
                alternatives=supported_value_shapes,
            )
        )

    if form_ir.multipatch is not None and not _SUPPORTED_MULTIPATCH_INTERFACE[backend]:
        alternatives = tuple(
            sorted(
                supported_backend
                for supported_backend, supports_multipatch in _SUPPORTED_MULTIPATCH_INTERFACE.items()
                if supports_multipatch
            )
        )
        diagnostics.append(
            CapabilityDiagnostic(
                code="unsupported_multipatch_interface",
                backend=backend,
                detail=(
                    "multipatch interface descriptors are not supported "
                    f"for backend {backend!r}"
                ),
                alternatives=alternatives,
            )
        )

    if strict and diagnostics:
        raise CapabilityError(diagnostics[0])

    return tuple(diagnostics)
