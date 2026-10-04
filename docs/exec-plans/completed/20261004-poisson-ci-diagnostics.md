# Make non-gating Poisson failures visible

## Objective

Expose failed numerical acceptance in CI without changing benchmark tolerances
or the intentionally non-gating smoke and scheduled workflows.

## Scope and acceptance

- Add a warning for failed runs using `--allow-fail`.
- Preserve strict exit status and JSON evidence.
- Test failing/passing, strict/non-gating, and local/Actions paths.
- Document the distinction between command success and numerical acceptance.
- Run the repository quality gate before handoff.

## Progress

- [x] Reproduce both quick backends reporting failed tolerances with exit 0.
- [x] Add explicit diagnostics and documentation.
- [x] Test all eight CLI outcomes; `make dev` passed on Python 3.12.
- [x] Verify repository review settings before publication.

## Outcome

`make dev` passed: formatting, Ruff, mypy, architecture, docs, the full 385-case
collection (one optional skip), and all 16 cut-panel evaluations. Eight new CLI
cases cover strict/non-gating failures and successes on local and Actions paths.
A real quick jplus run also emitted the expected Actions warning. Numerical
tolerances and non-gating workflow policy are unchanged.
