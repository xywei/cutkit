from __future__ import annotations

import pytest

from cutkit.io import (
    MeshmodeCutOverlay,
    MeshmodeOverlayBuildError,
    MeshmodeOverlayElement,
    build_meshmode_cut_overlay,
)


def test_overlay_build_success_preserves_target_order() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0), (1.0, 0.0)),
            weights=(0.2, 0.3),
            geometry_metadata={"zeta": 1, "alpha": "left"},
        ),
        MeshmodeOverlayElement(
            source_element_id="s2",
            points=((0.5, 0.5),),
            weights=(0.9,),
            geometry_metadata={"beta": "trimmed"},
        ),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=(11, 10),
        element_id_map={"s1": 10, "s2": 11},
    )

    assert overlay.target_element_ids == (11, 10)
    assert overlay.source_element_ids == ("s2", "s1")
    assert overlay.statuses == ("ok", "ok")
    assert overlay.point_indptr_by_element == (0, 1, 3)
    assert overlay.point_coords == ((0.5, 0.5), (0.0, 0.0), (1.0, 0.0))
    assert overlay.point_weights == (0.9, 0.2, 0.3)
    assert overlay.geometry_metadata_by_element == (
        (("beta", "trimmed"),),
        (("alpha", "left"), ("zeta", "1")),
    )
    assert not overlay.diagnostics


def test_overlay_strict_fails_fast_on_target_unmapped() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
        ),
    )

    with pytest.raises(MeshmodeOverlayBuildError) as error:
        build_meshmode_cut_overlay(
            elements,
            target_element_ids=(10, 11),
            element_id_map={"s1": 10},
            strict=True,
        )

    assert error.value.diagnostic.code == "target_unmapped"
    assert error.value.diagnostic.target_element_id == 11


def test_overlay_permissive_returns_partial_results_for_mapping_mismatch() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
        ),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=(10, 11),
        element_id_map={"s1": 10},
        strict=False,
    )

    assert overlay.statuses == ("ok", "mapping_mismatch")
    assert overlay.point_indptr_by_element == (0, 1, 1)
    assert any(
        diagnostic.code == "target_unmapped" for diagnostic in overlay.diagnostics
    )


def test_overlay_permissive_reports_orientation_mismatch() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
            orientation=-1,
        ),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=(10,),
        element_id_map={"s1": 10},
        expected_orientation_by_target={10: 1},
        strict=False,
    )

    assert overlay.statuses == ("orientation_mismatch",)
    assert overlay.point_indptr_by_element == (0, 0)
    assert any(
        diagnostic.code == "orientation_mismatch" for diagnostic in overlay.diagnostics
    )


def test_overlay_rejects_non_integral_expected_orientation() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
            orientation=1,
        ),
    )

    with pytest.raises(ValueError, match=r"\+1 or -1 integers"):
        build_meshmode_cut_overlay(
            elements,
            target_element_ids=(10,),
            element_id_map={"s1": 10},
            expected_orientation_by_target={10: 1.9},
        )


def test_overlay_element_rejects_boolean_orientation() -> None:
    with pytest.raises(ValueError, match=r"\+1 or -1 integer"):
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
            orientation=True,
        )


def test_overlay_strict_rejects_mapping_to_unknown_target() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
        ),
        MeshmodeOverlayElement(
            source_element_id="s2",
            points=((1.0, 1.0),),
            weights=(2.0,),
        ),
    )

    with pytest.raises(MeshmodeOverlayBuildError) as error:
        build_meshmode_cut_overlay(
            elements,
            target_element_ids=(10,),
            element_id_map={"s1": 10, "s2": 99},
            strict=True,
        )

    assert error.value.diagnostic.code == "unknown_target"
    assert error.value.diagnostic.target_element_id == 99


def test_overlay_propagates_source_status_and_empty_elements() -> None:
    elements = (
        MeshmodeOverlayElement(source_element_id="s1", status="invalid_box"),
        MeshmodeOverlayElement(source_element_id="s2"),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=(10, 11),
        element_id_map={"s1": 10, "s2": 11},
    )

    assert overlay.statuses == ("invalid_box", "empty")
    assert overlay.point_indptr_by_element == (0, 0, 0)
    assert not overlay.point_coords
    assert not overlay.point_weights
    assert not overlay.diagnostics


def test_overlay_permissive_duplicate_source_marks_mapping_mismatch() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
        ),
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((1.0, 1.0),),
            weights=(2.0,),
        ),
    )

    overlay = build_meshmode_cut_overlay(
        elements,
        target_element_ids=(10,),
        element_id_map={"s1": 10},
        strict=False,
    )

    assert overlay.statuses == ("mapping_mismatch",)
    assert overlay.point_indptr_by_element == (0, 0)
    assert any(
        diagnostic.code == "duplicate_source" for diagnostic in overlay.diagnostics
    )
    assert any(
        diagnostic.code == "target_ambiguous" for diagnostic in overlay.diagnostics
    )


def test_overlay_rejects_unknown_orientation_override_target() -> None:
    elements = (
        MeshmodeOverlayElement(
            source_element_id="s1",
            points=((0.0, 0.0),),
            weights=(1.0,),
        ),
    )

    with pytest.raises(ValueError, match="unknown target element"):
        build_meshmode_cut_overlay(
            elements,
            target_element_ids=(10,),
            element_id_map={"s1": 10},
            expected_orientation_by_target={99: 1},
            strict=False,
        )


def test_overlay_payload_rejects_nonzero_indptr_prefix() -> None:
    with pytest.raises(ValueError, match="must start at 0"):
        MeshmodeCutOverlay(
            contract_version=1,
            target_element_ids=(10,),
            source_element_ids=("s1",),
            statuses=("ok",),
            diagnostics=(),
            point_indptr_by_element=(1, 1),
            point_coords=(),
            point_weights=(),
            geometry_metadata_by_element=((),),
        )
