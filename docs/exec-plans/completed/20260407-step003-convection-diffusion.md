# Step-003 Convection-Diffusion Upgrade

## Objective

Upgrade FormDSL DG step-003 from diffusion/reaction-only Poisson prototype to a
convection-diffusion setup, while keeping trimmed-overlay execution and end-to-end
runtime validation on `ipa`.

## Scope

- Add DGSEM capability/lowering support for a `convection` term kind.
- Extend DGSEM solver assembly to include a convection contribution.
- Use a non-symmetric linear solve path when convection is present.
- Update step-003 payload/labels/docs to describe convection-diffusion.
- Add/adjust tests for new term support and behavior.

## Acceptance Criteria

- `assemble_form(..., backend="dgsem")` accepts `convection` terms.
- Step-003 form includes a convection term and no longer presents itself as
  Poisson-only.
- Local checks pass (`make dev`).
- Step-003 run on `ipa` succeeds for at least one resolution with convection and
  reports passing residual checks.

## Checklist

- [x] Add `convection` to DGSEM supported-term capabilities.
- [x] Extend DGSEM lowering to emit deterministic convection volume lowering.
- [x] Extend solver matrix assembly with convection contribution.
- [x] Add non-symmetric linear solve fallback for convection cases.
- [x] Update step-003 form payload and reporting strings.
- [x] Update/expand FormDSL tests for convection support.
- [x] Validate locally and on `ipa`.

## Outcomes

- DGSEM now supports `convection` in capability checks and lowering payloads.
- Step-003 payload and reporting now describe convection-diffusion.
- DGSEM solve path now chooses a non-symmetric solver when convection is present
  (`bicgstab` with `cgne` fallback).
- Local `make dev` passes, and `ipa` step-003 runs pass at resolutions 8, 16,
  and 24.
