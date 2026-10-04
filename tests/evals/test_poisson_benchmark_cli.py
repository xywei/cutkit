from __future__ import annotations

import importlib.util
import json
from pathlib import Path
import sys

import pytest

from cutkit.evals.poisson_benchmarks import (
    PlanarPoissonBenchmarkResult,
    PoissonBenchmarkResult,
    VolumePoissonBenchmarkResult,
)


@pytest.mark.parametrize("passed", [False, True])
@pytest.mark.parametrize("allow_fail", [False, True])
@pytest.mark.parametrize("github_actions", [False, True])
def test_cli_reports_numerical_failure_without_changing_exit_contract(
    passed: bool,
    allow_fail: bool,
    github_actions: bool,
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
    capsys: pytest.CaptureFixture[str],
) -> None:
    script = Path(__file__).resolve().parents[2] / "scripts/run_poisson_benchmarks.py"
    spec = importlib.util.spec_from_file_location("poisson_benchmark_cli", script)
    assert spec is not None and spec.loader is not None
    cli = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cli)
    result = PoissonBenchmarkResult(
        profile="quick",
        planar=PlanarPoissonBenchmarkResult("jplus", 1.0, (), 0.001, 0.01, passed),
        volume=VolumePoissonBenchmarkResult("jplus", 5, 1.0, (), 0.001, 0.01, passed),
        passed=passed,
    )
    monkeypatch.setattr(cli, "run_poisson_benchmarks", lambda **kwargs: result)
    manifest = tmp_path / "result.json"
    args = [str(script), "--manifest-path", str(manifest)]
    if allow_fail:
        args.append("--allow-fail")
    monkeypatch.setattr(sys, "argv", args)
    monkeypatch.setenv("GITHUB_ACTIONS", "true" if github_actions else "false")

    assert cli.main() == (0 if passed or allow_fail else 1)
    captured = capsys.readouterr()
    assert json.loads(manifest.read_text())["passed"] is passed
    assert f"overall_passed = {passed}" in captured.out
    should_warn = not passed and allow_fail
    assert ("::warning::" in captured.out) is (should_warn and github_actions)
    assert ("WARNING:" in captured.err) is (should_warn and not github_actions)
    assert ("not numerical acceptance" in captured.out + captured.err) is should_warn
