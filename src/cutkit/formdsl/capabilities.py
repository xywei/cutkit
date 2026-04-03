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


def capability_matrix() -> dict[str, dict[str, tuple[str, ...]]]:
    """Return the supported scalar subset by backend."""

    return {
        backend: {
            "terms": terms,
            "boundary_conditions": _SUPPORTED_BCS[backend],
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
    if supported_terms is None or supported_bcs is None:
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

    if strict and diagnostics:
        raise CapabilityError(diagnostics[0])

    return tuple(diagnostics)
