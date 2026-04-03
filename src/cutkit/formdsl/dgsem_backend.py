"""IR-to-DG-SEM lowering with explicit overlay prerequisites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from cutkit.io.meshmode_overlay import ElementId, MeshmodeCutOverlay, OverlayStatus

from .diagnostics import PrerequisiteError
from .ir import WeakFormIR

_BLOCKING_OVERLAY_STATUSES = {
    "invalid_box",
    "backend_error",
    "mapping_mismatch",
    "orientation_mismatch",
}


@dataclass(frozen=True)
class DGSEMOverlayDiagnostic:
    """Structured diagnostic forwarded from meshmode overlay validation."""

    code: str
    detail: str
    target_element_id: ElementId | None = None
    source_element_id: ElementId | None = None


@dataclass(frozen=True)
class DGSEMLoweringResult:
    """Deterministic DG-SEM lowering payload."""

    volume_terms: tuple[str, ...]
    trace_terms: tuple[str, ...]
    flux_family: str
    overlay_version: int
    overlay_statuses: tuple[OverlayStatus, ...]
    overlay_diagnostics: tuple[DGSEMOverlayDiagnostic, ...]


def _format_float(value: float) -> str:
    return f"{value:.16g}"


def _closure_value_signature(value: object) -> str:
    if value is None:
        return "none"
    if isinstance(value, bool):
        return f"bool:{int(value)}"
    if isinstance(value, int):
        return f"int:{value}"
    if isinstance(value, float):
        return f"float:{_format_float(value)}"
    if isinstance(value, str):
        return f"str:{value}"
    if callable(value):
        module = getattr(value, "__module__", "")
        qualname = getattr(value, "__qualname__", type(value).__name__)
        return f"callable:{module}.{qualname}" if module else f"callable:{qualname}"
    return f"type:{type(value).__module__}.{type(value).__qualname__}"


def _callable_closure_signature(func: Callable[[float, float], float]) -> str:
    closure = getattr(func, "__closure__", None)
    if not closure:
        return ""

    code = getattr(func, "__code__", None)
    freevars = tuple(getattr(code, "co_freevars", ())) if code is not None else ()
    parts: list[str] = []
    for index, cell in enumerate(closure):
        name = freevars[index] if index < len(freevars) else f"var{index}"
        try:
            content = cell.cell_contents
        except ValueError:
            content = None
        parts.append(f"{name}={_closure_value_signature(content)}")
    return "|".join(parts)


def _source_signature(
    term_source: float | Callable[[float, float], float] | None,
) -> str:
    if callable(term_source):
        module = getattr(term_source, "__module__", "")
        qualname = getattr(term_source, "__qualname__", type(term_source).__name__)
        base = f"callable:{module}.{qualname}" if module else f"callable:{qualname}"
        closure = _callable_closure_signature(term_source)
        if closure:
            return f"{base}[{closure}]"
        return base
    if term_source is None:
        return "implicit:1"
    return f"const:{_format_float(float(term_source))}"


def lower_dgsem(
    form_ir: WeakFormIR,
    *,
    overlay_payload: MeshmodeCutOverlay | None,
    strict: bool,
) -> DGSEMLoweringResult:
    """Lower shared IR into a DG-SEM-oriented payload."""

    if overlay_payload is None:
        raise PrerequisiteError("dgsem backend requires meshmode cut-overlay payload")

    raw_version = overlay_payload.contract_version
    if isinstance(raw_version, bool) or not isinstance(raw_version, int):
        raise PrerequisiteError(
            "dgsem backend requires integer meshmode cut-overlay contract_version"
        )
    version = raw_version
    if version < 1:
        raise PrerequisiteError(
            "dgsem backend requires meshmode cut-overlay contract_version >= 1"
        )

    overlay_statuses = overlay_payload.statuses
    overlay_diagnostics = tuple(
        DGSEMOverlayDiagnostic(
            code=diagnostic.code,
            detail=diagnostic.detail,
            target_element_id=diagnostic.target_element_id,
            source_element_id=diagnostic.source_element_id,
        )
        for diagnostic in overlay_payload.diagnostics
    )

    if strict and overlay_diagnostics:
        first = overlay_diagnostics[0]
        raise PrerequisiteError(
            "dgsem backend requires mismatch-free meshmode overlay diagnostics: "
            f"{first.code}"
        )

    if strict:
        for index, status in enumerate(overlay_statuses):
            if status not in _BLOCKING_OVERLAY_STATUSES:
                continue
            target = overlay_payload.target_element_ids[index]
            raise PrerequisiteError(
                "dgsem backend requires viable overlay statuses; "
                f"target {target!r} has status {status!r}"
            )

    volume_terms: list[str] = []
    for term in form_ir.terms:
        if term.kind == "source":
            volume_terms.append(
                f"source:{_format_float(term.coefficient)}:{_source_signature(term.source)}"
            )
            continue
        volume_terms.append(f"{term.kind}:{_format_float(term.coefficient)}")

    trace_terms: list[str] = []
    for bc in form_ir.boundary_conditions:
        if bc.kind == "natural":
            trace_terms.append(f"neumann:{bc.boundary}:{_format_float(bc.value)}")
        elif bc.kind == "essential":
            trace_terms.append(f"dirichlet:{bc.boundary}:{_format_float(bc.value)}")

    flux_family = str(form_ir.metadata.get("dg_flux", "sipg"))
    return DGSEMLoweringResult(
        volume_terms=tuple(sorted(volume_terms)),
        trace_terms=tuple(sorted(trace_terms)),
        flux_family=flux_family,
        overlay_version=version,
        overlay_statuses=overlay_statuses,
        overlay_diagnostics=overlay_diagnostics,
    )
