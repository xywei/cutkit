"""Cartesian 3D cut-cell scaffolding for folded-volume integration workflows."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

Axis3D = Literal["x", "y", "z"]


@dataclass(frozen=True)
class CartesianCell3D:
    """One Cartesian cell in a structured 3D grid."""

    ix: int
    iy: int
    iz: int
    x0: float
    x1: float
    y0: float
    y1: float
    z0: float
    z1: float

    @property
    def width(self) -> float:
        return self.x1 - self.x0

    @property
    def height(self) -> float:
        return self.y1 - self.y0

    @property
    def depth(self) -> float:
        return self.z1 - self.z0

    @property
    def volume(self) -> float:
        return self.width * self.height * self.depth


@dataclass(frozen=True)
class CellClip3D:
    """Coarse cut-state classification for one Cartesian 3D cell."""

    cell: CartesianCell3D
    kind: Literal["outside", "inside", "trimmed"]


def build_cartesian_grid_3d(
    *,
    resolution: int,
    bounds: tuple[float, float, float, float, float, float] = (
        0.0,
        0.0,
        0.0,
        1.0,
        1.0,
        1.0,
    ),
) -> tuple[CartesianCell3D, ...]:
    """Build a structured Cartesian grid over *bounds*."""

    if resolution < 1:
        raise ValueError("resolution must be positive")

    xmin, ymin, zmin, xmax, ymax, zmax = bounds
    hx = (xmax - xmin) / resolution
    hy = (ymax - ymin) / resolution
    hz = (zmax - zmin) / resolution

    cells: list[CartesianCell3D] = []
    for ix in range(resolution):
        x0 = xmin + ix * hx
        x1 = x0 + hx
        for iy in range(resolution):
            y0 = ymin + iy * hy
            y1 = y0 + hy
            for iz in range(resolution):
                z0 = zmin + iz * hz
                z1 = z0 + hz
                cells.append(
                    CartesianCell3D(
                        ix=ix,
                        iy=iy,
                        iz=iz,
                        x0=x0,
                        x1=x1,
                        y0=y0,
                        y1=y1,
                        z0=z0,
                        z1=z1,
                    )
                )

    return tuple(cells)


def classify_x_aligned_cell(
    cell: CartesianCell3D,
    *,
    surface_min_x: float | None,
    surface_max_x: float | None,
) -> CellClip3D:
    """Classify *cell* against an x-aligned trim interval.

    `surface_min_x` and `surface_max_x` are lower/upper bounds of the trimmed
    boundary x-location over the cell yz footprint.
    """

    return classify_axis_aligned_cell(
        cell,
        axis="x",
        surface_min=surface_min_x,
        surface_max=surface_max_x,
    )


def _cell_axis_interval(cell: CartesianCell3D, axis: Axis3D) -> tuple[float, float]:
    if axis == "x":
        return (cell.x0, cell.x1)
    if axis == "y":
        return (cell.y0, cell.y1)
    return (cell.z0, cell.z1)


def classify_axis_aligned_cell(
    cell: CartesianCell3D,
    *,
    axis: Axis3D,
    surface_min: float | None,
    surface_max: float | None,
) -> CellClip3D:
    """Classify *cell* against an axis-aligned trim interval.

    For the selected axis, ``surface_min``/``surface_max`` represent lower/upper
    bounds of the trimmed boundary coordinate over the orthogonal footprint.
    """

    if axis not in {"x", "y", "z"}:
        raise ValueError(f"unsupported axis: {axis!r}")

    if surface_min is None and surface_max is None:
        return CellClip3D(cell=cell, kind="outside")

    cell_lo, cell_hi = _cell_axis_interval(cell, axis)
    lo = cell_lo if surface_min is None else surface_min
    hi = cell_hi if surface_max is None else surface_max

    if lo >= cell_hi:
        return CellClip3D(cell=cell, kind="outside")
    if hi <= cell_lo:
        return CellClip3D(cell=cell, kind="inside")
    return CellClip3D(cell=cell, kind="trimmed")


def classify_y_aligned_cell(
    cell: CartesianCell3D,
    *,
    surface_min_y: float | None,
    surface_max_y: float | None,
) -> CellClip3D:
    """Classify *cell* against a y-aligned trim interval."""

    return classify_axis_aligned_cell(
        cell,
        axis="y",
        surface_min=surface_min_y,
        surface_max=surface_max_y,
    )


def classify_z_aligned_cell(
    cell: CartesianCell3D,
    *,
    surface_min_z: float | None,
    surface_max_z: float | None,
) -> CellClip3D:
    """Classify *cell* against a z-aligned trim interval."""

    return classify_axis_aligned_cell(
        cell,
        axis="z",
        surface_min=surface_min_z,
        surface_max=surface_max_z,
    )
