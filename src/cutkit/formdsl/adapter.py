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


def _ufl_operands(node: object) -> tuple[object, ...]:
    raw_operands = getattr(node, "ufl_operands", ())
    if isinstance(raw_operands, tuple):
        return raw_operands
    if isinstance(raw_operands, list):
        return tuple(raw_operands)
    return ()


def _ufl_walk(node: object) -> tuple[object, ...]:
    nodes = [node]
    collected: list[object] = []
    while nodes:
        current = nodes.pop()
        collected.append(current)
        nodes.extend(_ufl_operands(current))
    return tuple(collected)


def _ufl_argument_number(node: object) -> int | None:
    if type(node).__name__ != "Argument":
        return None
    number_fn = getattr(node, "number", None)
    if callable(number_fn):
        try:
            return int(number_fn())
        except (TypeError, ValueError):
            return None
    if isinstance(number_fn, int):
        return number_fn
    return None


def _ufl_contains_argument(node: object, *, number: int) -> bool:
    for current in _ufl_walk(node):
        if _ufl_argument_number(current) == number:
            return True
    return False


def _ufl_argument_count(node: object, *, number: int) -> int:
    count = 0
    for current in _ufl_walk(node):
        if _ufl_argument_number(current) == number:
            count += 1
    return count


def _ufl_contains_grad_argument(node: object, *, number: int) -> bool:
    for current in _ufl_walk(node):
        if type(current).__name__ not in {"Grad", "ReferenceGrad"}:
            continue
        operands = _ufl_operands(current)
        if not operands:
            continue
        if _ufl_contains_argument(operands[0], number=number):
            return True
    return False


def _ufl_grad_argument_count(node: object, *, number: int) -> int:
    count = 0
    for current in _ufl_walk(node):
        if type(current).__name__ not in {"Grad", "ReferenceGrad"}:
            continue
        operands = _ufl_operands(current)
        if not operands:
            continue
        if _ufl_contains_argument(operands[0], number=number):
            count += 1
    return count


def _ufl_numeric_value(node: object) -> float | None:
    if isinstance(node, bool):
        return None
    if isinstance(node, (int, float)):
        return float(node)
    if _ufl_operands(node):
        return None
    float_fn = getattr(node, "__float__", None)
    if callable(float_fn):
        try:
            return float(float_fn())
        except (TypeError, ValueError):
            return None
    return None


def _ufl_scalar_factor(node: object) -> float:
    node_type = type(node).__name__
    operands = _ufl_operands(node)

    if node_type == "Product":
        factor = 1.0
        for operand in operands:
            factor *= _ufl_scalar_factor(operand)
        return factor

    if node_type == "Division" and len(operands) == 2:
        numerator = _ufl_scalar_factor(operands[0])
        denominator = _ufl_scalar_factor(operands[1])
        if denominator == 0.0:
            raise ValueError("UFL term contains division by zero scalar factor")
        return numerator / denominator

    if node_type.startswith("Negative") and operands:
        return -_ufl_scalar_factor(operands[0])

    scalar = _ufl_numeric_value(node)
    if scalar is not None:
        return scalar
    return 1.0


def _ufl_split_sum(node: object) -> tuple[object, ...]:
    if type(node).__name__ != "Sum":
        return (node,)
    terms: list[object] = []
    for operand in _ufl_operands(node):
        terms.extend(_ufl_split_sum(operand))
    return tuple(terms)


def _ufl_has_unsupported_leaf(node: object) -> bool:
    for current in _ufl_walk(node):
        if _ufl_operands(current):
            continue
        if _ufl_argument_number(current) is not None:
            continue
        if _ufl_numeric_value(current) is not None:
            continue
        return True
    return False


def _ufl_space_label(argument: object) -> str:
    element_fn = getattr(argument, "ufl_element", None)
    if callable(element_fn):
        return str(element_fn())
    return "P1"


