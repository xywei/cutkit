#!/usr/bin/env python3
"""Run a deterministic DGSEM lowering-only example payload."""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict
from pathlib import Path
from typing import Any

from cutkit.formdsl import assemble_form
from cutkit.io import MeshmodeCutOverlay


def _parse_flux_family(raw: str) -> str:
    value = raw.strip().lower()
    if value in {"sipg", "central", "upwind"}:
        return value
    raise argparse.ArgumentTypeError("flux must be one of: sipg, central, upwind")


def _build_demo_overlay_payload() -> MeshmodeCutOverlay:
    return MeshmodeCutOverlay(
        contract_version=1,
        target_element_ids=(0,),
        source_element_ids=(0,),
        statuses=("ok",),
        diagnostics=(),
        point_indptr_by_element=(0, 0),
        point_coords=(),
        point_weights=(),
        geometry_metadata_by_element=((),),
    )


def _default_form_payload(*, flux_family: str) -> dict[str, object]:
    return {
        "trial_space": "P1",
        "test_space": "P1",
        "terms": [
            {"kind": "diffusion", "coefficient": 1.0},
            {"kind": "source", "coefficient": 1.0, "source": 1.0},
        ],
        "boundary_conditions": [
            {"kind": "essential", "boundary": "left", "value": 0.0},
            {"kind": "natural", "boundary": "right", "value": 1.0},
        ],
        "metadata": {"dg_flux": flux_family},
    }


def _print_signature_list(title: str, entries: tuple[str, ...]) -> None:
    print(title)
    for entry in entries:
        print(f"- {entry}")


def _print_operator_chains(payload: Any) -> None:
    print("Volume lowering operator chains")
    for entry in payload.volume_lowering:
        print(f"- {entry.kind}: {' -> '.join(entry.operator_chain)}")

    print("Trace lowering operator chains")
    for entry in payload.trace_lowering:
        print(f"- {entry.kind}:{entry.boundary}: {' -> '.join(entry.operator_chain)}")

    print("Flux lowering operator chains")
    for entry in payload.flux_lowering:
        boundary = entry.boundary if entry.boundary is not None else "interior"
        print(f"- {entry.role}:{boundary}: {' -> '.join(entry.operator_chain)}")


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Run one CUTKIT DGSEM lowering-only example (no grudge solve execution)"
        )
    )
    parser.add_argument(
        "--flux",
        type=_parse_flux_family,
        default="sipg",
        help="flux family: sipg, central, or upwind",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="enable strict backend checks",
    )
    parser.add_argument(
        "--manifest-path",
        type=Path,
        default=None,
        help="optional JSON output path for lowering payload",
    )
    args = parser.parse_args()

    result = assemble_form(
        _default_form_payload(flux_family=args.flux),
        backend="dgsem",
        strict=args.strict,
        overlay_payload=_build_demo_overlay_payload(),
    )
    payload = result.payload

    print("execution_mode = lowering_only")
    print("backend = dgsem")
    print(f"flux_family = {payload.flux_family}")
    print(f"geometry_map = {payload.geometry_map}")
    print()
    _print_signature_list("Volume signature", payload.volume_terms)
    _print_signature_list("Trace signature", payload.trace_terms)
    _print_signature_list("Flux signature", payload.flux_terms)
    print()
    _print_operator_chains(payload)

    if args.manifest_path is not None:
        data = {
            "backend": result.backend,
            "execution_mode": "lowering_only",
            "diagnostics": [asdict(diagnostic) for diagnostic in result.diagnostics],
            "payload": asdict(payload),
        }
        args.manifest_path.parent.mkdir(parents=True, exist_ok=True)
        args.manifest_path.write_text(
            json.dumps(data, indent=2, sort_keys=True) + "\n",
            encoding="utf-8",
        )
        print()
        print(f"wrote manifest: {args.manifest_path}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
