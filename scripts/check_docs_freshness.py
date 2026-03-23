#!/usr/bin/env python3
"""Check markdown cross-references for stale local paths."""

from __future__ import annotations

import argparse
from pathlib import Path

from cutkit.docs_freshness import find_missing_references


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--root",
        type=Path,
        default=Path(__file__).resolve().parents[1],
        help="Repository root to scan.",
    )
    return parser.parse_args()


def main() -> int:
    args = _parse_args()
    root = args.root.resolve()
    missing = find_missing_references(root)

    if not missing:
        print("Docs freshness check passed.")
        return 0

    print("Docs freshness check failed: stale cross-references found")
    for item in missing:
        source = item.source.relative_to(root)
        resolved = item.resolved
        try:
            resolved_display = resolved.relative_to(root)
        except ValueError:
            resolved_display = resolved
        if item.missing_anchor is None:
            print(f"- {source}: `{item.reference}` -> missing `{resolved_display}`")
        else:
            print(
                f"- {source}: `{item.reference}` -> missing anchor"
                f" `#{item.missing_anchor}` in `{resolved_display}`"
            )
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
