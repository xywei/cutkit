"""UFL adapter entrypoints for method-neutral form IR."""

from __future__ import annotations

from collections.abc import Mapping
from numbers import Integral as IntegralNumber
from typing import Any

from .ir import (
    BackendName,
    BoundaryCondition,
    MultipatchDescriptor,
    MultipatchInterfaceDescriptor,
    SourceComponent,
    SourceValue,
    Term,
    WeakFormIR,
)

_VALID_BOUNDARIES = {"all", "left", "right", "bottom", "top"}
_VECTOR_SPACE_PATTERNS = (
    "vector(",
    "vectorelement(",
    "vector element",
    "tensor(",
    "tensorelement(",
    "tensor element",
)
_VALID_INTERFACE_ORIENTATIONS = {"aligned", "reversed"}


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


def _normalize_patch_id(raw_patch_id: object, *, context: str) -> str:
    patch_id = str(raw_patch_id).strip()
    if not patch_id:
        raise ValueError(f"{context} patch id must be non-empty")
    return patch_id


def _normalize_interface_boundary(raw_boundary: object, *, context: str) -> str:
    boundary = str(raw_boundary).strip()
    if not _is_valid_boundary_selector(boundary):
        raise ValueError(f"{context} boundary selector {boundary!r} is unsupported")
    return boundary


def _multipatch_interface_sort_key(
    descriptor: MultipatchInterfaceDescriptor,
) -> tuple[str, str, str, str, str]:
    return (
        descriptor.plus_patch,
        descriptor.minus_patch,
        descriptor.plus_boundary,
        descriptor.minus_boundary,
        descriptor.orientation,
    )


def _parse_multipatch_descriptor(
    raw_descriptor: object,
    *,
    context: str,
) -> MultipatchDescriptor:
    if not isinstance(raw_descriptor, Mapping):
        raise ValueError(f"{context} multipatch must be a mapping")

    raw_patch_ids = raw_descriptor.get("patch_ids")
    if not isinstance(raw_patch_ids, list) or not raw_patch_ids:
        raise ValueError(f"{context} multipatch patch_ids must be a non-empty list")

    patch_ids: list[str] = []
    for index, raw_patch_id in enumerate(raw_patch_ids):
        patch_id = _normalize_patch_id(
            raw_patch_id,
            context=f"{context} multipatch patch_ids[{index}]",
        )
        if patch_id in patch_ids:
            raise ValueError(f"{context} multipatch patch_ids must be unique")
        patch_ids.append(patch_id)

    if len(patch_ids) < 2:
        raise ValueError(
            f"{context} multipatch patch_ids must include at least two patches"
        )

    patch_id_set = set(patch_ids)
    raw_interfaces = raw_descriptor.get("interfaces")
    if not isinstance(raw_interfaces, list) or not raw_interfaces:
        raise ValueError(f"{context} multipatch interfaces must be a non-empty list")

    interfaces: list[MultipatchInterfaceDescriptor] = []
    required_keys = (
        "plus_patch",
        "minus_patch",
        "plus_boundary",
        "minus_boundary",
        "orientation",
    )
    for index, raw_interface in enumerate(raw_interfaces):
        if not isinstance(raw_interface, Mapping):
            raise ValueError(
                f"{context} multipatch interfaces[{index}] must be a mapping"
            )

        for key in required_keys:
            if key not in raw_interface:
                raise ValueError(
                    f"{context} multipatch interfaces[{index}] is missing required key {key!r}"
                )

        plus_patch = _normalize_patch_id(
            raw_interface["plus_patch"],
            context=f"{context} multipatch interfaces[{index}] plus_patch",
        )
        minus_patch = _normalize_patch_id(
            raw_interface["minus_patch"],
            context=f"{context} multipatch interfaces[{index}] minus_patch",
        )
        if plus_patch == minus_patch:
            raise ValueError(
                f"{context} multipatch interfaces[{index}] must reference two distinct patches"
            )
        if plus_patch not in patch_id_set or minus_patch not in patch_id_set:
            raise ValueError(
                f"{context} multipatch interfaces[{index}] references unknown patch id"
            )

        plus_boundary = _normalize_interface_boundary(
            raw_interface["plus_boundary"],
            context=f"{context} multipatch interfaces[{index}] plus_boundary",
        )
        minus_boundary = _normalize_interface_boundary(
            raw_interface["minus_boundary"],
            context=f"{context} multipatch interfaces[{index}] minus_boundary",
        )
        orientation = str(raw_interface["orientation"]).strip().lower()
        if orientation not in _VALID_INTERFACE_ORIENTATIONS:
            raise ValueError(
                f"{context} multipatch interfaces[{index}] orientation {orientation!r} is unsupported"
            )

        interfaces.append(
            MultipatchInterfaceDescriptor(
                plus_patch=plus_patch,
                minus_patch=minus_patch,
                plus_boundary=plus_boundary,
                minus_boundary=minus_boundary,
                orientation=orientation,
            )
        )

    return MultipatchDescriptor(
        patch_ids=tuple(sorted(patch_ids)),
        interfaces=tuple(sorted(interfaces, key=_multipatch_interface_sort_key)),
    )


