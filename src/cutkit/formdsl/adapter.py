"""UFL adapter entrypoints for method-neutral form IR."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from .ir import BackendName, BoundaryCondition, Term, WeakFormIR

_VALID_BOUNDARIES = {"all", "left", "right", "bottom", "top"}
_VECTOR_SPACE_TOKENS = ("vector", "tensor")


def _is_valid_boundary_selector(boundary: str) -> bool:
    if boundary in _VALID_BOUNDARIES:
        return True
    if not boundary.startswith("marker:"):
        return False
    marker = boundary.removeprefix("marker:").strip()
    return bool(marker)


def _validate_boundary_marker_metadata(metadata: Mapping[str, str]) -> None:
    for key, value in metadata.items():
        if not key.startswith("boundary_marker:"):
            continue
        marker = key.removeprefix("boundary_marker:").strip()
        if not marker:
            raise ValueError("boundary marker metadata key is missing marker id")
        if value not in _VALID_BOUNDARIES:
            raise ValueError(
                f"boundary marker metadata {key!r} has unsupported selector {value!r}"
            )


def _validate_ir_boundaries(boundary_conditions: tuple[BoundaryCondition, ...]) -> None:
    for index, condition in enumerate(boundary_conditions):
        if _is_valid_boundary_selector(condition.boundary):
            continue
        raise ValueError(
            f"boundary condition at index {index} has unsupported boundary {condition.boundary!r}"
        )


def _is_vector_space_label(space: str) -> bool:
    lowered = space.strip().lower()
    return any(token in lowered for token in _VECTOR_SPACE_TOKENS)


def _validate_scalar_spaces(*, trial_space: str, test_space: str) -> None:
    for label_name, label in (
        ("trial_space", trial_space),
        ("test_space", test_space),
    ):
        if _is_vector_space_label(label):
            raise ValueError(
                f"{label_name} {label!r} is vector-valued; "
                "current formdsl subset supports scalar spaces only"
            )


def _validate_form_ir(form_ir: WeakFormIR) -> None:
    if not form_ir.terms:
        raise ValueError("form payload must provide a non-empty 'terms' list")
    _validate_scalar_spaces(
        trial_space=form_ir.trial_space,
        test_space=form_ir.test_space,
    )
    _validate_ir_boundaries(form_ir.boundary_conditions)
    _validate_boundary_marker_metadata(form_ir.metadata)


def _integral_subdomain_id(integral: object) -> object | None:
    subdomain_id_fn = getattr(integral, "subdomain_id", None)
    if callable(subdomain_id_fn):
        return subdomain_id_fn()
    if subdomain_id_fn is None:
        return None
    return subdomain_id_fn


def _boundary_selector_from_integral(integral: object) -> str:
    subdomain_id = _integral_subdomain_id(integral)
    if subdomain_id is None:
        return "all"

    selector = str(subdomain_id).strip()
    if selector in {"", "everywhere", "otherwise", "on_boundary"}:
        return "all"
    if selector in _VALID_BOUNDARIES:
        return selector
    return f"marker:{selector}"


def _extract_ufl_boundary_marker_metadata(form: Any) -> dict[str, str]:
    raw_marker_map = getattr(form, "boundary_marker_map", None)
    if raw_marker_map is None:
        return {}
    if not isinstance(raw_marker_map, Mapping):
        raise TypeError("UFL boundary_marker_map must be a mapping if provided")

    metadata: dict[str, str] = {}
    for marker_id, selector in raw_marker_map.items():
        marker_text = str(marker_id).strip()
        if not marker_text:
            raise ValueError("UFL boundary marker map contains empty marker id")
        metadata[f"boundary_marker:{marker_text}"] = str(selector).strip()

    _validate_boundary_marker_metadata(metadata)
    return metadata


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


def _ufl_non_scalar_factors(node: object) -> tuple[object, ...] | None:
    node_type = type(node).__name__
    operands = _ufl_operands(node)

    if node_type == "Product":
        factors: list[object] = []
        for operand in operands:
            operand_factors = _ufl_non_scalar_factors(operand)
            if operand_factors is None:
                return None
            factors.extend(operand_factors)
        return tuple(factors)

    if node_type == "Division" and len(operands) == 2:
        numerator_factors = _ufl_non_scalar_factors(operands[0])
        denominator_factors = _ufl_non_scalar_factors(operands[1])
        if numerator_factors is None or denominator_factors is None:
            return None
        if denominator_factors:
            return None
        return numerator_factors

    if node_type.startswith("Negative") and operands:
        return _ufl_non_scalar_factors(operands[0])

    if _ufl_numeric_value(node) is not None:
        return ()

    return (node,)


def _ufl_is_argument(node: object, *, number: int) -> bool:
    return _ufl_argument_number(node) == number and not _ufl_operands(node)


def _ufl_is_grad_of_argument(node: object, *, number: int) -> bool:
    if type(node).__name__ not in {"Grad", "ReferenceGrad"}:
        return False
    operands = _ufl_operands(node)
    if len(operands) != 1:
        return False
    return _ufl_is_argument(operands[0], number=number)


def _ufl_is_diffusion_factor(node: object) -> bool:
    if type(node).__name__ not in {"Inner", "Dot"}:
        return False
    operands = _ufl_operands(node)
    if len(operands) != 2:
        return False
    left, right = operands
    return (
        _ufl_is_grad_of_argument(left, number=1)
        and _ufl_is_grad_of_argument(right, number=0)
    ) or (
        _ufl_is_grad_of_argument(left, number=0)
        and _ufl_is_grad_of_argument(right, number=1)
    )


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


def _ufl_argument_shape(argument: object) -> tuple[int, ...] | None:
    raw_shape = getattr(argument, "ufl_shape", None)
    shape = raw_shape() if callable(raw_shape) else raw_shape

    if shape is None:
        element_fn = getattr(argument, "ufl_element", None)
        if callable(element_fn):
            element = element_fn()
            raw_value_shape = getattr(element, "value_shape", None)
            shape = raw_value_shape() if callable(raw_value_shape) else raw_value_shape

    if shape is None:
        return None
    if isinstance(shape, tuple):
        try:
            return tuple(int(entry) for entry in shape)
        except (TypeError, ValueError):
            return None
    if isinstance(shape, list):
        try:
            return tuple(int(entry) for entry in shape)
        except (TypeError, ValueError):
            return None
    return None


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
            for argument in arguments:
                shape = _ufl_argument_shape(argument)
                if shape in (None, ()):
                    continue
                raise ValueError(
                    "vector-valued UFL arguments are not supported "
                    "for current scalar subset"
                )
            test_space = _ufl_space_label(arguments[0])
            trial_space = (
                _ufl_space_label(arguments[1]) if len(arguments) > 1 else test_space
            )

    _validate_scalar_spaces(
        trial_space=trial_space,
        test_space=test_space,
    )

    terms: list[Term] = []
    boundary_conditions: list[BoundaryCondition] = []
    metadata = _extract_ufl_boundary_marker_metadata(form)

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
            factors = _ufl_non_scalar_factors(summand)
            if factors is None:
                raise ValueError(
                    "unsupported UFL integrand structure for current scalar subset"
                )

            if integral_type == "cell":
                if len(factors) == 1 and _ufl_is_diffusion_factor(factors[0]):
                    terms.append(Term(kind="diffusion", coefficient=coefficient))
                    continue
                if (
                    len(factors) == 2
                    and _ufl_is_argument(factors[0], number=0)
                    and _ufl_is_argument(factors[1], number=1)
                ):
                    terms.append(Term(kind="mass", coefficient=coefficient))
                    continue
                if (
                    len(factors) == 2
                    and _ufl_is_argument(factors[0], number=1)
                    and _ufl_is_argument(factors[1], number=0)
                ):
                    terms.append(Term(kind="mass", coefficient=coefficient))
                    continue
                if len(factors) == 1 and _ufl_is_argument(factors[0], number=0):
                    terms.append(
                        Term(kind="source", coefficient=coefficient, source=1.0)
                    )
                    continue
                raise ValueError(
                    "unsupported UFL cell integrand for current scalar subset"
                )

            if integral_type == "exterior_facet":
                if len(factors) == 1 and _ufl_is_argument(factors[0], number=0):
                    boundary_selector = _boundary_selector_from_integral(integral)
                    boundary_conditions.append(
                        BoundaryCondition(
                            kind="natural",
                            value=coefficient,
                            boundary=boundary_selector,
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
        metadata=metadata,
    )
    _validate_form_ir(form_ir)
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
        _validate_form_ir(form)
        return form

    module_name = type(form).__module__
    if module_name.startswith("ufl"):
        return _parse_ufl_form(form)

    if not isinstance(form, Mapping):
        raise TypeError("form must be WeakFormIR or mapping payload")

    trial_space = str(form.get("trial_space", "P1"))
    test_space = str(form.get("test_space", "P1"))
    _validate_scalar_spaces(
        trial_space=trial_space,
        test_space=test_space,
    )

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
        if not _is_valid_boundary_selector(boundary):
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
    _validate_boundary_marker_metadata(metadata)

    form_ir = WeakFormIR(
        trial_space=trial_space,
        test_space=test_space,
        terms=tuple(terms),
        boundary_conditions=tuple(boundary_conditions),
        metadata=metadata,
    )
    _validate_form_ir(form_ir)
    return form_ir