def _parse_ufl_form(form: Any) -> WeakFormIR:
    integrals_fn = getattr(form, "integrals", None)
    if not callable(integrals_fn):
        raise TypeError("UFL form must expose an integrals() method")

    integrals = tuple(integrals_fn())
    if not integrals:
        raise ValueError("UFL form must contain at least one integral")

    trial_space = "P1"
    test_space = "P1"
    arguments_fn = getattr(form, "arguments", None)
    if callable(arguments_fn):
        raw_arguments = tuple(arguments_fn())

        def _argument_sort_key(argument: object) -> int:
            number = _ufl_argument_number(argument)
            return number if number is not None else 99

        arguments = sorted(
            raw_arguments,
            key=_argument_sort_key,
        )
        if arguments:
            test_space = _ufl_space_label(arguments[0])
            trial_space = (
                _ufl_space_label(arguments[1]) if len(arguments) > 1 else test_space
            )

    terms: list[Term] = []
    boundary_conditions: list[BoundaryCondition] = []

    for integral in integrals:
        integral_type_fn = getattr(integral, "integral_type", None)
        integrand_fn = getattr(integral, "integrand", None)
        if not callable(integral_type_fn) or not callable(integrand_fn):
            raise ValueError("UFL integral payload is missing required accessors")

        integral_type = str(integral_type_fn())
        integrand = integrand_fn()
        for summand in _ufl_split_sum(integrand):
            if _ufl_has_unsupported_leaf(summand):
                raise ValueError(
                    "UFL term contains unsupported symbolic coefficients; use mapping/IR payload"
                )

            coefficient = _ufl_scalar_factor(summand)
            has_test = _ufl_contains_argument(summand, number=0)
            has_trial = _ufl_contains_argument(summand, number=1)
            has_grad_test = _ufl_contains_grad_argument(summand, number=0)
            has_grad_trial = _ufl_contains_grad_argument(summand, number=1)
            test_count = _ufl_argument_count(summand, number=0)
            trial_count = _ufl_argument_count(summand, number=1)
            test_grad_count = _ufl_grad_argument_count(summand, number=0)
            trial_grad_count = _ufl_grad_argument_count(summand, number=1)

            if integral_type == "cell":
                if (
                    has_grad_test
                    and has_grad_trial
                    and test_count == 1
                    and trial_count == 1
                    and test_grad_count == 1
                    and trial_grad_count == 1
                ):
                    terms.append(Term(kind="diffusion", coefficient=coefficient))
                    continue
                if (
                    has_test
                    and has_trial
                    and not has_grad_test
                    and not has_grad_trial
                    and test_count == 1
                    and trial_count == 1
                ):
                    terms.append(Term(kind="mass", coefficient=coefficient))
                    continue
                if (
                    has_test
                    and not has_trial
                    and not has_grad_test
                    and test_count == 1
                    and trial_count == 0
                ):
                    terms.append(
                        Term(kind="source", coefficient=coefficient, source=1.0)
                    )
                    continue
                raise ValueError(
                    "unsupported UFL cell integrand for current scalar subset"
                )

            if integral_type == "exterior_facet":
                if has_test and not has_trial:
                    boundary_conditions.append(
                        BoundaryCondition(
                            kind="natural",
                            value=coefficient,
                            boundary="all",
                        )
                    )
                    continue
                raise ValueError(
                    "unsupported UFL exterior facet integrand for current scalar subset"
                )

            raise ValueError(f"unsupported UFL integral type {integral_type!r}")

    if not terms:
        raise ValueError("UFL form did not yield any supported scalar terms")

    form_ir = WeakFormIR(
        trial_space=trial_space,
        test_space=test_space,
        terms=tuple(terms),
        boundary_conditions=tuple(boundary_conditions),
    )
    _validate_ir_boundaries(form_ir.boundary_conditions)
    return form_ir


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
        return _parse_ufl_form(form)

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
