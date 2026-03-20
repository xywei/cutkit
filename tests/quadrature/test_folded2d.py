from __future__ import annotations

import pytest

from cutkit.diagnostics import moment_report, panel_area_from_loops
from cutkit.geometry import PanelLoop2D, TrimmedPanel2D
from cutkit.quadrature import decompose_panel, folded_quadrature_rule


def test_decomposition_area_matches_panel_for_concave_case() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(
            (
                (0.0, 0.0),
                (2.0, 0.0),
                (2.0, 1.0),
                (1.0, 1.0),
                (1.0, 2.0),
                (0.0, 2.0),
            )
        )
    )

    normalized, _anchor, triangles = decompose_panel(panel)
    tri_area = sum(triangle.signed_area for triangle in triangles)
    assert tri_area == pytest.approx(panel_area_from_loops(normalized))


def test_folded_quadrature_recovers_degree2_moments() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0))),
        holes=(PanelLoop2D(((0.25, 0.25), (0.75, 0.25), (0.75, 0.75), (0.25, 0.75))),),
    )
    folded = folded_quadrature_rule(panel, order=5)
    report = moment_report(folded.triangles, folded.rule)
    assert report.max_abs_error < 1.0e-10


def test_anchor_must_be_inside_panel() -> None:
    panel = TrimmedPanel2D(
        outer=PanelLoop2D(((0.0, 0.0), (1.0, 0.0), (1.0, 1.0), (0.0, 1.0)))
    )
    with pytest.raises(ValueError):
        folded_quadrature_rule(panel, order=4, anchor=(1.5, 0.5))
