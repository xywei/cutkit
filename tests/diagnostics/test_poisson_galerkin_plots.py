from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from cutkit.diagnostics.poisson_galerkin_plots import (
    render_poisson_galerkin_error_plot_svg,
    write_poisson_galerkin_error_plots,
)


@dataclass(frozen=True)
class _Row:
    resolution: int
    abs_error: float
    rel_error: float


@dataclass(frozen=True)
class _Benchmark:
    profile: str
    backend_mode: str
    rows: tuple[_Row, ...]


def _sample_benchmarks() -> dict[str, _Benchmark]:
    return {
        "jplus": _Benchmark(
            profile="quick",
            backend_mode="jplus",
            rows=(
                _Row(8, 1.0e-5, 1.0e-4),
                _Row(16, 2.0e-6, 2.0e-5),
            ),
        ),
        "folded": _Benchmark(
            profile="quick",
            backend_mode="folded",
            rows=(
                _Row(8, 1.4e-5, 1.3e-4),
                _Row(16, 2.6e-6, 2.5e-5),
            ),
        ),
    }


def test_render_poisson_galerkin_error_plot_svg_includes_backend_labels() -> None:
    svg = render_poisson_galerkin_error_plot_svg(
        _sample_benchmarks(),
        metric="abs_error",
        title="Poisson Galerkin",
    )

    assert "<svg" in svg
    assert "Poisson Galerkin" in svg
    assert "jplus" in svg
    assert "folded" in svg


def test_write_poisson_galerkin_error_plots_creates_svg_files(tmp_path: Path) -> None:
    artifacts = write_poisson_galerkin_error_plots(
        _sample_benchmarks(),
        output_dir=tmp_path,
        prefix="solver",
    )

    assert len(artifacts) == 2
    for artifact in artifacts:
        assert artifact.file_path.exists()
        assert artifact.file_path.read_text(encoding="utf-8").startswith("<svg")
