# Near-Field Template Experiments

This note records the first mathematical check for issue 61: whether folded
decomposition charts can support a reusable near-field template story for later
box-code or Volumential work.

## Bezier Fan Chart

For the mathematical model, start with the chart type expected from CAD-backed
folded decomposition: a fan from a seed point `V` to a smooth Bezier trim curve
`C(t)`. A degree-`p` Bezier edge is

$$
\begin{aligned}
C(t) &= \sum_{a=0}^p B_a^p(t)P_a, \\
B_a^p(t) &= \binom{p}{a}(1-t)^{p-a}t^a,
\qquad 0\le t\le 1.
\end{aligned}
$$

The folded chart is

$$
\begin{aligned}
T(r,t) &= (1-r)V + rC(t),
\qquad 0\le r,t\le 1.
\end{aligned}
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

For a target point near the source chart, choose a template coordinate `z_x`
whose mapped source point `T(z_x)` is closest to `x`, or otherwise represents the
local source point responsible for the near-singular behavior. Write nearby
source coordinates as

$$
\begin{aligned}
\xi &= z_x + \delta, \\
d &= x - T(z_x).
\end{aligned}
$$

Here `delta` is the local source displacement away from the nearest source point,
and `d` is the physical target offset from that point. Instead of keeping only
the first metric term, use a high-order Taylor jet of the chart around `z_x`:

$$
\begin{aligned}
T(z_x+\delta)
&= T(z_x) + \sum_{1\le |\alpha|\le K} \\
&\quad \frac{1}{\alpha!}\partial^\alpha T(z_x)\delta^\alpha \\
&\quad + R_{K+1}(\delta).
\end{aligned}
$$

Define the order-`K` displacement polynomial

$$
\begin{aligned}
P_K(\delta;z_x,d)
&= d - \sum_{1\le |\alpha|\le K} \\
&\quad \frac{1}{\alpha!}\partial^\alpha T(z_x)\delta^\alpha.
\end{aligned}
$$

The singular model for the point-target kernel is then

$$
\begin{aligned}
G_K^{\mathrm{sing}}(x,z_x,\delta)
&= -\frac{1}{2\pi}\log |P_K(\delta;z_x,d)|.
\end{aligned}
$$

For an on-surface target, `d=0`. For an off-surface target, `d` carries the
normal and tangential target offset. Increasing `K` moves curvature and mixed
terms from the remainder into the singular model. If `C(t)` is a degree-`p`
Bezier curve, the fan map `T(r,t)=(1-r)V+rC(t)` is a polynomial of total degree
`p+1` in `(r,t)`, so the Taylor jet terminates once `K >= p+1`. For
rational/NURBS-derived charts, `K` is a truncation order chosen by the requested
accuracy.

The reusable part is a family of template-space singular model integrals or
correction operators parameterized by the finite jet data
$\{\partial^\alpha T(z_x)\}$ and the target offset `d`. The runtime payload remains
map coefficients, Jacobian data, source coefficients, target-node offsets, and
high-order correction or interpolation data.

## Metric-Field Expansion Tables

The table-building objective is to separate fixed singular template integrals
from per-chart smooth geometry and per-target offset coefficients. For a target
node represented by offset coordinates `tau`, use local source coordinates near
the closest chart point and write `xi = z_x + delta`. The high-order singular
distance model is

$$
|x-T(z_x+\delta)|^2 \approx |P_K(\delta;z_x,d)|^2.
$$

For `K=1` and an on-surface target, this reduces to the metric model

$$
\begin{aligned}
|P_1(\delta;z_x,0)|^2 &= \delta^T M(z_x)\delta, \\
M(z_x) &= DT(z_x)^TDT(z_x).
\end{aligned}
$$

The higher-order table strategy uses the full finite jet, not just `M(z_x)`. The
metric field remains the first term and a useful organizing parameter, but the
practical expansion variables are the coefficients of `P_K` plus the target
offset `d`.

Choose a reference jet, beginning with a positive-definite reference metric `M0`
and reference higher-order coefficients for one metric/curvature bin, chart
family, or local average. For the first metric term, write

$$
M(z) = M_0 + \Delta M(z).
$$

Then the metric contribution to the logarithmic singular factor can be expanded as

$$
\begin{aligned}
\log(\delta^T M(z)\delta)
&= \log(\delta^T M_0\delta) \\
&\quad + \log\left(1+\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right).
\end{aligned}
$$

If the metric family is binned or normalized so that

$$
\left|\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right| < 1,
$$

then

$$
\begin{aligned}
\log(\delta^T M(z)\delta)
&= \log(\delta^T M_0\delta) \\
&\quad + \sum_{k\ge 1}\frac{(-1)^{k+1}}{k}\left(\frac{\delta^T\Delta M(z)\delta}{\delta^T M_0\delta}\right)^k.
\end{aligned}
$$

The same expansion idea applies to the full high-order polynomial distance by
expanding the coefficients of `P_K` around the reference jet. Thus the kernel
singular part has the schematic expansion

$$
\begin{aligned}
G_K^{\mathrm{sing}}(x,z_x,\delta)
&\approx \sum_\alpha c_\alpha(z_x,\tau)S_\alpha(\delta;\mathcal J_0).
\end{aligned}
$$

where $\mathcal J_0$ denotes the selected reference jet. The fixed functions
`S_alpha` depend only on template displacement and the reference jet, while
`c_alpha(z_x,tau)` are smooth functions of metric entries, higher-order chart
derivatives, and target offset data. The expansion can be truncated by polynomial
order in the jet perturbation, by interpolation in jet/offset space, or by a
learned/empirical low-rank basis.

For one target node and one source density expansion mode `rho_j`, the singular
contribution becomes

$$
\begin{aligned}
u_j^{\mathrm{sing}}(\tau)
&\approx \sum_\alpha \int_{[0,1]^2} \\
&\quad \rho_j(\xi)c_\alpha(z_x,\tau) \\
&\quad \times S_\alpha(\xi-z_x;\mathcal J_0)J(\xi)\,d\xi.
\end{aligned}
$$

Expand the smooth per-chart/per-target factor in a template basis `p_beta`:

$$
c_\alpha(z_x,\tau)J(\xi) \approx \sum_\beta q_{\alpha\beta}(\tau)p_\beta(\xi).
$$

Then

$$
\begin{aligned}
u_j^{\mathrm{sing}}(\tau)
&\approx \sum_{\alpha,\beta}q_{\alpha\beta}(\tau)T_{j\alpha\beta}.
\end{aligned}
$$

$$
\begin{aligned}
T_{j\alpha\beta}
&= \int_{[0,1]^2} \\
&\quad \rho_j(\xi)p_\beta(\xi)S_\alpha(\xi-z_x;\mathcal J_0)\,d\xi.
\end{aligned}
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
\begin{aligned}
T_r &= C(t)-V, \\
T_t &= rC'(t).
\end{aligned}
$$

$$
M(r,t) =
\left[
\begin{matrix}
|C(t)-V|^2 & r(C(t)-V)\cdot C'(t) \\
r(C(t)-V)\cdot C'(t) & r^2|C'(t)|^2
\end{matrix}
\right].
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
\begin{aligned}
u_\lambda(\lambda x)
&= \lambda^2\left(u(x) - \frac{\log(\lambda)m_\rho}{2\pi}\right).
\end{aligned}
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
