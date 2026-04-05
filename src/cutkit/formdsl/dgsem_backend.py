"""IR-to-DG-SEM lowering with explicit overlay prerequisites."""

from __future__ import annotations

from dataclasses import dataclass
from math import isfinite
from typing import Callable, Literal, cast

from cutkit.io.meshmode_overlay import ElementId, MeshmodeCutOverlay, OverlayStatus

from .diagnostics import PrerequisiteError
from .ir import WeakFormIR

_BLOCKING_OVERLAY_STATUSES = {
    "invalid_box",
    "backend_error",
    "mapping_mismatch",
    "orientation_mismatch",
}

DGSEMBuildingBlock = Literal[
    "grudge.op.mass",
    "grudge.op.inverse_mass",
    "grudge.op.face_mass",
    "grudge.op.project",
    "grudge.op.interior_trace_pairs",
    "grudge.op.bdry_trace_pair",
    "grudge.op.weak_local_grad",
    "grudge.op.weak_local_div",
]
DGSEMFluxFamily = Literal["sipg", "central", "upwind"]
DGSEMLoweringDiagnosticCode = Literal[
    "unsupported_flux_family",
    "invalid_penalty",
    "unsupported_term",
]

_SUPPORTED_FLUX_FAMILIES: tuple[DGSEMFluxFamily, ...] = ("sipg", "central", "upwind")

_DIFFUSION_OPERATOR_CHAIN: tuple[DGSEMBuildingBlock, ...] = (
    "grudge.op.weak_local_grad",
    "grudge.op.weak_local_div",
    "grudge.op.inverse_mass",
)
_MASS_OPERATOR_CHAIN: tuple[DGSEMBuildingBlock, ...] = (
    "grudge.op.mass",
    "grudge.op.inverse_mass",
)
_TRACE_OPERATOR_CHAIN: tuple[DGSEMBuildingBlock, ...] = (
    "grudge.op.project",
    "grudge.op.face_mass",
)
_INTERIOR_FLUX_OPERATOR_CHAIN: dict[DGSEMFluxFamily, tuple[DGSEMBuildingBlock, ...]] = {
    "sipg": (
        "grudge.op.interior_trace_pairs",
        "grudge.op.project",
        "grudge.op.face_mass",
        "grudge.op.inverse_mass",
    ),
    "central": (
        "grudge.op.interior_trace_pairs",
        "grudge.op.project",
        "grudge.op.face_mass",
    ),
    "upwind": (
        "grudge.op.interior_trace_pairs",
        "grudge.op.project",
        "grudge.op.face_mass",
    ),
}
_BOUNDARY_FLUX_OPERATOR_CHAIN: tuple[DGSEMBuildingBlock, ...] = (
    "grudge.op.bdry_trace_pair",
    "grudge.op.project",
    "grudge.op.face_mass",
    "grudge.op.inverse_mass",
)


@dataclass(frozen=True)
class DGSEMOverlayDiagnostic:
    """Structured diagnostic forwarded from meshmode overlay validation."""

    code: str
    detail: str
    target_element_id: ElementId | None = None
    source_element_id: ElementId | None = None


@dataclass(frozen=True)
class DGSEMLoweringDiagnostic:
    """Deterministic diagnostic emitted during DG-specific lowering."""

    code: DGSEMLoweringDiagnosticCode
    detail: str


@dataclass(frozen=True)
class DGSEMVolumeLowering:
    """One DG volume-form lowering entry tied to grudge operator blocks."""

    kind: str
    coefficient: float
    operator_chain: tuple[DGSEMBuildingBlock, ...]
    source_signature: str | None = None


@dataclass(frozen=True)
class DGSEMTraceLowering:
    """One DG trace/boundary lowering entry."""

    kind: str
    boundary: str
    value: float
    operator_chain: tuple[DGSEMBuildingBlock, ...]


@dataclass(frozen=True)
class DGSEMFluxLowering:
    """One DG flux lowering entry built from grudge operator blocks."""

    family: DGSEMFluxFamily
    role: str
    boundary: str | None
    diffusion_coefficient: float
    boundary_value: float | None
    penalty: float | None
    operator_chain: tuple[DGSEMBuildingBlock, ...]


@dataclass(frozen=True)
class DGSEMLoweringResult:
    """Deterministic DG-SEM lowering payload."""

    volume_terms: tuple[str, ...]
    trace_terms: tuple[str, ...]
    flux_family: str
    overlay_version: int
    overlay_statuses: tuple[OverlayStatus, ...]
    overlay_diagnostics: tuple[DGSEMOverlayDiagnostic, ...]
    lowering_diagnostics: tuple[DGSEMLoweringDiagnostic, ...]
    volume_lowering: tuple[DGSEMVolumeLowering, ...]
    trace_lowering: tuple[DGSEMTraceLowering, ...]
    flux_lowering: tuple[DGSEMFluxLowering, ...]
    flux_terms: tuple[str, ...]


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


