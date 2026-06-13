# Near-Field Template Experiments

This note records the first mathematical check for issue 61: whether folded
decomposition charts can support a reusable near-field template story for later
box-code or Volumential work.

## Bezier Fan Chart

For the mathematical model, start with the chart type expected from CAD-backed
folded decomposition: a fan from a seed point `V` to a smooth Bezier trim curve
`C(t)`. A degree-`p` Bezier edge is

$$
C(t) = \sum_{a=0}^p B_a^p(t)P_a,
\qquad B_a^p(t)=\binom{p}{a}(1-t)^{p-a}t^a,
\qquad 0\le t\le 1.
$$

The folded chart is

$$
T(r,t) = (1-r)V + rC(t),
\qquad 0\le r,t\le 1.
$$

Its Jacobian is

$$
J(r,t) = r\det(C(t)-V,C'(t)).
$$

The factor `r` is the Duffy-style apex degeneracy already used by
`cutkit.quadrature.folded2d`. It is not a new singularity for physical
integration; it cancels area at the apex. The straight-edge case is only the
degree-1 specialization and should be treated as a smoke-test fixture, not as
the primary derivation.

## Mapped Kernel

For the 2D Laplace kernel

$$
G(x,y) = -\frac{1}{2\pi}\log |x-y|,
$$

the point-target near-field integral is

$$
u(x) = \int_{[0,1]^2} G(x,T_e(r,t))\rho(T_e(r,t))J_e(r,t)\,dr\,dt.
$$

This is the primary target model for the box-code experiment. The source is a
folded piece, but targets are physical-space discretization nodes in the source
box and neighboring near-field boxes. There is no target folded piece in the
first near-field experiment.

For reusable tables, express the target relative to the same physical box or
chart payload. If `x0` is a chart/box reference point and `H` is a box-scale map,
write

$$
x = x_0 + H\tau,
$$

where `tau` is the template-space location of a target node in the containing or
neighboring box. The source-to-point integral is then a fixed-domain integral in
the source chart coordinates and the target offset parameter `tau`:

$$
u(\tau) = \int_{[0,1]^2}G(x_0+H\tau,T_e(\xi))\rho(T_e(\xi))J_e(\xi)\,d\xi.
$$

The experiment should classify target/source geometry as:

- target node on or very near the source folded piece;
- target node in the source piece's containing box;
- target node in an edge-neighboring box;
- target node in a vertex-neighboring box;
- well-separated target node, where ordinary tensor-product quadrature should already work.

## Point-Target Singular Split

For a target point near the source chart, let `z_x` be a closest or projected
template coordinate with `T(z_x)` near `x`, and write `xi = z_x + delta`. Then

$$
T(z_x+\delta)-T(z_x) = DT(z_x)\delta + O(|\delta|^2),
$$

$$
|T(z_x+\delta)-T(z_x)| =
\sqrt{\delta^T M(z_x)\delta}\,(1+O(|\delta|)),
\qquad M(z_x) = DT(z_x)^TDT(z_x).
$$

For an on-surface or asymptotically close target, this gives the leading model

$$
G(x,T(z_x+\delta))
= -\frac{1}{2\pi}\log\sqrt{\delta^T M(z_x)\delta}
+ \text{lower-order correction}.
$$

For an off-surface target, include the normal/offset residual `d = x-T(z_x)`:

$$
|x-T(z_x+\delta)|^2
= |d-DT(z_x)\delta|^2 + \text{higher-order chart terms}.
$$

The reusable part would be template-space singular model integrals or correction
operators. The runtime payload remains map coefficients, Jacobian data, source
coefficients, target-node offsets, and correction moment/interpolation data. For
a Bezier fan map, `T(r,t)` is polynomial in `(r,t)` and contains mixed
higher-order terms from `rC(t)`. Subtracting only the local metric model leaves
an `O(|delta|)` correction whose first derivative at the singular point can
depend on approach direction. A smooth-remainder expansion should therefore
either include higher-order distance terms in the singular model or treat this
first prototype as a leading singular split plus a bounded local correction.

## Metric-Field Expansion Tables

The table-building objective is to separate fixed singular template integrals
from per-chart smooth geometry and per-target offset coefficients. For a target
node represented by offset coordinates `tau`, use local source coordinates near
the closest chart point and write `xi = z_x + delta`. The on-surface singular
distance model is

$$
|T(z_x+\delta)-T(z_x)|^2
= \delta^T M(z_x)\delta + \text{higher-order chart terms},
\qquad M(z_x)=DT(z_x)^TDT(z_x).
$$

Choose a positive-definite reference metric `M0` for one metric bin, chart
family, or local average, and write

$$
M(z) = M_0 + \Delta M(z).
$$

Then the logarithmic singular factor can be expanded as

$$
\log(\delta^T M(z)\delta)
= \log(\delta^T M_0\delta)
+ \log\left(1+
\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right).
$$

If the metric family is binned or normalized so that

$$
\left|\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right| < 1,
$$

then

$$
\log(\delta^T M(z)\delta)
= \log(\delta^T M_0\delta)
+ \sum_{k\ge 1}\frac{(-1)^{k+1}}{k}
\left(\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right)^k.
$$

Thus the kernel singular part has the schematic expansion

$$
G_{\mathrm{sing}}(x,T(z_x+\delta))
\approx \sum_\alpha c_\alpha(z_x,\tau)S_\alpha(\delta;M_0),
$$

where `S_alpha` are fixed singular template functions for the selected reference
metric and `c_alpha(z_x,tau)` are smooth functions of the entries of
`Delta M(z_x)` and the target offset data. The expansion can be truncated either
by polynomial order in `Delta M`, by interpolation in metric/offset space, or by
a learned/empirical low-rank basis.
For full smooth-remainder tables near a chart diagonal, the singular model should
also include enough higher-order chart-distance terms to remove direction-
dependent local corrections.

For one target node and one source density expansion mode `rho_j`, the singular
contribution becomes

$$
u_j^{\mathrm{sing}}(\tau) \approx \sum_\alpha \int_{[0,1]^2}
\rho_j(\xi)c_\alpha(z_x,\tau)S_\alpha(\xi-z_x;M_0)J(\xi)\,d\xi.
$$

Expand the smooth per-chart/per-target factor in a template basis `p_beta`:

$$
c_\alpha(z_x,\tau)J(\xi) \approx \sum_\beta q_{\alpha\beta}(\tau)p_\beta(\xi).
$$

Then

$$
u_j^{\mathrm{sing}}(\tau) \approx
\sum_{\alpha,\beta}q_{\alpha\beta}(\tau)T_{j\alpha\beta},
$$

$$
T_{j\alpha\beta} = \int_{[0,1]^2}
\rho_j(\xi)p_\beta(\xi)S_\alpha(\xi-z_x;M_0)\,d\xi.
$$

The tensors `T_{j alpha beta}` are precomputed on fixed source template domains,
or tabulated over a small target-offset grid. At runtime, each folded chart and
target node only supply the coefficients `q_{alpha beta}(tau)` from smooth
metric/Jacobian fields, target offset data, and any higher-order correction or
remainder representation.

For the Bezier fan map

$$
T(r,t) = (1-r)V + rC(t),
$$

the metric entries are explicit:

$$
T_r = C(t)-V,
\qquad T_t = rC'(t),
$$

$$
M(r,t) =
\begin{bmatrix}
|C(t)-V|^2 & r(C(t)-V)\cdot C'(t) \\
r(C(t)-V)\cdot C'(t) & r^2|C'(t)|^2
\end{bmatrix}.
$$

For Bezier or piecewise-Bezier CAD trims, these entries are smooth
low-parameter functions of `(r,t)`, the seed `V`, and the Bezier control points
`P_a`. This is the mathematical reason precomputed template tables can apply to
each chart piece: the singular table is fixed after choosing `M0`, while
observed folded-decomposition geometry should enter through a small smooth
expansion of `M`, `J`, and the higher-order correction data.

## Feasibility Result

The answer is qualified yes. Singular or nearly singular folded-piece
interactions can be moved to fixed template domains, but not to a finite exact
table independent of geometry. The singular coordinate form is reusable; the
metric and higher-order geometry terms enter through smooth geometry-dependent
payloads.

The practical hypothesis is stronger than carrying `M(z)` pointwise at runtime:
because the folded maps have smooth, low-parameter structure away from collapsed
seed faces, the metric field `M(z)` should vary smoothly over the template and
across the geometry families produced by folded decomposition. A functional
expansion in the metric data, for example moments, interpolation coefficients,
or a low-rank basis in `M` and the correction terms, may cover enough practical
cut-piece cases to make reusable near-field corrections worthwhile.

The open numerical question is therefore whether the smooth dependence on `M`,
seed location, and curve coefficients is compact enough to approximate by such a
functional expansion for useful geometry families.

## Measurements

For each geometry and interaction case, record:

- reference value;
- ordinary pulled-forward tensor-product quadrature error;
- template singular-correction error;
- higher-order correction/remainder approximation error;
- dependence on quadrature order;
- dependence on seed location and curve coefficients;
- size, rank, and smoothness of geometry-parameterized correction data;
- how many metric-field expansion modes are needed for the observed folded
  decomposition cases.

The first geometry family should be CAD-independent but CAD-realistic: quadratic
and cubic Bezier fan charts with seed locations chosen to produce positive,
negative, and folded orientations. Straight fan pieces are useful only as
low-level smoke tests. OpenCascade should be used later as a source of
stress-test Bezier/NURBS-derived fixtures, not as a dependency of the numerical
question.

## Prototype

`cutkit.evals.nearfield_templates` implements:

- `FanTemplateMap2D` for the current straight-edge smoke-test fan map.
- `point_target_laplace_potential(...)` for point-target source integrals with
  polynomial template densities.
- `diagonal_remainder_sample(...)` for the metric singular split.
- `run_nearfield_template_experiment(...)` for the baseline feasibility check.

The script wrapper is:

```bash
uv run python scripts/run_nearfield_template_experiment.py --order 12
```

The current smoke-test experiment checks the exact scale law for the 2D log
kernel. If both the source fan and physical target point are scaled by `lambda`,
then

$$
u_\lambda(\lambda x)
= \lambda^2\left(u(x) - \frac{\log(\lambda)m_\rho}{2\pi}\right),
$$

where `m_rho` is the density-weighted signed source mass on the unscaled fan
piece. It also records diagonal remainder samples that shrink as the source and
target template coordinates coalesce and a point-target low-order-vs-reference
error.

## Next Decision

The idea is feasible as a CUTKIT experiment, with these limits:

- Far-field source clouds can remain ordinary signed quadrature sources.
- Near-field correction reuse should target template singular bases plus
  functional expansions in the smooth metric field `M(z)` and higher geometry
  terms.
- Volumential should still own tree/list composition; CUTKIT should export the
  local geometry/operator payloads needed by those lists.
