# UFL Form Backend Support

This document describes the current form support matrix for the shared UFL-style
form DSL entrypoint in `cutkit.formdsl`.

## Current Backends

- `iga`: trimmed-domain spline assembly using CUTKIT quadrature integration.
- `dgsem`: method-neutral lowering payload for meshmode+grudge adapters.

The parser now supports explicit `value_shape` metadata in `WeakFormIR` and
mapping payloads. Current backend support is:

- `iga`: scalar value shape only (`()`)
- `dgsem`: scalar and rank-1 vector value shapes (`()`, `(N,)`)

Mapping payloads that use vector/tensor space labels must declare
`value_shape`; otherwise parsing fails with a deterministic payload diagnostic.

## Geometry Map Support

`geometry_map` metadata defaults to `bspline` when omitted.

| `geometry_map` | iga | dgsem |
| --- | --- | --- |
| `bspline` | yes | yes |
| `nurbs` | yes (single-patch rational execution path) | no (`unsupported_geometry_map`) |

For `iga` + `geometry_map=nurbs`, formdsl now uses a deterministic
`nurbs_rational_single_patch` lowering path and records that execution mode in
the IGA payload metadata. Optional metadata key `nurbs_weights` can be provided
as a comma-separated positive weight vector with length equal to the IGA dof
count for the chosen `resolution` and `spline_degree`; otherwise unit weights
are used.

For rank-1 vector forms, mapping payload `source` terms support two
deterministic conventions:

- scalar source (`float`/callable/`null`): broadcast to each component,
- component tuple/list source: component-wise source values with length equal to
  `value_shape[0]`.

## Supported Term Subset

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
- `unsupported_geometry_map`
- `unsupported_value_shape`

## DG-SEM Prerequisite

The `dgsem` backend requires an explicit `MeshmodeCutOverlay` payload from
`cutkit.io` with `contract_version >= 1`. If missing, lowering raises
`PrerequisiteError` instead of attempting implicit translation.

Overlay viability is also mode-sensitive:

- strict mode: fails fast on overlay diagnostics or blocking statuses
  (`mapping_mismatch`, `orientation_mismatch`, `invalid_box`, `backend_error`).
- permissive mode: returns DG lowering payloads while forwarding deterministic
  overlay statuses/diagnostics in the DG payload.

## DG Flux/Trace Lowering (Initial Subset)

For the scalar subset, DG lowering emits deterministic operator-building payloads
based on grudge API blocks (for example `grudge.op.mass`,
`grudge.op.weak_local_grad`, `grudge.op.face_mass`, `grudge.op.project`).

For rank-1 vector forms on `dgsem`, lowering emits component-aware payload
entries (`component[i]:...` signatures and `component` metadata on lowering
entries) in stable component order.

- supported `dg_flux` families: `sipg` (default), `central`, `upwind`
- optional `dg_penalty`: positive float (used by `sipg`, defaults to `1.0`)

In strict mode, unsupported flux families or invalid penalties raise
`PrerequisiteError`. In permissive mode, lowering falls back to deterministic
defaults and records structured lowering diagnostics in the DG payload.

Current family operator behavior in lowering payloads:

| `dg_flux` family | Boundary operator chain | Interior operator chain | Penalty behavior |
| --- | --- | --- | --- |
| `sipg` | `bdry_trace_pair -> project -> face_mass -> inverse_mass` | `interior_trace_pairs -> project -> face_mass -> inverse_mass` | uses validated `dg_penalty` |
| `central` | `bdry_trace_pair -> project -> face_mass` | `interior_trace_pairs -> project -> face_mass` | ignores `dg_penalty` |
| `upwind` | `bdry_trace_pair -> project -> face_mass` | `interior_trace_pairs -> project -> face_mass` | ignores `dg_penalty` |

## Backend Parity Benchmark Example

Use the formdsl parity benchmark runner for a shared IGA + DG-SEM example:

```bash
uv run python scripts/run_formdsl_parity_benchmark.py --resolutions 8,16
```

This reports manufactured-solution IGA errors and deterministic DG lowering
signatures for the same form IR.

## Phase 3 Evaluation Notes

These are tracked outcomes from the Phase 3 backlog tasks:

- Vector-valued forms: initial MVP landed with explicit `value_shape`
  propagation in IR and DG-SEM lowering payloads, while IGA remains
  capability-gated to scalar shape.
- Additional DG flux families: `central` and `upwind` are now evaluated with
  deterministic lowering coverage; future work should refine physically richer
  upwind variants once full DG operator execution lands.
- NURBS and multipatch mapping: evaluation completed and tracked in
  `docs/formdsl-nurbs-multipatch-evaluation.md`; implementation remains staged
  behind explicit geometry-map and interface diagnostics.
