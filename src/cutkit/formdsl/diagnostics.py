"""Deterministic diagnostics for form/backend capability checks."""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class CapabilityDiagnostic:
    """Structured capability mismatch message."""

    code: str
    backend: str
    detail: str
    alternatives: tuple[str, ...] = ()


class CapabilityError(ValueError):
    """Raised when strict capability checks fail."""

    def __init__(self, diagnostic: CapabilityDiagnostic) -> None:
        super().__init__(
            f"[{diagnostic.code}] backend={diagnostic.backend}: {diagnostic.detail}"
        )
        self.diagnostic = diagnostic


class PrerequisiteError(RuntimeError):
    """Raised when backend prerequisites are not met."""
