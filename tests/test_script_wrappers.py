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
