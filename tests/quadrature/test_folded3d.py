from __future__ import annotations

import math

import pytest

from cutkit.quadrature import (
    boundary_quadrature_rule_3d,
    folded_seeds_without_jplus_3d,
    integrate_bernstein_over_boundary_3d,
    integrate_general_over_boundary_3d,
    integrate_general_over_cartesian_grid_xsurface_3d,
    seed_grid_3d,
    signed_boundary_volume_3d,
)
from cutkit.topology import orient_boundary_triangles_outward


def _oriented_reference_tetra() -> tuple[
    tuple[
        tuple[float, float, float],
        tuple[float, float, float],
        tuple[float, float, float],
    ],
    ...,
]:
    v0 = (0.0, 0.0, 0.0)
    v1 = (1.0, 0.0, 0.0)
    v2 = (0.0, 1.0, 0.0)
    v3 = (0.0, 0.0, 1.0)
    return orient_boundary_triangles_outward(
        (
            (v0, v2, v1),
            (v0, v1, v3),
            (v0, v3, v2),
            (v1, v2, v3),
        )
    )


def test_seed_grid_3d_and_folded_exclusion_policy() -> None:
    seeds = seed_grid_3d(3)
    assert len(seeds) == 27

    jplus = (1.0, 1.0, 1.0)
    folded = folded_seeds_without_jplus_3d(seeds, jplus_seed=jplus)
    assert len(folded) == 26
    assert jplus not in folded


def test_boundary_quadrature_rule_3d_integrates_constant_to_volume() -> None:
    boundary = _oriented_reference_tetra()
    seed = (0.1, 0.1, 0.1)

    rule = boundary_quadrature_rule_3d(boundary, seed=seed, order=4)
    volume = signed_boundary_volume_3d(boundary, seed=seed)
    assert sum(rule.weights) == pytest.approx(volume, rel=1.0e-12, abs=1.0e-12)


def test_integrate_bernstein_over_boundary_degree0_matches_volume() -> None:
    boundary = _oriented_reference_tetra()
    seed = (0.1, 0.1, 0.1)

    values = integrate_bernstein_over_boundary_3d(
        boundary, seed=seed, degree=0, order=5
    )
    assert len(values) == 1
    assert values[0] == pytest.approx(1.0 / 6.0, rel=1.0e-12, abs=1.0e-12)


def test_integrate_general_over_boundary_matches_reference_moment() -> None:
    boundary = _oriented_reference_tetra()
    seed = (0.1, 0.1, 0.1)

    value = integrate_general_over_boundary_3d(
        boundary,
        seed=seed,
        order=7,
        integrand=lambda x, y, z: x + y + z,
    )
    assert value == pytest.approx(1.0 / 8.0, rel=1.0e-10, abs=1.0e-10)


def test_integrate_general_over_cartesian_grid_xsurface_3d_cube_fraction() -> None:
    full_cube = integrate_general_over_cartesian_grid_xsurface_3d(
        resolution=4,
        order=4,
        x_surface_from_yz=lambda _y, _z: 0.0,
        integrand=lambda _x, _y, _z: 1.0,
    )
    assert full_cube == pytest.approx(1.0, rel=1.0e-12, abs=1.0e-12)

    half_cube = integrate_general_over_cartesian_grid_xsurface_3d(
        resolution=4,
        order=4,
        x_surface_from_yz=lambda _y, _z: 0.5,
        integrand=lambda _x, _y, _z: 1.0,
    )
    assert half_cube == pytest.approx(0.5, rel=1.0e-12, abs=1.0e-12)


def test_integrate_general_over_boundary_supports_scalar_only_callable() -> None:
    boundary = _oriented_reference_tetra()
    seed = (0.1, 0.1, 0.1)

    value = integrate_general_over_boundary_3d(
        boundary,
        seed=seed,
        order=7,
        integrand=lambda x, y, z: math.sin(x) * 0.0 + x + y + z,
    )
    assert value == pytest.approx(1.0 / 8.0, rel=1.0e-10, abs=1.0e-10)


def test_integrate_cartesian_xsurface_supports_scalar_only_callable() -> None:
    value = integrate_general_over_cartesian_grid_xsurface_3d(
        resolution=4,
        order=4,
        x_surface_from_yz=lambda _y, _z: 0.5,
        integrand=lambda x, _y, _z: math.sin(x) * 0.0 + 1.0,
    )
    assert value == pytest.approx(0.5, rel=1.0e-12, abs=1.0e-12)
