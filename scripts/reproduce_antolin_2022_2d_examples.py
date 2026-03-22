#!/usr/bin/env python3
"""Compatibility wrapper for the Antolin Section 6 reproduction script."""

from __future__ import annotations

import sys

from reproduce_antolin_2022_examples import main


def _ensure_skip_3d(argv: list[str]) -> list[str]:
    if "--skip-3d" in argv[1:]:
        return argv
    return [argv[0], "--skip-3d", *argv[1:]]


if __name__ == "__main__":
    sys.argv = _ensure_skip_3d(sys.argv)
    raise SystemExit(main())
