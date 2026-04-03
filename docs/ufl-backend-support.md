# UFL Form Backend Support

This document describes the current scalar-form support matrix for the shared
UFL-style form DSL entrypoint in `cutkit.formdsl`.

## Current Backends

- `iga`: trimmed-domain spline assembly using CUTKIT quadrature integration.
- `dgsem`: method-neutral lowering payload for meshmode+grudge adapters.

## Supported Scalar Term Subset

| Term kind | iga | dgsem |
| --- | --- | --- |
| `diffusion` | yes | yes |
| `mass` | yes | yes |
| `reaction` | yes | yes |
| `source` | yes | yes |

## Supported Boundary Conditions

| Boundary condition kind | iga | dgsem |
| --- | --- | --- |
| `essential` | yes | yes |
| `natural` | yes | yes |

Boundary selectors currently use: `all`, `left`, `right`, `bottom`, `top`.

Natural loads on `iga` are integrated over the trimmed panel boundary geometry.
Selectors `left|right|bottom|top` are geometric filters on boundary segments that
lie on the corresponding effective bounding-box side.

Marker selectors are also supported via `marker:<id>` when metadata provides a
mapping key `boundary_marker:<id>` to one of `all|left|right|bottom|top`.

## Deterministic Capability Diagnostics

`cutkit.formdsl` provides strict and permissive capability checks:

- strict mode (`strict=True`): raises `CapabilityError` with deterministic code
  and backend metadata.
- permissive mode (`strict=False`): returns diagnostics in the assembly result
  and proceeds with lowering.

Common diagnostic codes:

- `unsupported_term`
- `unsupported_boundary_condition`

## DG-SEM Prerequisite

The `dgsem` backend requires an explicit `MeshmodeCutOverlay` payload from
`cutkit.io` with `contract_version >= 1`. If missing, lowering raises
`PrerequisiteError` instead of attempting implicit translation.

Overlay viability is also mode-sensitive:

- strict mode: fails fast on overlay diagnostics or blocking statuses
  (`mapping_mismatch`, `orientation_mismatch`, `invalid_box`, `backend_error`).
- permissive mode: returns DG lowering payloads while forwarding deterministic
  overlay statuses/diagnostics in the DG payload.

## Phase 3 Evaluation Notes

These are tracked outcomes from the Phase 3 backlog tasks:

- Vector-valued forms: defer until scalar parity metrics stabilize; extend IR
  with explicit component shape and tensor contraction metadata.
- Additional DG flux families: prioritize `central` and `upwind` as next
  add-ons after SIPG parity checks.
- NURBS and multipatch mapping: postpone until B-spline single-patch parity is
  stable; add geometry-map diagnostics before enabling rational terms.
