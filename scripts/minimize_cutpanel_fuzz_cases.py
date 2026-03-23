#!/usr/bin/env python3
"""Deterministically minimize fuzz candidate cut-panel fixtures."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from cutkit.evals import (
    case_to_fixture_payload,
    cases_from_fixture_payload,
    minimize_fuzz_cases,
)


def _parse_args() -> argparse.Namespace:
    repo_root = Path(__file__).resolve().parents[1]
    fixtures_dir = repo_root / "src" / "cutkit" / "evals" / "fixtures"

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input",
        type=Path,
        default=fixtures_dir / "cutpanel-fuzz-candidates.json",
        help="Input fuzz candidate fixture JSON.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=fixtures_dir / "cutpanel-fuzz-derived.json",
        help="Output minimized fuzz-derived fixture JSON.",
    )
    parser.add_argument(
        "--max-cases",
        type=int,
        default=6,
        help="Maximum number of minimized cases to keep.",
    )
    parser.add_argument(
        "--seed",
        default="cutkit-corpus-v2",
        help="Deterministic seed label embedded in output payload.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    repo_root = Path(__file__).resolve().parents[1]
    input_path = args.input.resolve()
    output_path = args.output.resolve()

    try:
        input_display = str(input_path.relative_to(repo_root))
    except ValueError:
        input_display = str(input_path)

    payload = json.loads(input_path.read_text(encoding="utf-8"))
    cases = cases_from_fixture_payload(payload)
    minimized = minimize_fuzz_cases(tuple(cases), max_cases=args.max_cases)
    deduplicated = minimize_fuzz_cases(tuple(cases), max_cases=max(1, len(cases)))

    output_payload = {
        "schema_version": 1,
        "source": "fuzz-derived",
        "seed": args.seed,
        "minimization": {
            "input": input_display,
            "input_case_count": len(cases),
            "deduplicated_case_count": len(deduplicated),
            "selected_case_count": len(minimized),
            "max_cases": args.max_cases,
        },
        "cases": [case_to_fixture_payload(case) for case in minimized],
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(
        json.dumps(output_payload, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    print(
        "Minimized fuzz fixture: "
        f"input={len(cases)} deduplicated={len(deduplicated)} selected={len(minimized)}"
    )
    print(f"Wrote {output_path}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
