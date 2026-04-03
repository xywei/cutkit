"""UFL adapter entrypoints for method-neutral form IR."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .ir import BackendName, BoundaryCondition, Term, WeakFormIR

_VALID_BOUNDARIES = {"all", "left", "right", "bottom", "top"}


def _validate_ir_boundaries(boundary_conditions: tuple[BoundaryCondition, ...]) -> None:
    for index, condition in enumerate(boundary_conditions):
        if condition.boundary in _VALID_BOUNDARIES:
            continue
        raise ValueError(
            f"boundary condition at index {index} has unsupported boundary {condition.boundary!r}"
        )


def parse_form(
    form: WeakFormIR | Mapping[str, Any] | Any,
    *,
    backend: BackendName,
) -> WeakFormIR:
    """Parse a supported form object into ``WeakFormIR``.

    The adapter accepts a native ``WeakFormIR`` or a deterministic dictionary
    payload for minimal scalar forms.
    """

    del backend

    if isinstance(form, WeakFormIR):
        _validate_ir_boundaries(form.boundary_conditions)
        return form

    module_name = type(form).__module__
    if module_name.startswith("ufl"):
        raise ValueError(
            "UFL objects require optional parser integration; provide dict/IR input"
        )

    if not isinstance(form, Mapping):
        raise TypeError("form must be WeakFormIR or mapping payload")

    trial_space = str(form.get("trial_space", "P1"))
    test_space = str(form.get("test_space", "P1"))

    raw_terms = form.get("terms")
    if not isinstance(raw_terms, list) or not raw_terms:
        raise ValueError("form payload must provide a non-empty 'terms' list")

    terms: list[Term] = []
    for index, raw_term in enumerate(raw_terms):
        if not isinstance(raw_term, Mapping):
            raise ValueError(f"term at index {index} must be a mapping")
        kind = str(raw_term.get("kind", "")).strip()
        if not kind:
            raise ValueError(f"term at index {index} is missing 'kind'")

        coefficient = float(raw_term.get("coefficient", 1.0))
        source = raw_term.get("source")
        if source is not None and not callable(source):
            source = float(source)
        terms.append(Term(kind=kind, coefficient=coefficient, source=source))

    raw_bcs = form.get("boundary_conditions", [])
    if not isinstance(raw_bcs, list):
        raise ValueError("'boundary_conditions' must be a list")
    boundary_conditions: list[BoundaryCondition] = []
    for index, raw_bc in enumerate(raw_bcs):
        if not isinstance(raw_bc, Mapping):
            raise ValueError(f"boundary condition at index {index} must be a mapping")
        kind = str(raw_bc.get("kind", "")).strip()
        if not kind:
            raise ValueError(f"boundary condition at index {index} is missing 'kind'")
        boundary = str(raw_bc.get("boundary", "all"))
        if boundary not in _VALID_BOUNDARIES:
            raise ValueError(
                f"boundary condition at index {index} has unsupported boundary {boundary!r}"
            )
        boundary_conditions.append(
            BoundaryCondition(
                kind=kind,
                value=float(raw_bc.get("value", 0.0)),
                boundary=boundary,
            )
        )

    metadata: dict[str, str] = {}
    raw_meta = form.get("metadata", {})
    if isinstance(raw_meta, Mapping):
        metadata = {str(key): str(value) for key, value in raw_meta.items()}

    form_ir = WeakFormIR(
        trial_space=trial_space,
        test_space=test_space,
        terms=tuple(terms),
        boundary_conditions=tuple(boundary_conditions),
        metadata=metadata,
    )
    _validate_ir_boundaries(form_ir.boundary_conditions)
    return form_ir
