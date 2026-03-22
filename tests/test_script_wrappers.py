from __future__ import annotations

import importlib.util
import sys
from pathlib import Path
from typing import Any


def _load_2d_wrapper_module() -> Any:
    script_path = (
        Path(__file__).resolve().parents[1]
        / "scripts"
        / "reproduce_antolin_2022_2d_examples.py"
    )
    spec = importlib.util.spec_from_file_location("repro_2d_wrapper", script_path)
    assert spec is not None
    assert spec.loader is not None

    module = importlib.util.module_from_spec(spec)
    sys.path.insert(0, str(script_path.parent))
    try:
        spec.loader.exec_module(module)
    finally:
        del sys.path[0]
    return module


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