def _parse_flux_family(
    form_ir: WeakFormIR,
    *,
    strict: bool,
) -> tuple[DGSEMFluxFamily, tuple[DGSEMLoweringDiagnostic, ...]]:
    diagnostics: list[DGSEMLoweringDiagnostic] = []

    raw_flux_family = str(form_ir.metadata.get("dg_flux", "sipg")).strip().lower()
    if raw_flux_family in _SUPPORTED_FLUX_FAMILIES:
        return cast(DGSEMFluxFamily, raw_flux_family), ()

    diagnostic = DGSEMLoweringDiagnostic(
        code="unsupported_flux_family",
        detail=(
            f"unsupported dg_flux {raw_flux_family!r}; "
            f"supported: {', '.join(_SUPPORTED_FLUX_FAMILIES)}"
        ),
    )
    if strict:
        raise PrerequisiteError(f"dgsem backend {diagnostic.detail}")
    diagnostics.append(diagnostic)
    return "sipg", tuple(diagnostics)


def _parse_penalty(
    form_ir: WeakFormIR,
    *,
    strict: bool,
) -> tuple[float, tuple[DGSEMLoweringDiagnostic, ...]]:
    diagnostics: list[DGSEMLoweringDiagnostic] = []
    raw_penalty = form_ir.metadata.get("dg_penalty", 1.0)

    try:
        penalty = float(raw_penalty)
    except (TypeError, ValueError) as exc:
        diagnostic = DGSEMLoweringDiagnostic(
            code="invalid_penalty",
            detail=f"invalid dg_penalty value {raw_penalty!r}; expected positive float",
        )
        if strict:
            raise PrerequisiteError(f"dgsem backend {diagnostic.detail}") from exc
        diagnostics.append(diagnostic)
        return 1.0, tuple(diagnostics)

    if not isfinite(penalty) or penalty <= 0.0:
        diagnostic = DGSEMLoweringDiagnostic(
            code="invalid_penalty",
            detail=f"invalid dg_penalty value {raw_penalty!r}; expected positive float",
        )
        if strict:
            raise PrerequisiteError(f"dgsem backend {diagnostic.detail}")
        diagnostics.append(diagnostic)
        return 1.0, tuple(diagnostics)

    return penalty, tuple(diagnostics)


