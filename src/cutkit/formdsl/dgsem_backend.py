"""IR-to-DG-SEM lowering with explicit overlay prerequisites."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from .diagnostics import PrerequisiteError
from .ir import WeakFormIR


@dataclass(frozen=True)
class DGSEMLoweringResult:
    """Deterministic DG-SEM lowering payload."""

    volume_terms: tuple[str, ...]
    trace_terms: tuple[str, ...]
    flux_family: str
    overlay_version: int


def _format_float(value: float) -> str:
    return f"{value:.16g}"


def _source_signature(
    term_source: float | Callable[[float, float], float] | None,
) -> str:
    if callable(term_source):
        module = getattr(term_source, "__module__", "")
        qualname = getattr(term_source, "__qualname__", type(term_source).__name__)
        return f"callable:{module}.{qualname}" if module else f"callable:{qualname}"
    if term_source is None:
        return "implicit:1"
    return f"const:{_format_float(float(term_source))}"


def lower_dgsem(
    form_ir: WeakFormIR,
    *,
    overlay_payload: dict[str, object] | None,
) -> DGSEMLoweringResult:
    """Lower shared IR into a DG-SEM-oriented payload."""

    if overlay_payload is None:
        raise PrerequisiteError("dgsem backend requires meshmode cut-overlay payload")

    raw_version = overlay_payload.get("contract_version", 0)
    if isinstance(raw_version, bool):
        version = int(raw_version)
    elif isinstance(raw_version, int):
        version = raw_version
    elif isinstance(raw_version, float):
        if not raw_version.is_integer():
            raise PrerequisiteError(
                "overlay payload contract_version must be an integer value"
            )
        version = int(raw_version)
    elif isinstance(raw_version, str):
        try:
            version = int(raw_version)
        except ValueError as exc:
            raise PrerequisiteError(
                "overlay payload contract_version must be numeric"
            ) from exc
    else:
        raise PrerequisiteError("overlay payload contract_version must be numeric")
    if version < 1:
        raise PrerequisiteError(
            "dgsem backend requires meshmode cut-overlay contract_version >= 1"
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
    )
