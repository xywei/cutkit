from __future__ import annotations

import pytest

from cutkit.io import (
    ElementId,
    MeshmodeOverlayBuildError,
    MeshmodeOverlayElement,
    build_meshmode_cut_overlay,
)


def test_overlay_nominal_meshmode_style_layout() -> None:
    targets = (40, 10, 30, 20)
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s20",
            points=((0.65, 0.20),),
            weights=(0.5,),
            geometry_metadata={"status": "trimmed"},
        ),
        MeshmodeOverlayElement(
            source_element_id="s40",
            points=((0.15, 0.70), (0.22, 0.75)),
            weights=(0.3, 0.7),
            geometry_metadata={"region": "north", "cut_fraction": 0.85},
        ),
        MeshmodeOverlayElement(
            source_element_id="s10",
            points=((0.12, 0.15),),
            weights=(1.0,),
            geometry_metadata={"cut_fraction": 1.0},
        ),
        MeshmodeOverlayElement(
            source_element_id="s30",
            points=((0.45, 0.45), (0.52, 0.40)),
            weights=(0.2, 0.8),
            geometry_metadata={"region": "inner", "touches_boundary": True},
        ),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=targets,
        element_id_map={"s10": 10, "s20": 20, "s30": 30, "s40": 40},
        strict=True,
    )

    assert overlay.target_element_ids == targets
    assert overlay.source_element_ids == ("s40", "s10", "s30", "s20")
    assert overlay.statuses == ("ok", "ok", "ok", "ok")
    assert overlay.point_indptr_by_element == (0, 2, 3, 5, 6)
    assert overlay.point_coords == (
        (0.15, 0.70),
        (0.22, 0.75),
        (0.12, 0.15),
        (0.45, 0.45),
        (0.52, 0.40),
        (0.65, 0.20),
    )
    assert overlay.point_weights == (0.3, 0.7, 1.0, 0.2, 0.8, 0.5)
    assert overlay.geometry_metadata_by_element == (
        (("cut_fraction", "0.85"), ("region", "north")),
        (("cut_fraction", "1.0"),),
        (("region", "inner"), ("touches_boundary", "True")),
        (("status", "trimmed"),),
    )
    assert not overlay.diagnostics


def _mixed_overlay_inputs() -> tuple[
    tuple[MeshmodeOverlayElement, ...],
    dict[ElementId, ElementId],
    tuple[int, ...],
]:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s10",
            points=((0.10, 0.10), (0.15, 0.12)),
            weights=(0.4, 0.6),
        ),
        MeshmodeOverlayElement(
            source_element_id="s11",
            status="invalid_box",
        ),
        MeshmodeOverlayElement(
            source_element_id="s12",
            points=((0.50, 0.50),),
            weights=(1.0,),
            orientation=-1,
        ),
        MeshmodeOverlayElement(
            source_element_id="s-orphan",
            points=((0.90, 0.90),),
            weights=(1.0,),
        ),
    )
    mapping: dict[ElementId, ElementId] = {
        "s10": 10,
        "s11": 11,
        "s12": 12,
        "missing-13": 13,
        "ghost-99": 99,
    }
    targets = (10, 11, 12, 13, 14)
    return elements, mapping, targets


def test_overlay_mixed_meshmode_style_layout_permissive() -> None:
    elements, mapping, targets = _mixed_overlay_inputs()

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=targets,
        element_id_map=mapping,
        expected_orientation_by_target={12: 1},
        strict=False,
    )

    assert overlay.target_element_ids == targets
    assert overlay.source_element_ids == ("s10", "s11", "s12", "missing-13", None)
    assert overlay.statuses == (
        "ok",
        "invalid_box",
        "orientation_mismatch",
        "mapping_mismatch",
        "mapping_mismatch",
    )
    assert overlay.point_indptr_by_element == (0, 2, 2, 2, 2, 2)
    assert overlay.point_coords == ((0.10, 0.10), (0.15, 0.12))
    assert overlay.point_weights == (0.4, 0.6)

    codes = {diagnostic.code for diagnostic in overlay.diagnostics}
    assert {
        "unknown_target",
        "source_unmapped",
        "orientation_mismatch",
        "mapped_source_missing",
        "target_unmapped",
    }.issubset(codes)


def test_overlay_mixed_meshmode_style_layout_strict_fails_fast() -> None:
    elements, mapping, targets = _mixed_overlay_inputs()

    with pytest.raises(MeshmodeOverlayBuildError) as error:
        build_meshmode_cut_overlay(
            elements,
            target_element_ids=targets,
            element_id_map=mapping,
            expected_orientation_by_target={12: 1},
            strict=True,
        )

    assert error.value.diagnostic.code == "unknown_target"
