from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cutkit.diagnostics.poisson_galerkin_figures import (
    render_cell_classification_svg,
    render_solution_field_svg,
    render_trimmed_geometry_svg,
    write_poisson_galerkin_figure_pack,
)


@dataclass(frozen=True)
class _Cell:
    ix: int
    iy: int
    x0: float
    x1: float
    y0: float
    y1: float


@dataclass(frozen=True)
class _Clip:
    cell: _Cell
    kind: str
    polygon: tuple[tuple[float, float], ...]


@dataclass(frozen=True)
class _Snapshot:
    resolution: int
    bounds: tuple[float, float, float, float]
    panel_polygon: tuple[tuple[float, float], ...]
    clipped_cells: tuple[_Clip, ...]
    inside_cell_count: int
    trimmed_cell_count: int


def _sample_snapshot() -> _Snapshot:
    return _Snapshot(
        resolution=2,
        bounds=(0.0, 0.0, 1.0, 1.0),
        panel_polygon=((0.0, 0.2), (0.8, 0.0), (1.0, 0.8), (0.1, 1.0)),
        clipped_cells=(
            _Clip(_Cell(0, 0, 0.0, 0.5, 0.0, 0.5), "inside", ()),
            _Clip(
                _Cell(1, 0, 0.5, 1.0, 0.0, 0.5),
                "trimmed",
                ((0.5, 0.0), (1.0, 0.0), (0.8, 0.5), (0.5, 0.4)),
            ),
            _Clip(_Cell(0, 1, 0.0, 0.5, 0.5, 1.0), "inside", ()),
            _Clip(_Cell(1, 1, 0.5, 1.0, 0.5, 1.0), "outside", ()),
        ),
        inside_cell_count=2,
        trimmed_cell_count=1,
    )


def test_render_trimmed_geometry_svg_has_expected_labels() -> None:
    svg = render_trimmed_geometry_svg(_sample_snapshot(), title="Geometry")
    assert "<svg" in svg
    assert "Geometry" in svg
    assert "resolution = 2" in svg


def test_render_cell_classification_svg_has_counts() -> None:
    svg = render_cell_classification_svg(_sample_snapshot(), title="Cells")
    assert "Cells" in svg
    assert "inside=2, trimmed=1" in svg


def test_render_solution_field_svg_contains_title() -> None:
    snapshot = _sample_snapshot()
    solution = tuple(float(index) / 9.0 for index in range(9))
    svg = render_solution_field_svg(snapshot, solution=solution, title="Solution")
    assert "Solution" in svg
    assert "resolution = 2" in svg


def test_write_poisson_galerkin_figure_pack_creates_expected_files(
    tmp_path: Path,
) -> None:
    snapshot = _sample_snapshot()
    solution = tuple(float(index) / 9.0 for index in range(9))
    artifacts = write_poisson_galerkin_figure_pack(
        snapshot,
        solutions={"jplus": solution, "folded": solution},
        output_dir=tmp_path,
        prefix="paper",
    )

    assert len(artifacts) == 4
    for artifact in artifacts:
        assert artifact.file_path.exists()
        assert artifact.file_path.read_text(encoding="utf-8").startswith("<svg")
