# DMK-Style Near-Field Split Report

Date: 2026-06-12

Remote runner: `ipa`

Command:

```bash
PYTHONPATH=src python3 scripts/run_nearfield_template_experiment.py \
  --dmk-split-report \
  --orders 4,6,8,10,14,18,24 \
  --sigmas 0.08,0.16,0.32 \
  --reference-order 128
```

Raw JSON and Markdown artifacts were generated on `ipa` in the remote run
directory and copied to the local temporary workspace for summarization. A second
residual-inclusive run was generated with the same parameters after adding direct
quadrature of `G_{\mathrm{local},\sigma}`. The raw artifacts are not checked in
because the concise tables below capture the relevant results.

## Setup

The experiment uses two straight-edge polygon fixtures, each integrated as a
signed sum of folded fans from a shared seed to each boundary edge. It compares:

- full 2D log-kernel folded quadrature;
- smooth Ewald/heat-kernel complement folded quadrature;
- the implied localized residual, measured as `full_reference - smooth_reference`.

The split is

$$
G(r)=G_{\mathrm{smooth},\sigma}(r)+G_{\mathrm{local},\sigma}(r),
\qquad
G_{\mathrm{local},\sigma}(r)=\frac{1}{4\pi}E_1(r^2/\sigma^2),
$$

where `E1` is the exponential integral. The smoothed complement has a removable
limit at `r=0`, so ordinary folded quadrature no longer sees the log singularity.

Targets cover interior, boundary-near-inside, boundary-near-outside, and
vertex-near-inside cases. Seed modes are the current robust interior anchor and a
simple node barycenter.

## Summary

At the highest tested order, `order=24`, the smoothed folded quadrature was
consistently more accurate than direct full-log quadrature.

sigma | min improvement | median improvement | max improvement | median local/full
--- | --- | --- | --- | ---
0.08 | 9.252e+01 | 1.805e+03 | 3.986e+04 | 1.347e-02
0.16 | 7.045e+01 | 6.599e+02 | 5.466e+04 | 4.753e-02
0.32 | 1.179e+02 | 1.359e+03 | 4.176e+04 | 1.530e-01

Target class | min improvement | median improvement | max improvement
--- | --- | --- | ---
boundary_near_inside | 9.327e+01 | 1.158e+04 | 5.466e+04
boundary_near_outside | 7.045e+01 | 8.439e+02 | 1.479e+04
interior | 1.479e+02 | 1.415e+03 | 4.176e+04
vertex_near_inside | 9.366e+01 | 5.099e+02 | 1.890e+03

Here `improvement = full_abs_error / smooth_abs_error` against the same
high-order reference. The smallest improvement is still about `70x`; median
improvements are hundreds to tens of thousands depending on target class and
window width.

Relative errors for the same `order=24` samples show the same pattern:

sigma | full rel err median | smooth rel err median | local rel err median | reconstructed rel err median
--- | ---: | ---: | ---: | ---:
0.08 | 5.691e-05 | 9.370e-08 | 8.892e-03 | 5.691e-05
0.16 | 5.691e-05 | 7.368e-08 | 1.629e-03 | 5.691e-05
0.32 | 5.691e-05 | 6.844e-08 | 4.190e-04 | 5.691e-05

Target class | full rel err median | smooth rel err median | local rel err median | reconstructed rel err median
--- | ---: | ---: | ---: | ---:
boundary_near_inside | 1.147e-03 | 7.614e-08 | 1.494e-02 | 1.147e-03
boundary_near_outside | 4.122e-05 | 5.124e-08 | 1.629e-03 | 4.122e-05
interior | 4.225e-05 | 4.332e-08 | 8.944e-04 | 4.225e-05
vertex_near_inside | 1.053e-04 | 1.680e-07 | 1.235e-03 | 1.053e-04

The residual-inclusive run evaluates

$$
\int G_{\mathrm{local},\sigma}(|x-y|)\rho(y)\,dy
$$

by the same ordinary folded quadrature. Its error is essentially the full-log
error, while the reconstructed error from `smooth + local` matches the direct
full-log error. This means the current direct local-residual quadrature has not
solved the near-field problem; it simply moves the difficult part into an
isolated compact term.

## Seed Comparison

fixture | seed mode | det ratio | edge-distance ratio
--- | --- | --- | ---
convex_quad | interior_anchor | 1.718e+00 | 1.510e+00
convex_quad | node_barycenter | 2.220e+00 | 1.550e+00
skew_quad | interior_anchor | 1.425e+00 | 1.474e+00
skew_quad | node_barycenter | 1.697e+00 | 1.264e+00

