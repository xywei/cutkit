#!/usr/bin/env bash
set -euo pipefail

branch_name="$(git rev-parse --abbrev-ref HEAD)"

if [[ "${branch_name}" == "main" ]]; then
  printf "Direct pushes to 'main' are blocked. Open a PR from a feature branch.\n" >&2
  exit 1
fi
