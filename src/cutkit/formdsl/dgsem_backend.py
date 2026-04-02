"""IR-to-DG-SEM lowering with explicit overlay prerequisites."""

from __future__ import annotations

from dataclasses import dataclass

from .diagnostics import PrerequisiteError
from .ir import WeakFormIR


@dataclass(frozen=True)
class DGSEMLoweringResult:
    """Deterministic DG-SEM lowering payload."""

    volume_terms: tuple[str, ...]
    trace_terms: tuple[str, ...]
    flux_family: str
    overlay_version: int


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
        version = int(raw_version)
    elif isinstance(raw_version, str):
        version = int(raw_version)
    else:
        raise PrerequisiteError("overlay payload contract_version must be numeric")
    if version < 1:
        raise PrerequisiteError(
            "dgsem backend requires meshmode cut-overlay contract_version >= 1"
        )

    volume_terms = tuple(sorted({term.kind for term in form_ir.terms}))
    trace_terms: list[str] = []
    for bc in form_ir.boundary_conditions:
        if bc.kind == "natural":
            trace_terms.append(f"neumann:{bc.boundary}")
        elif bc.kind == "essential":
            trace_terms.append(f"dirichlet:{bc.boundary}")

    flux_family = str(form_ir.metadata.get("dg_flux", "sipg"))
    return DGSEMLoweringResult(
        volume_terms=volume_terms,
        trace_terms=tuple(sorted(set(trace_terms))),
        flux_family=flux_family,
        overlay_version=version,
    )