The node barycenter is viable on these convex fixtures but is not uniformly
better. It improves the edge-distance ratio on `skew_quad` but worsens the
boundary-determinant ratio on both fixtures. This supports treating the seed as
a measured quality parameter rather than replacing the robust interior anchor
yet.

## Interpretation

The split validates the preferred direction for the first experiment:

- Ordinary folded decomposition is effective for the smoothed kernel.
- Direct folded quadrature of the compact local residual is the new bottleneck;
  at `order=24`, local residual median relative error ranges from `4.2e-4` to
  `8.9e-3` depending on `sigma`, versus smooth-part median relative errors near
  `1e-7`.
- The singularity removal, not seed tuning, is the dominant improvement for the
  smooth path in these fixtures.
- Wider windows move more of the full interaction into the localized residual:
  median `|local/full|` grows from `1.3e-2` at `sigma=0.08` to `1.5e-1` at
  `sigma=0.32`.
- Boundary-near targets still benefit strongly in the smooth path, so the next
  question is not whether folded quadrature can handle the smooth remainder; it
  can. The remaining question is how to evaluate the localized residual with an
  analytic, asymptotic, or precomputed boundary-aware method.

## Analytic Full-Space Local Moment

A follow-up run tested the simplest analytic local residual estimator for
`G_{\mathrm{local},\sigma}`: replace the clipped local domain by the full plane
and use the leading Taylor moment

$$
u_{\mathrm{local},\sigma}(x)
\approx \frac{\sigma^2}{4}\rho(x).
$$

For the current polynomial test density, the isotropic Laplacian correction
vanishes, so this is the natural first full-space analytic estimate. It was used
unchanged for interior, boundary-near, exterior-near, and vertex-near targets.

At `order=24`, the analytic local relative errors were:

sigma | case set | analytic local rel err min | median | max | analytic reconstructed rel err median
--- | --- | ---: | ---: | ---: | ---:
0.08 | all | 2.594e-06 | 2.610e-01 | 4.969e+00 | 4.023e-03
0.08 | interior only | 2.594e-06 | 1.869e-04 | 6.371e-04 | 2.342e-06
0.08 | trim-near only | 1.892e-01 | 3.145e-01 | 4.969e+00 | 4.891e-03
0.16 | all | 2.446e-04 | 6.148e-01 | 2.378e+00 | 3.038e-02
0.16 | interior only | 2.446e-04 | 8.227e-04 | 1.466e-03 | 4.383e-05
0.16 | trim-near only | 4.213e-01 | 7.880e-01 | 2.378e+00 | 3.997e-02
0.32 | all | 5.745e-02 | 1.060e+00 | 1.623e+00 | 1.532e-01
0.32 | interior only | 5.745e-02 | 7.254e-02 | 8.766e-02 | 1.414e-02
0.32 | trim-near only | 6.560e-01 | 1.409e+00 | 1.623e+00 | 1.866e-01

By target class, over all tested `sigma` values and seeds:

Target class | analytic local rel err min | median | max | analytic reconstructed rel err median
--- | ---: | ---: | ---: | ---:
boundary_near_inside | 1.892e-01 | 4.799e-01 | 7.530e-01 | 2.186e-02
boundary_near_outside | 1.452e+00 | 2.141e+00 | 4.969e+00 | 5.235e-02
interior | 2.594e-06 | 9.924e-04 | 8.766e-02 | 4.383e-05
vertex_near_inside | 2.171e-01 | 7.880e-01 | 1.609e+00 | 3.997e-02

This confirms the expected split:

- Full-space analytic moments work for interior windows when `sigma` is small
  compared with distance to the physical boundary.
- The same full-space moments are not acceptable for trim-intersecting windows.
  They include outside-domain mass and can be worse than direct local quadrature.
- Larger `sigma` improves smooth-part quadrature but worsens the full-space local
  approximation unless the target is far from every trim boundary.

## Next Experiment

Add a local-residual method that separates two cases:

- interior support: use analytic Taylor/radial moments when the window is well
  separated from the physical boundary;
- boundary-intersecting support: build boundary-aware moments or a small
  precomputed folded-fan correction table.

The residual-inclusive and analytic-moment runs together indicate that direct
local folded quadrature is not competitive as the primary method, while
full-space analytic moments are only valid for interior windows. The next
implementation should therefore add a window/boundary classifier and route
interior windows to analytic moments, with trim-intersecting windows routed to a
boundary-aware correction experiment. The candidate local models and moment
expansions are catalogued in `docs/nearfield-local-model-catalogue.md`.
