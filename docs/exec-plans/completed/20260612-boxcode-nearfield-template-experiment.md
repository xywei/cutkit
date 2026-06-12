# Box-Code Near-Field Template Experiment

## Objective

Evaluate whether folded-decomposition charts can support reusable near-field
template corrections for box-code and Volumential-style workflows.

## Scope

- Derive the mapped-kernel form for a 2D fan folded piece.
- Include both point-target and target-piece bilinear near-field forms.
- Identify singular factors that can be separated from smooth geometry payloads.
- Frame the reuse hypothesis as a functional expansion in smooth metric fields
  `M(z)`, not just as raw runtime geometry data.
- Add a small analytic experiment driver with deterministic tests.
- Document feasibility limits and the next CUTKIT/Volumential boundary.

## Non-Goals

- No production Volumential integration in this branch.
- No CAD dependency for the first prototype.
- No claim that arbitrary cut shapes have finite exact correction tables.

## Acceptance Criteria

- The derivation states the mapped self-interaction form and its split.
- The derivation records the point-target form, bilinear form, interaction
  taxonomy, and measurement criteria from issue 61.
- The prototype records a self or adjacent template experiment with a direct
  high-order reference value.
- Tests check the experiment against an analytic or independently computed
  invariant.
- Documentation explains whether the idea is feasible and what data must remain
  runtime geometry payload.

## Completed Checklist

- [x] Read issue 61 and repository orientation docs.
- [x] Work through the 2D fan-map singularity derivation.
- [x] Add an experiment module or script for the near-field template prototype.
- [x] Add tests for the prototype invariants.
- [x] Update docs and doc index if new documentation is added.
- [x] Run targeted tests and `make dev`.
- [x] Move this plan to completed with outcomes.

## Outcomes

- The near-field template idea is feasible as a CUTKIT experiment: singular and
  nearly singular folded-piece interactions can be expressed on fixed template
  domains.
- The reusable singular part is a template-space log singular model. The metric
  field `M(z) = DT(z)^T DT(z)` and higher-order terms are smooth geometry data.
- The practical reuse hypothesis is that a functional expansion in `M(z)` and
  smooth-remainder data covers the folded-decomposition cases with few modes.
- The first prototype covers analytic straight fan maps, point-target
  integrals, bilinear self interactions, a log-kernel scale-law check, and a
  diagonal metric-remainder sample.

## Validation

- `uv run --extra dev python -m pytest tests/evals/test_nearfield_templates.py tests/test_script_wrappers.py`
- `uv run --extra dev python scripts/run_nearfield_template_experiment.py --order 6`
- `make dev`

## Remaining Risks

- Template corrections may be reusable only after parameterized compression, not
  as shape-independent lookup tables.
- Self-interaction singular quadrature may need specialized rules beyond the
  first direct high-order reference prototype.
- Curved analytic pieces and adjacent-piece cases still need follow-up coverage.
