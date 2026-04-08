from __future__ import annotations

import argparse
import importlib.util
import sys
from pathlib import Path
from typing import Any

import pytest


def _load_script_module(script_name: str, module_name: str) -> Any:
    script_path = Path(__file__).resolve().parents[1] / "scripts" / script_name
    spec = importlib.util.spec_from_file_location(module_name, script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.path[0]
    return module


def _load_2d_wrapper_module() -> Any:
    return _load_script_module(
        "reproduce_antolin_2022_2d_examples.py", "repro_2d_wrapper"
    )


def _load_formdsl_parity_script_module() -> Any:
    return _load_script_module(
        "run_formdsl_parity_benchmark.py", "run_formdsl_parity_benchmark"
    )


def _load_formdsl_dgsem_example_script_module() -> Any:
    return _load_script_module(
        "run_formdsl_dgsem_lowering_example.py",
        "run_formdsl_dgsem_lowering_example",
    )


def _load_formdsl_step_001_script_module() -> Any:
    return _load_script_module(
        "run_formdsl_step_001_iga_poisson.py",
        "run_formdsl_step_001_iga_poisson",
    )


def _load_formdsl_step_002_script_module() -> Any:
    return _load_script_module(
        "run_formdsl_step_002_iga_multipatch_poisson.py",
        "run_formdsl_step_002_iga_multipatch_poisson",
    )


def _load_formdsl_step_003_script_module() -> Any:
    return _load_script_module(
        "run_formdsl_step_003_dgsem_poisson.py",
        "run_formdsl_step_003_dgsem_poisson",
    )


def test_2d_wrapper_injects_skip_3d_flag() -> None:
    module = _load_2d_wrapper_module()

    argv = ["reproduce_antolin_2022_2d_examples.py", "--sample-count", "16"]
    patched = module._ensure_skip_3d(argv)
    assert patched[1] == "--skip-3d"
    assert patched[2:] == argv[1:]


def test_2d_wrapper_does_not_duplicate_skip_3d_flag() -> None:
    module = _load_2d_wrapper_module()

    argv = [
        "reproduce_antolin_2022_2d_examples.py",
        "--skip-3d",
        "--sample-count",
        "16",
    ]
    patched = module._ensure_skip_3d(argv)
    assert patched == argv


def test_formdsl_parity_parser_accepts_csv_resolutions() -> None:
    module = _load_formdsl_parity_script_module()

    assert module._parse_resolutions("8, 16,32") == (8, 16, 32)


def test_formdsl_parity_parser_rejects_invalid_resolutions() -> None:
    module = _load_formdsl_parity_script_module()

    with pytest.raises(argparse.ArgumentTypeError):
        module._parse_resolutions("8, bad")
    with pytest.raises(argparse.ArgumentTypeError):
        module._parse_resolutions("0")
    with pytest.raises(argparse.ArgumentTypeError):
        module._parse_resolutions("   ")


def test_formdsl_dgsem_flux_parser_accepts_supported_values() -> None:
    module = _load_formdsl_dgsem_example_script_module()

    assert module._parse_flux_family("sipg") == "sipg"
    assert module._parse_flux_family(" CENTRAL ") == "central"


def test_formdsl_dgsem_flux_parser_rejects_invalid_values() -> None:
    module = _load_formdsl_dgsem_example_script_module()

    with pytest.raises(argparse.ArgumentTypeError):
        module._parse_flux_family("lax-friedrichs")


def test_formdsl_dgsem_demo_overlay_payload_contract() -> None:
    module = _load_formdsl_dgsem_example_script_module()

    payload = module._build_demo_overlay_payload()
    assert payload.contract_version == 1
    assert payload.statuses == ("ok",)
    assert payload.target_element_ids == (0,)


def test_formdsl_step_001_numeric_parsers() -> None:
    module = _load_formdsl_step_001_script_module()

    assert module._positive_int("16") == 16
    assert module._positive_float("1e-3") == pytest.approx(1.0e-3)

    with pytest.raises(argparse.ArgumentTypeError):
        module._positive_int("0")
    with pytest.raises(argparse.ArgumentTypeError):
        module._positive_float("-1")


def test_formdsl_step_002_form_payload_has_multipatch() -> None:
    module = _load_formdsl_step_002_script_module()

    payload = module._form_payload()
    assert payload["multipatch"] is not None
    assert payload["boundary_conditions"]


def test_formdsl_step_003_overlay_payload_size() -> None:
    module = _load_formdsl_step_003_script_module()

    overlay, snapshot = module._build_overlay_payload(
        resolution=5,
        sample_count=64,
        quadrature_order=2,
    )
    assert overlay.contract_version == 1
    assert len(overlay.target_element_ids) == 25
    assert len(overlay.statuses) == 25
    assert overlay.diagnostics == ()
    assert "ok" in overlay.statuses
    assert "empty" in overlay.statuses
    assert overlay.point_indptr_by_element[0] == 0
    assert overlay.point_indptr_by_element[-1] == len(overlay.point_coords)
    assert snapshot.resolution == 5
