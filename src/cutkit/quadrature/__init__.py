"""Quadrature layer for trimmed-domain integration workflows."""

from cutkit.quadrature.folded2d import (
    FoldedQuadratureResult,
    SignedTriangle2D,
    decompose_panel,
    folded_quadrature_rule,
    gauss_legendre_01,
    triangle_duffy_rule,
)
from cutkit.quadrature.folded_curves2d import (
    FoldedCurveQuadratureResult,
    folded_curve_quadrature_rule,
)
from cutkit.quadrature.rule2d import QuadratureRule2D, concatenate_rules

__all__ = [
    "FoldedQuadratureResult",
    "QuadratureRule2D",
    "SignedTriangle2D",
    "concatenate_rules",
    "decompose_panel",
    "FoldedCurveQuadratureResult",
    "folded_curve_quadrature_rule",
    "folded_quadrature_rule",
    "gauss_legendre_01",
    "triangle_duffy_rule",
]
