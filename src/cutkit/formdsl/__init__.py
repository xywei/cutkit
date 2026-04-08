"""UFL-style form DSL and backend lowering entrypoints."""

from .adapter import parse_form
from .assembly import assemble_form
from .diagnostics import (
    CapabilityDiagnostic,
    CapabilityError,
    PrerequisiteError,
)
from .ir import (
    BoundaryCondition,
    MultipatchDescriptor,
    MultipatchInterfaceDescriptor,
    Term,
    WeakFormIR,
)
from .solver import DGSEMExecutionMode, FormSolveResult, solve_form

__all__ = [
    "BoundaryCondition",
    "CapabilityDiagnostic",
    "CapabilityError",
    "MultipatchDescriptor",
    "MultipatchInterfaceDescriptor",
    "PrerequisiteError",
    "Term",
    "WeakFormIR",
    "assemble_form",
    "parse_form",
    "DGSEMExecutionMode",
    "FormSolveResult",
    "solve_form",
]
