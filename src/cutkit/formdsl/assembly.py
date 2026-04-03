"""Shared frontend for backend-selectable form assembly."""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from cutkit.evals.poisson_galerkin import BackendMode
from cutkit.geometry import TrimmedPanel2D

from .adapter import parse_form
from .capabilities import check_support
from .dgsem_backend import DGSEMLoweringResult, lower_dgsem
from .ir import BackendName, WeakFormIR
from .iga_backend import IGAAssemblyResult, assemble_iga


@dataclass(frozen=True)
class AssemblyResult:
    """Backend-tagged assembly output."""

    backend: BackendName
    ir: WeakFormIR
    diagnostics: tuple[Any, ...]
    payload: IGAAssemblyResult | DGSEMLoweringResult


def assemble_form(
    form: WeakFormIR | Mapping[str, object],
    *,
    backend: BackendName,
    strict: bool = True,
    panel: TrimmedPanel2D | None = None,
    resolution: int = 8,
    spline_degree: int = 2,
    quadrature_order: int = 4,
    backend_mode: BackendMode = "jplus",
    bounds: tuple[float, float, float, float] | None = None,
    overlay_payload: Mapping[str, object] | None = None,
) -> AssemblyResult:
    """Parse and lower one weak form into the selected backend."""

    form_ir = parse_form(form, backend=backend)
    diagnostics = check_support(form_ir, backend=backend, strict=strict)

    payload: IGAAssemblyResult | DGSEMLoweringResult
    if backend == "iga":
        if panel is None:
            raise ValueError("panel is required for iga assembly")
        payload = assemble_iga(
            form_ir,
            panel=panel,
            resolution=resolution,
            spline_degree=spline_degree,
            quadrature_order=quadrature_order,
            backend_mode=backend_mode,
            bounds=bounds,
        )
    else:
        payload = lower_dgsem(
            form_ir,
            overlay_payload=dict(overlay_payload)
            if overlay_payload is not None
            else None,
        )

    return AssemblyResult(
        backend=backend,
        ir=form_ir,
        diagnostics=diagnostics,
        payload=payload,
    )
