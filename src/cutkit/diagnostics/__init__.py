"""Diagnostics layer for quality metrics and debugging outputs."""

from cutkit.diagnostics.moments2d import (
    MONOMIALS_DEGREE2,
    AreaConsistencyReport,
    MomentError,
    MomentReport,
    approximate_moments,
    area_consistency,
    exact_moments_degree2,
    moment_report,
    panel_area_from_loops,
)
from cutkit.diagnostics.volume3d import (
    SeedInvariantVolumeReport,
    seed_invariant_volume_report,
)
from cutkit.diagnostics.svg_plot import (
    SvgLineSeries,
    SvgLogLogChart,
    render_loglog_chart_svg,
)
from cutkit.diagnostics.poisson_galerkin_plots import (
    PoissonGalerkinPlotArtifact,
    render_poisson_galerkin_error_plot_svg,
    write_poisson_galerkin_error_plots,
)
from cutkit.diagnostics.poisson_galerkin_figures import (
    PoissonGalerkinFigureArtifact,
    render_cell_classification_svg,
    render_solution_field_svg,
    render_trimmed_geometry_svg,
    write_poisson_galerkin_figure_pack,
)

__all__ = [
    "MONOMIALS_DEGREE2",
    "AreaConsistencyReport",
    "MomentError",
    "MomentReport",
    "approximate_moments",
    "area_consistency",
    "exact_moments_degree2",
    "moment_report",
    "panel_area_from_loops",
    "SeedInvariantVolumeReport",
    "seed_invariant_volume_report",
    "SvgLineSeries",
    "SvgLogLogChart",
    "render_loglog_chart_svg",
    "PoissonGalerkinPlotArtifact",
    "render_poisson_galerkin_error_plot_svg",
    "write_poisson_galerkin_error_plots",
    "PoissonGalerkinFigureArtifact",
    "render_trimmed_geometry_svg",
    "render_cell_classification_svg",
    "render_solution_field_svg",
    "write_poisson_galerkin_figure_pack",
]
