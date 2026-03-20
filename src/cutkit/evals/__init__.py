"""Evaluation harnesses for CUTKIT geometry and integration workflows."""

from cutkit.evals.cutpanel import (
    CutPanelCase,
    CutPanelEvaluation,
    CutPanelMetrics,
    default_cases,
    evaluate_case,
    run_default_eval,
    validate_case,
)
from cutkit.evals.antolin_wei_buffa_2022_2d import (
    GeneralFunctionOrderResult,
    GeneralFunctionResult,
    NUMPY_ACCELERATION_ENABLED,
    PolynomialDegreeResult,
    PolynomialExperimentResult,
    build_section_6_1_1_bspline_panel,
    build_section_6_1_2_rational_panel,
    run_general_function_experiment,
    run_polynomial_experiment,
    section_6_2_integrand,
)

__all__ = [
    "CutPanelCase",
    "CutPanelEvaluation",
    "CutPanelMetrics",
    "default_cases",
    "evaluate_case",
    "run_default_eval",
    "validate_case",
    "GeneralFunctionOrderResult",
    "GeneralFunctionResult",
    "NUMPY_ACCELERATION_ENABLED",
    "PolynomialDegreeResult",
    "PolynomialExperimentResult",
    "build_section_6_1_1_bspline_panel",
    "build_section_6_1_2_rational_panel",
    "run_general_function_experiment",
    "run_polynomial_experiment",
    "section_6_2_integrand",
]
