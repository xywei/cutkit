# Meshmode Cut-Overlay Contract

`cutkit.io.build_meshmode_cut_overlay` builds a deterministic, versioned
overlay payload from CUTKIT element integration outputs using explicit
CUTKIT-to-target element mapping.

## API Surface

- `MeshmodeOverlayElement`: per-source CUTKIT payload (points, weights,
  metadata, status, orientation).
- `build_meshmode_cut_overlay(...)`: contract builder with strict/permissive
  validation behavior.
- `MeshmodeCutOverlay`: output payload containing:
  - `contract_version`
  - `target_element_ids`
  - `source_element_ids`
  - `statuses`
  - `diagnostics`
  - `point_indptr_by_element`, `point_coords`, `point_weights`
  - `geometry_metadata_by_element`

## Validation Modes

- `strict=True`: fail fast with `MeshmodeOverlayBuildError` on the first mapping
  or orientation mismatch.
- `strict=False`: return partial-success payloads and collect deterministic
  diagnostics for failed elements.

## Status Model

- Source-propagated statuses: `ok`, `empty`, `invalid_box`, `backend_error`
- Overlay validation statuses: `mapping_mismatch`, `orientation_mismatch`

## Marker For Downstream Consumers

The initial contract version is `1`. Downstream adapters should branch on
`contract_version` instead of relying on implicit positional assumptions.