def lower_dgsem(
    form_ir: WeakFormIR,
    *,
    overlay_payload: MeshmodeCutOverlay | None,
    strict: bool,
) -> DGSEMLoweringResult:
    """Lower shared IR into a DG-SEM-oriented payload."""

    if overlay_payload is None:
        raise PrerequisiteError("dgsem backend requires meshmode cut-overlay payload")
    if not isinstance(overlay_payload, MeshmodeCutOverlay):
        raise PrerequisiteError("dgsem backend requires MeshmodeCutOverlay payload")

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
    volume_lowering: list[DGSEMVolumeLowering] = []
    diffusion_coefficients: list[float] = []
    term_diagnostics: list[DGSEMLoweringDiagnostic] = []
    for term in form_ir.terms:
        coefficient = float(term.coefficient)
        if term.kind == "source":
            source_signature = _source_signature(term.source)
            volume_terms.append(
                f"source:{_format_float(coefficient)}:{source_signature}"
            )
            volume_lowering.append(
                DGSEMVolumeLowering(
                    kind="source",
                    coefficient=coefficient,
                    operator_chain=_MASS_OPERATOR_CHAIN,
                    source_signature=source_signature,
                )
            )
            continue
        if term.kind == "diffusion":
            volume_terms.append(f"{term.kind}:{_format_float(coefficient)}")
            diffusion_coefficients.append(coefficient)
            volume_lowering.append(
                DGSEMVolumeLowering(
                    kind=term.kind,
                    coefficient=coefficient,
                    operator_chain=_DIFFUSION_OPERATOR_CHAIN,
                )
            )
        elif term.kind in {"mass", "reaction"}:
            volume_terms.append(f"{term.kind}:{_format_float(coefficient)}")
            volume_lowering.append(
                DGSEMVolumeLowering(
                    kind=term.kind,
                    coefficient=coefficient,
                    operator_chain=_MASS_OPERATOR_CHAIN,
                )
            )
        else:
            diagnostic = DGSEMLoweringDiagnostic(
                code="unsupported_term",
                detail=f"unsupported dgsem term kind {term.kind!r} omitted from lowering",
            )
            if strict:
                raise PrerequisiteError(f"dgsem backend {diagnostic.detail}")
            term_diagnostics.append(diagnostic)

    if diffusion_coefficients:
        flux_family, flux_family_diagnostics = _parse_flux_family(
            form_ir, strict=strict
        )
        if flux_family == "sipg":
            penalty, penalty_diagnostics = _parse_penalty(form_ir, strict=strict)
        else:
            penalty = 1.0
            penalty_diagnostics = ()
        lowering_diagnostics_list = list(flux_family_diagnostics + penalty_diagnostics)
    else:
        raw_flux_family = str(form_ir.metadata.get("dg_flux", "sipg")).strip().lower()
        if raw_flux_family in _SUPPORTED_FLUX_FAMILIES:
            flux_family = cast(DGSEMFluxFamily, raw_flux_family)
        else:
            flux_family = "sipg"
        penalty = 1.0
        lowering_diagnostics_list = []

    lowering_diagnostics_list.extend(term_diagnostics)

    trace_terms: list[str] = []
    trace_lowering: list[DGSEMTraceLowering] = []
    flux_lowering: list[DGSEMFluxLowering] = []
    for bc in form_ir.boundary_conditions:
        if bc.kind == "natural":
            value = float(bc.value)
            trace_terms.append(f"neumann:{bc.boundary}:{_format_float(value)}")
            trace_lowering.append(
                DGSEMTraceLowering(
                    kind="neumann",
                    boundary=bc.boundary,
                    value=value,
                    operator_chain=_TRACE_OPERATOR_CHAIN,
                )
            )
            for coefficient in diffusion_coefficients:
                flux_lowering.append(
                    DGSEMFluxLowering(
                        family=flux_family,
                        role="boundary_neumann",
                        boundary=bc.boundary,
                        diffusion_coefficient=coefficient,
                        boundary_value=value,
                        penalty=penalty if flux_family == "sipg" else None,
                        operator_chain=_BOUNDARY_FLUX_OPERATOR_CHAIN,
                    )
                )
        elif bc.kind == "essential":
            value = float(bc.value)
            trace_terms.append(f"dirichlet:{bc.boundary}:{_format_float(value)}")
            trace_lowering.append(
                DGSEMTraceLowering(
                    kind="dirichlet",
                    boundary=bc.boundary,
                    value=value,
                    operator_chain=_TRACE_OPERATOR_CHAIN,
                )
            )
            for coefficient in diffusion_coefficients:
                flux_lowering.append(
                    DGSEMFluxLowering(
                        family=flux_family,
                        role="boundary_dirichlet",
                        boundary=bc.boundary,
                        diffusion_coefficient=coefficient,
                        boundary_value=value,
                        penalty=penalty if flux_family == "sipg" else None,
                        operator_chain=_BOUNDARY_FLUX_OPERATOR_CHAIN,
                    )
                )

    for coefficient in diffusion_coefficients:
        flux_lowering.append(
            DGSEMFluxLowering(
                family=flux_family,
                role="interior",
                boundary=None,
                diffusion_coefficient=coefficient,
                boundary_value=None,
                penalty=penalty if flux_family == "sipg" else None,
                operator_chain=_INTERIOR_FLUX_OPERATOR_CHAIN[flux_family],
            )
        )

    flux_terms = tuple(
        sorted(
            f"{entry.family}:{entry.role}:{entry.boundary or 'interior'}:"
            f"{_format_float(entry.diffusion_coefficient)}:"
            f"{_format_float(entry.boundary_value) if entry.boundary_value is not None else 'none'}:"
            f"{_format_float(entry.penalty) if entry.penalty is not None else 'none'}"
            for entry in flux_lowering
        )
    )

    return DGSEMLoweringResult(
        volume_terms=tuple(sorted(volume_terms)),
        trace_terms=tuple(sorted(trace_terms)),
        flux_family=flux_family,
        overlay_version=version,
        overlay_statuses=overlay_statuses,
        overlay_diagnostics=overlay_diagnostics,
        lowering_diagnostics=tuple(lowering_diagnostics_list),
        volume_lowering=tuple(
            sorted(
                volume_lowering,
                key=lambda entry: (
                    entry.kind,
                    _format_float(entry.coefficient),
                    entry.source_signature or "",
                ),
            )
        ),
        trace_lowering=tuple(
            sorted(
                trace_lowering,
                key=lambda entry: (
                    entry.kind,
                    entry.boundary,
                    _format_float(entry.value),
                ),
            )
        ),
        flux_lowering=tuple(
            sorted(
                flux_lowering,
                key=lambda entry: (
                    entry.role,
                    entry.boundary or "",
                    _format_float(entry.diffusion_coefficient),
                    _format_float(entry.boundary_value)
                    if entry.boundary_value is not None
                    else "",
                ),
            )
        ),
        flux_terms=flux_terms,
    )
