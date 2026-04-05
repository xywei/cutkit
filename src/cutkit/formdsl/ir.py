"""Method-neutral weak-form intermediate representation."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Literal

BackendName = Literal["iga", "dgsem"]


@dataclass(frozen=True)
class Term:
    """One scalar weak-form term contribution."""

    kind: str
    coefficient: float = 1.0
    source: float | Callable[[float, float], float] | None = None


@dataclass(frozen=True)
class BoundaryCondition:
    """Backend-neutral boundary condition descriptor."""

    kind: str
    value: float = 0.0
    boundary: str = "all"


@dataclass(frozen=True)
class WeakFormIR:
    """Canonical weak form used by CUTKIT backend lowerers."""

    trial_space: str
    test_space: str
    terms: tuple[Term, ...]
    boundary_conditions: tuple[BoundaryCondition, ...] = field(default_factory=tuple)
    metadata: dict[str, str] = field(default_factory=dict)
    value_shape: tuple[int, ...] = field(default_factory=tuple)