def _validate_multipatch_descriptor(
    multipatch: MultipatchDescriptor,
    *,
    context: str,
) -> None:
    if len(multipatch.patch_ids) < 2:
        raise ValueError(f"{context} patch_ids must include at least two patches")

    normalized_patch_ids: list[str] = []
    for index, patch_id in enumerate(multipatch.patch_ids):
        normalized_patch_ids.append(
            _normalize_patch_id(
                patch_id,
                context=f"{context} patch_ids[{index}]",
            )
        )

    if len(set(normalized_patch_ids)) != len(normalized_patch_ids):
        raise ValueError(f"{context} patch_ids must be unique")
    canonical_patch_ids = tuple(sorted(normalized_patch_ids))
    if canonical_patch_ids != multipatch.patch_ids:
        raise ValueError(
            f"{context} patch_ids must be sorted for deterministic ordering"
        )

    if not multipatch.interfaces:
        raise ValueError(f"{context} interfaces must be non-empty")

    patch_id_set = set(canonical_patch_ids)
    for index, interface in enumerate(multipatch.interfaces):
        if interface.plus_patch == interface.minus_patch:
            raise ValueError(
                f"{context} interfaces[{index}] must reference two distinct patches"
            )
        if (
            interface.plus_patch not in patch_id_set
            or interface.minus_patch not in patch_id_set
        ):
            raise ValueError(
                f"{context} interfaces[{index}] references unknown patch id"
            )
        _normalize_interface_boundary(
            interface.plus_boundary,
            context=f"{context} interfaces[{index}] plus_boundary",
        )
        _normalize_interface_boundary(
            interface.minus_boundary,
            context=f"{context} interfaces[{index}] minus_boundary",
        )
        if interface.orientation not in _VALID_INTERFACE_ORIENTATIONS:
            raise ValueError(
                f"{context} interfaces[{index}] orientation {interface.orientation!r} is unsupported"
            )

    canonical_interfaces = tuple(
        sorted(multipatch.interfaces, key=_multipatch_interface_sort_key)
    )
    if canonical_interfaces != multipatch.interfaces:
        raise ValueError(
            f"{context} interfaces must be sorted for deterministic ordering"
        )


def _is_vector_space_label(space: str) -> bool:
    lowered = space.strip().lower()
    return any(pattern in lowered for pattern in _VECTOR_SPACE_PATTERNS)


def _normalize_value_shape(
    raw_shape: object,
    *,
    context: str,
) -> tuple[int, ...]:
    if raw_shape in (None, (), []):
        return ()
    if isinstance(raw_shape, tuple):
        entries = raw_shape
    elif isinstance(raw_shape, list):
        entries = tuple(raw_shape)
    else:
        raise ValueError(f"{context} value_shape must be tuple/list of positive ints")

    value_shape: list[int] = []
    for index, entry in enumerate(entries):
        if isinstance(entry, bool):
            raise ValueError(
                f"{context} value_shape entry {index} must be positive integer"
            )
        if isinstance(entry, IntegralNumber):
            normalized = int(entry)
        elif isinstance(entry, str):
            text = entry.strip()
            if text.startswith("+"):
                text = text[1:]
            if not text.isdigit():
                raise ValueError(
                    f"{context} value_shape entry {index} must be positive integer"
                )
            normalized = int(text)
        else:
            raise ValueError(
                f"{context} value_shape entry {index} must be positive integer"
            )
        if normalized <= 0:
            raise ValueError(
                f"{context} value_shape entry {index} must be positive integer"
            )
        value_shape.append(normalized)
    return tuple(value_shape)


def _mapping_value_shape(
    *,
    trial_space: str,
    test_space: str,
    raw_value_shape: object,
) -> tuple[int, ...]:
    value_shape = _normalize_value_shape(raw_value_shape, context="form payload")
    if value_shape:
        return value_shape

    if _is_vector_space_label(trial_space) or _is_vector_space_label(test_space):
        raise ValueError(
            "form payload with vector/tensor space labels must declare value_shape"
        )
    return ()


def _normalize_source_component(
    raw_source: object,
    *,
    context: str,
    component_index: int | None = None,
) -> SourceComponent:
    component_suffix = (
        f" component {component_index}" if component_index is not None else ""
    )
    if raw_source is None or callable(raw_source):
        return raw_source
    if isinstance(raw_source, bool):
        raise ValueError(
            f"{context}{component_suffix} source must be float, callable, or null"
        )
    if isinstance(raw_source, (int, float, str)):
        try:
            return float(raw_source)
        except ValueError as exc:
            raise ValueError(
                f"{context}{component_suffix} source must be float, callable, or null"
            ) from exc
    raise ValueError(
        f"{context}{component_suffix} source must be float, callable, or null"
    )


