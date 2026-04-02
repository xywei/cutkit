"""UFL-style form DSL and backend lowering entrypoints."""

from .adapter import parse_form
from .assembly import assemble_form
from .diagnostics import (
    CapabilityDiagnostic,
    CapabilityError,
    PrerequisiteError,
)
from .ir import BoundaryCondition, Term, WeakFormIR

__all__ = [
    "BoundaryCondition",
    "CapabilityDiagnostic",
    "CapabilityError",
    "PrerequisiteError",
    "Term",
    "WeakFormIR",
    "assemble_form",
    "parse_form",
]
