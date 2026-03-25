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
from cutkit.quadrature.folded3d import (
    Axis3D,
    boundary_quadrature_rule_3d,
    folded_boundary_cells_3d,
    folded_seeds_without_jplus_3d,
    integrate_bernstein_over_boundary_3d,
    integrate_general_over_cartesian_grid_bounded_surface_3d,
    integrate_general_over_cartesian_grid_bounded_xsurface_3d,
    integrate_general_over_cartesian_grid_bounded_ysurface_3d,
    integrate_general_over_cartesian_grid_bounded_zsurface_3d,
    integrate_general_over_boundary_3d,
    integrate_general_over_cartesian_grid_surface_3d,
    integrate_general_over_cartesian_grid_xsurface_3d,
    integrate_general_over_cartesian_grid_ysurface_3d,
    integrate_general_over_cartesian_grid_zsurface_3d,
    same_seed_3d,
    seed_grid_3d,
    signed_boundary_volume_3d,
)
from cutkit.quadrature.rule2d import QuadratureRule2D, concatenate_rules
from cutkit.quadrature.rule3d import QuadratureRule3D, concatenate_rules_3d

__all__ = [
    "FoldedQuadratureResult",
    "Axis3D",
    "QuadratureRule2D",
    "SignedTriangle2D",
    "concatenate_rules",
    "decompose_panel",
    "FoldedCurveQuadratureResult",
    "folded_curve_quadrature_rule",
    "boundary_quadrature_rule_3d",
    "folded_boundary_cells_3d",
    "folded_seeds_without_jplus_3d",
    "folded_quadrature_rule",
    "gauss_legendre_01",
    "integrate_bernstein_over_boundary_3d",
    "integrate_general_over_boundary_3d",
    "integrate_general_over_cartesian_grid_bounded_surface_3d",
    "integrate_general_over_cartesian_grid_bounded_xsurface_3d",
    "integrate_general_over_cartesian_grid_bounded_ysurface_3d",
    "integrate_general_over_cartesian_grid_bounded_zsurface_3d",
    "integrate_general_over_cartesian_grid_surface_3d",
    "integrate_general_over_cartesian_grid_xsurface_3d",
    "integrate_general_over_cartesian_grid_ysurface_3d",
    "integrate_general_over_cartesian_grid_zsurface_3d",
    "QuadratureRule3D",
    "triangle_duffy_rule",
    "same_seed_3d",
    "seed_grid_3d",
    "signed_boundary_volume_3d",
    "concatenate_rules_3d",
]