def _normalize_source_value(raw_source: object, *, context: str) -> SourceValue:
    if isinstance(raw_source, tuple) or isinstance(raw_source, list):
        components: list[SourceComponent] = []
        for component_index, component_source in enumerate(raw_source):
            components.append(
                _normalize_source_component(
                    component_source,
                    context=context,
                    component_index=component_index,
                )
            )
        return tuple(components)

    return _normalize_source_component(raw_source, context=context)


def _validate_form_ir(form_ir: WeakFormIR) -> None:
    if not form_ir.terms:
        raise ValueError("form payload must provide a non-empty 'terms' list")
    normalized_shape = _normalize_value_shape(
        form_ir.value_shape,
        context="WeakFormIR",
    )
    if normalized_shape != form_ir.value_shape:
        raise ValueError("WeakFormIR value_shape must be tuple of positive integers")
    if normalized_shape == () and (
        _is_vector_space_label(form_ir.trial_space)
        or _is_vector_space_label(form_ir.test_space)
    ):
        raise ValueError(
            "WeakFormIR with vector/tensor space labels must declare value_shape"
        )

    if len(normalized_shape) > 1:
        for index, term in enumerate(form_ir.terms):
            if term.kind == "source" and isinstance(term.source, tuple):
                raise ValueError(
                    f"source term at index {index} does not support vector source "
                    "tuples for rank-2+ value_shape"
                )

    if len(normalized_shape) == 1:
        component_count = normalized_shape[0]
        for index, term in enumerate(form_ir.terms):
            if term.kind != "source":
                continue
            if not isinstance(term.source, tuple):
                continue
            if len(term.source) != component_count:
                raise ValueError(
                    f"source term at index {index} vector source length "
                    f"{len(term.source)} does not match value_shape[0]={component_count}"
                )

    if normalized_shape == ():
        for index, term in enumerate(form_ir.terms):
            if term.kind != "source":
                continue
            if isinstance(term.source, tuple):
                raise ValueError(
                    f"source term at index {index} provides vector source "
                    "for scalar value_shape"
                )

    _validate_ir_boundaries(form_ir.boundary_conditions)
    _validate_boundary_marker_metadata(form_ir.metadata)
    if form_ir.multipatch is not None:
        _validate_multipatch_descriptor(
            form_ir.multipatch,
            context="WeakFormIR multipatch",
        )


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


def _extract_ufl_multipatch_descriptor(form: Any) -> MultipatchDescriptor | None:
    raw_descriptor = getattr(form, "multipatch_descriptor", None)
    if raw_descriptor is None:
        return None
    return _parse_multipatch_descriptor(raw_descriptor, context="UFL form")


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

    try:
        return _normalize_value_shape(shape, context="UFL argument")
    except ValueError:
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
    value_shape: tuple[int, ...] = ()
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
            argument_shapes: list[tuple[int, ...]] = []
            for argument in arguments:
                shape = _ufl_argument_shape(argument)
                if shape is None:
                    raise ValueError(
                        "UFL argument value_shape is invalid for formdsl parsing"
                    )
                argument_shapes.append(shape)

            unique_shapes = tuple(sorted(set(argument_shapes)))
            if len(unique_shapes) > 1:
                raise ValueError(
                    "UFL arguments must share one value_shape across trial/test spaces"
                )

            value_shape = argument_shapes[0]
            test_space = _ufl_space_label(arguments[0])
            trial_space = (
                _ufl_space_label(arguments[1]) if len(arguments) > 1 else test_space
            )

    terms: list[Term] = []
    boundary_conditions: list[BoundaryCondition] = []
    metadata = _extract_ufl_boundary_marker_metadata(form)
    multipatch = _extract_ufl_multipatch_descriptor(form)

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
                    "unsupported UFL integrand structure for current formdsl subset"
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
                    "unsupported UFL cell integrand for current formdsl subset"
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
                    "unsupported UFL exterior facet integrand for current formdsl subset"
                )

            raise ValueError(f"unsupported UFL integral type {integral_type!r}")

    if not terms:
        raise ValueError("UFL form did not yield any supported form terms")

    form_ir = WeakFormIR(
        trial_space=trial_space,
        test_space=test_space,
        terms=tuple(terms),
        boundary_conditions=tuple(boundary_conditions),
        metadata=metadata,
        value_shape=value_shape,
        multipatch=multipatch,
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
    payload for minimal form terms.
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
    value_shape = _mapping_value_shape(
        trial_space=trial_space,
        test_space=test_space,
        raw_value_shape=form.get("value_shape"),
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
        source = _normalize_source_value(
            raw_term.get("source"),
            context=f"term at index {index}",
        )
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

    multipatch: MultipatchDescriptor | None = None
    raw_multipatch = form.get("multipatch")
    if raw_multipatch is not None:
        multipatch = _parse_multipatch_descriptor(
            raw_multipatch,
            context="form payload",
        )

    form_ir = WeakFormIR(
        trial_space=trial_space,
        test_space=test_space,
        terms=tuple(terms),
        boundary_conditions=tuple(boundary_conditions),
        metadata=metadata,
        value_shape=value_shape,
        multipatch=multipatch,
    )
    _validate_form_ir(form_ir)
    return form_ir
