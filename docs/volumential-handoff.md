# Volumential Handoff Contract

This document defines the intended CUTKIT -> volumential interface boundary for
far/near potential workflows.

The key design choice is:

- CUTKIT emits geometric/quadrature/operator primitives.
- Volumential owns tree/list splitting and final interaction composition.

## Far-Field Export

Use `SignedSourceCloudBatch` from `cutkit.potentials` and materialize with
`as_volumential_arrays(...)`.

Returned fields:

- `dim`: `2` or `3`.
- `shape`: source-box batch shape.
- `coords`: tuple of coordinate arrays (`(x, y)` for 2D, `(x, y, z)` for 3D).
- `weights`: signed quadrature weights.
- `charges`: `density(point) * weight` (signed).
- `point_ptr`: per-source-box pointer array (`len = n_source_boxes + 1`).
- `source_box_index`: source-box index per point.
- `statuses` / `errors`: per-source-box status metadata.
- `backend_mode`, `order`: quadrature provenance.

Notes:

- Negative weights/charges are expected for folded decompositions.
- `point_ptr` and `source_box_index` preserve deterministic flatten ordering.

## Near-Field Export

### 1) Build restricted source sets from interaction lists

Use list plumbing helpers:

- `build_source_box_selection_from_lists(...)`
- `build_restricted_sources_from_selection(...)`
- or one-shot: `build_restricted_sources_from_interaction_lists(...)`

These convert `self/list1/list3/list4` source-box selections into
`RestrictedSourceBatch` for local solves.

### 2) Build local boundary traces

- `build_local_box_boundary_trace(...)` returns `BoundaryTraceBatch` with
  sampled trace points/values on each local box boundary.

### 3) Assemble near-field local operators

- `assemble_local_nearfield_operators(..., operator_mode="assembled")`
  returns `LocalOperatorBatch` with CSR payload.
- `assemble_local_nearfield_operators(..., operator_mode="matrix_free")`
  returns `LocalOperatorBatch` with matrix-free kernel id + descriptor.

For downstream consumers:

- `LocalOperatorBatch.as_assembled_arrays(...)`
- `LocalOperatorBatch.as_matrix_free_descriptor(...)`

Both include:

- `rhs`, `free_dof_ptr`
- `free_global_ptr`, `free_global_index`
- `fixed_dof_ptr`, `fixed_dof_index`, `fixed_dof_value`
- box/status metadata (`shape`, `box_bounds`, `statuses`, `errors`)

### 4) Optional CUTKIT local solve/evaluation

If needed for debugging/reference:

- `solve_local_operator_batch(...)`
- `build_nearfield_target_batch(...)`
- `evaluate_local_nearfield_targets(...)`

These are optional for volumential integration; you can also solve/evaluate
outside CUTKIT from exported operator data.

## Composition Ownership

For production volumential workflows, composition remains external:

- CUTKIT does **not** need to own final `far + near` orchestration.
- Volumential list logic determines whether to use
  `far + near` or `far - near_direct + near` style reconciliation.

CUTKIT provides `compose_far_and_near_potentials(...)` as an optional reference
utility only.

## Minimal Integration Skeleton

```python
from cutkit.potentials import (
    build_restricted_sources_from_interaction_lists,
    build_local_box_boundary_trace,
    assemble_local_nearfield_operators,
)

# far-field source cloud
cloud = solid.source_cloud_over_boxes(...)
cloud_arrays = cloud.as_volumential_arrays(use_numpy=True)

# list plumbing from your volumential neighborhood classification
restricted = build_restricted_sources_from_interaction_lists(
    source_cloud=cloud,
    shape=local_shape,
    self_boxes=self_list,
    list1_boxes=list1,
    list3_boxes=list3,
    list4_boxes=list4,
)

# local traces/operators
trace = build_local_box_boundary_trace(...)
ops = assemble_local_nearfield_operators(
    ...,
    restricted_sources=restricted,
    boundary_trace=trace,
    operator_mode="assembled",  # or "matrix_free"
)
ops_arrays = ops.as_assembled_arrays(use_numpy=True)
```
