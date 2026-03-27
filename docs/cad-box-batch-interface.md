# CAD Box Batch Interface

CUTKIT provides a consumer-facing CAD facade in `cutkit.cad` for loading BREP
geometry, clipping with one or many axis-aligned boxes, and running folded
integration workflows.

## Entry Points

- `CadSession.opencascade()`
- `CadFace2D` and `CadSolid3D` handles
- `Box2D` / `Box3D` scalar objects
- `Box2DArray` / `Box3DArray` array-mode containers

## Input Pattern: Object Or Arrays

Batch APIs accept one of the following input styles:

1. Object mode: `boxes=Box*` or `boxes=Sequence[Box*]`
2. Array mode: `boxes=Box*Array(...)`
3. Array mode: explicit coordinate arrays (`x0=...`, `x1=...`, ...)

Do not mix `boxes=...` and explicit coordinate arrays in the same call.

Scalar values broadcast against array inputs in batch mode.

## 3D Example

```python
from cutkit.cad import Box3D, CadSession

cad = CadSession.opencascade()
solid = cad.load_solid("example-solid.brep")

# Single box clip + folded integration
clipped = solid.clip_box(Box3D(x0=0.0, x1=0.5, y0=0.0, y1=1.0, z0=0.0, z1=1.0))
value = clipped.integrate_folded_boundary(
    integrand=lambda x, y, z: x + y + z,
    order=5,
)

# Many boxes, array mode
batch = solid.integrate_over_boxes(
    integrand=lambda x, y, z: 1.0,
    order=5,
    x0=[0.0, 0.5],
    x1=[0.5, 1.0],
    y0=0.0,
    y1=1.0,
    z0=0.0,
    z1=1.0,
    strict=False,
)

print(batch.statuses)
print(batch.values)
```

## 2D Example

```python
from cutkit.cad import Box2DArray, CadSession

cad = CadSession.opencascade()
face = cad.load_face("example-face.brep")

batch = face.integrate_over_boxes(
    integrand=lambda x, y: x * x + y,
    order=5,
    boxes=Box2DArray(
        x0=[0.0, 0.5],
        x1=[0.5, 1.0],
        y0=0.0,
        y1=1.0,
    ),
    strict=False,
)

print(batch.statuses)
print(batch.values)
```

## Batch Statuses

- `ok`: successful clip/integration result
- `empty`: valid box produced empty clipped geometry
- `invalid_box`: invalid bounds (for example `x1 <= x0`)
- `backend_error`: CAD/mesh backend failure for that entry

Use `strict=True` (default) to raise immediately for invalid/backend errors.
Use `strict=False` to collect per-box status and continue.
