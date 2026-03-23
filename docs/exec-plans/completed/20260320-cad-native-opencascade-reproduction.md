# CAD-Native Reproduction

## Objective

Shift the Section 6 reproduction track from polygonized MVP geometry to a
CAD-native workflow and designate OpenCascade as the CAD core for exact
geometry clipping.

## Scope

- Add CAD-native curve-loop primitives and folded quadrature for curved edges.
- Add OpenCascade-backed Section 6.1.1/6.1.2 face construction and cell clipping.
- Add CAD-native 2D Section 6.1/6.2 experiment entry points.
- Add script support for selecting CAD-native vs polygonized 2D mode.
- Update docs to reflect CAD-native direction and OpenCascade backend.

## Non-Goals

- Replacing existing polygonized workflows used for MVP fallback.
- Reworking 3D experiments in this change.

## Acceptance Criteria

- New CAD-native helpers are available behind OpenCascade availability checks.
- Existing polygonized tests continue to pass.
- New curve-folded quadrature tests pass.
- `make check` passes in the default development environment.

## Checklist

- [x] Add curve-loop geometry types for CAD-native 2D boundaries.
- [x] Add folded quadrature over curved edges.
- [x] Add OpenCascade adapter module for Section 6 CAD faces and rectangle clipping.
- [x] Add CAD-native polynomial/general 2D experiment runners.
- [x] Add script mode selector (`auto`, `polygonized`, `cad-native`).
- [x] Update docs to reflect CAD-native + OpenCascade direction.
- [x] Run full checks.

## Final Outcome

- Status: merged.
- Delivered via: `https://github.com/xywei/cutkit/pull/6`
- Follow-ups: 3D core and parity scaffolding landed in
  `https://github.com/xywei/cutkit/pull/7`.
