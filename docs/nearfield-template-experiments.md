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
and `d` is the physical target offset from that point. The kernel depends on the
physical displacement from the source point to the target:

$$
x - T(\xi) = x - T(z_x+\delta).
$$

The purpose of the singular split is to approximate this displacement accurately
near `delta=0`, while keeping the approximation expressed on the fixed source
template. Instead of keeping only the first metric term, replace the chart by its
order-`K` Taylor jet around `z_x`:

$$
\begin{aligned}
T(z_x+\delta)
&= T(z_x) + \sum_{1\le |\alpha|\le K} \\
&\quad \frac{1}{\alpha!}\partial^\alpha T(z_x)\delta^\alpha \\
&\quad + R_{K+1}(\delta).
\end{aligned}
$$

Substituting this jet into `x - T(z_x+delta)` gives a polynomial approximation to
the target-to-source displacement. This is the critical object to tabulate
against:

$$
\begin{aligned}
P_K(\delta;z_x,d)
&= d - \sum_{1\le |\alpha|\le K} \\
&\quad \frac{1}{\alpha!}\partial^\alpha T(z_x)\delta^\alpha.
\end{aligned}
$$

Thus `P_K` is not an extra geometric map; it is the high-order local model of
the physical vector `x - T(xi)`. Its coefficients are exactly the chart jet at
`z_x` plus the target offset `d`.

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
from per-chart smooth geometry and per-target offset coefficients. The table is
not built from the metric term alone. It is built from the high-order
target-to-source displacement polynomial `P_K`.

For a target node represented by offset coordinates `tau`, write source points
near the closest chart point as `xi = z_x + delta`. The singular distance model is

$$
|x-T(z_x+\delta)|^2 \approx |P_K(\delta;z_x,d)|^2.
$$

The coefficients of `P_K` are the runtime geometry payload:

$$
\mathcal J_K(z_x,d)
= \left(d,\{\partial^\alpha T(z_x):1\le |\alpha|\le K\}\right).
$$

This includes both on-surface and off-surface targets. On-surface targets have
`d=0`; off-surface targets have nonzero `d`, which may include both normal and
tangential offset components. The metric field is only the first quadratic part
of this larger jet. In the special case `K=1` and `d=0`, the model reduces to

$$
\begin{aligned}
|P_1(\delta;z_x,0)|^2 &= \delta^T M(z_x)\delta, \\
M(z_x) &= DT(z_x)^TDT(z_x).
\end{aligned}
$$

That special case is useful for sanity checks, but it is not the intended table
construction. The practical table construction chooses a reference jet
$\mathcal J_0$ for a geometry/target-offset bin and expands the actual jet around
it:

$$
\mathcal J_K(z_x,d) = \mathcal J_0 + \Delta\mathcal J(z_x,d).
$$

Equivalently, write the displacement polynomial as a reference model plus a
smooth perturbation:

$$
\begin{aligned}
P_K(\delta;z_x,d)
&= P_K^0(\delta) + \Delta P_K(\delta;z_x,d).
\end{aligned}
$$

Then the log kernel can be expanded around the reference displacement:

$$
\begin{aligned}
\log |P_K(\delta;z_x,d)|
&= \log |P_K^0(\delta)| \\
&\quad + \frac{1}{2}\log\left(1+R_K(\delta;z_x,d)\right),
\end{aligned}
$$

where

$$
\begin{aligned}
R_K(\delta;z_x,d)
&= \frac{N_K(\delta;z_x,d)}{|P_K^0(\delta)|^2}, \\
N_K(\delta;z_x,d)
&= 2P_K^0(\delta)\cdot\Delta P_K(\delta;z_x,d) \\
&\quad + |\Delta P_K(\delta;z_x,d)|^2.
\end{aligned}
$$

When each bin is chosen so the perturbation ratio is controlled, this expression
can be expanded in powers, interpolation modes, or a low-rank basis in the jet
perturbation coefficients. The resulting singular model has the schematic form

$$
\begin{aligned}
G_K^{\mathrm{sing}}(x,z_x,\delta)
&\approx \sum_\alpha c_\alpha(z_x,\tau)S_\alpha(\delta;\mathcal J_0).
\end{aligned}
$$

Here `S_alpha` are fixed template functions for the selected reference jet, and
`c_alpha(z_x,tau)` are smooth functions of the target offset `d`, the metric
entries, and all higher-order chart derivatives included in `P_K`. For Bezier
fan charts, these jet coefficients are smooth functions of the seed point and
Bezier control points.

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

If the smooth per-chart/per-target factor is also expanded in a template basis
`p_beta`,

$$
\begin{aligned}
c_\alpha(z_x,\tau)J(\xi)
&\approx \sum_\beta q_{\alpha\beta}(\tau)p_\beta(\xi),
\end{aligned}
$$

then the runtime evaluation uses precomputed source-template tables:

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
jet/Jacobian fields, target offset data, and any higher-order correction or
remainder representation.

## Gaussian Window Split

A more controlled near-field experiment is to split the kernel before building
tables. Choose a length scale `sigma`, usually tied to the local box size or fan
diameter, and a smooth radial window `w_sigma(r)` that is near one at `r=0` and
rapidly decays to numerical zero for `r` larger than a few `sigma`. For the 2D
Laplace kernel, write

$$
\begin{aligned}
G(x,y) &= G_{\mathrm{sing},\sigma}(x,y) + G_{\mathrm{smooth},\sigma}(x,y), \\
G_{\mathrm{sing},\sigma}(x,y) &= w_\sigma(|x-y|)G(x,y), \\
G_{\mathrm{smooth},\sigma}(x,y) &= \left(1-w_\sigma(|x-y|)\right)G(x,y).
\end{aligned}
$$

The smooth part can be handled by ordinary folded-decomposition quadrature on
the source fan:

$$
\begin{aligned}
u_{\mathrm{smooth},\sigma}(x)
&= \int_{[0,1]^2}G_{\mathrm{smooth},\sigma}(x,T(\xi)) \\
&\quad \times \rho(T(\xi))J(\xi)\,d\xi.
\end{aligned}
$$

The singular-windowed part is numerically local:

$$
\begin{aligned}
u_{\mathrm{sing},\sigma}(x)
&= \int_{[0,1]^2}G_{\mathrm{sing},\sigma}(x,T(\xi)) \\
&\quad \times \rho(T(\xi))J(\xi)\,d\xi.
\end{aligned}
$$

Because `G_{sing,sigma}` is compactly supported to numerical tolerance, this
term matters only when the physical target point lies inside the fan piece or
within the chosen window radius of it. For target nodes in neighboring boxes that
are outside this support, the singular table contribution is skipped and the
ordinary folded quadrature of the smooth part is sufficient.

This changes the table problem substantially. The expensive singular table only
needs to cover a restricted local target set:

- target points on or inside the source fan;
- target points within a few `sigma` of the fan boundary;
- target offsets whose support intersects the fan under the high-order local
  displacement model `P_K`.

There is an additional simplification for targets inside the source cut region.
Folded decomposition does not require a fixed seed; for a point target `x` inside
the cut region, choose the decomposition anchor to be `x` itself and refold the
local source panel around that target. Each resulting fan has the form

$$
\begin{aligned}
T_x(r,t) &= (1-r)x + rC(t).
\end{aligned}
$$

The point singularity is then exactly at the Duffy apex `r=0`, and the Jacobian
contributes the usual factor `r`. For the logarithmic kernel, the local integrand
has the form

$$
\begin{aligned}
G(x,T_x(r,t))J_x(r,t)
&\sim -\frac{1}{2\pi}\log(r|C(t)-x|)\,r\,\det(C(t)-x,C'(t)),
\end{aligned}
$$

which is integrable in the Duffy coordinate. This means inside-target cases may
not need a general reference-jet table at all: they can use target-centered
folded/Duffy quadrature as the singular treatment. The remaining table problem is
then concentrated on targets just outside the fan, near boundaries, or otherwise
too close for the smooth quadrature but not eligible for target-centered
refolding.

The smooth remainder no longer needs singular quadrature or reference-jet tables;
it is evaluated directly with the same signed folded quadrature machinery used
for far-field source clouds. The open design choices are the window family, the
scale `sigma`, and the criterion used to skip the singular table for targets
outside the window support.

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
`P_a`. They are the first terms of the larger displacement-jet payload. The
mathematical reason precomputed template tables may apply is not that `M` alone
is universal, but that the full finite jet $\mathcal J_K$, the Jacobian, and the
target offset vary smoothly across the folded-decomposition chart family.

## Feasibility Result

The answer is more favorable with a Gaussian-window split. Singular or nearly
singular source-folded-piece to physical-point interactions can be moved to fixed
source template domains, and the tabled part can be restricted to targets inside
or very close to the fan piece. For targets inside the cut region, a
target-centered Duffy refolding may handle the singularity directly, reducing the
need for tabulation even further. The reusable object is still not a finite exact
table independent of geometry. It is a local family of reference-jet tables plus
interpolation, expansion, or low-rank coefficients for the runtime displacement
jet, focused on the near-boundary/outside cases that remain after the Duffy and
window-support tests.

The practical hypothesis is now about the compactness of the full point-target
payload, not only the metric field. For each near target, the relevant runtime
data is

$$
\mathcal J_K(z_x,d),\quad J(\xi),\quad \rho(\xi),\quad \tau,
$$

where $\mathcal J_K$ contains the target offset and all chart derivatives used by
`P_K`. Because Bezier fan maps have smooth, low-parameter structure away from
collapsed seed faces, these jet coefficients should vary smoothly across the
folded-decomposition cases produced by CAD-like trims. A functional expansion in
the jet data, target-offset data, and Jacobian/density factors may therefore
cover enough practical cases to make precomputed near-field tables worthwhile.
The Gaussian-window split improves the odds because the table does not need to
represent weakly near or well-separated target interactions; those move to the
smooth folded-quadrature path. Target-centered refolding improves the odds again
for interior targets because the singularity is placed at the Duffy apex instead
of being represented by a generic local jet table.

The open numerical question is whether the observed set of jets and target
offsets is compact or low-rank enough after binning by reference jet
$\mathcal J_0$.
If many bins or many expansion modes are required even after windowing, the
technique may not be worthwhile even though the template formulation is
mathematically valid.

## Measurements

For each geometry and interaction case, record:

- reference value;
- ordinary pulled-forward tensor-product quadrature error;
- template singular-correction error;
- Gaussian-window smooth-part quadrature error;
- higher-order correction/remainder approximation error;
- sensitivity to the window scale `sigma` and support cutoff;
- dependence on quadrature order;
- dependence on target offset, including on-surface, near-surface, containing-box,
  and neighbor-box target nodes;
- dependence on seed location and Bezier curve coefficients;
- size, rank, and smoothness of the reference-jet correction data;
- how many reference-jet bins and jet-expansion modes are needed for the observed
  folded-decomposition cases;
- whether metric-only organization is sufficient for any subfamily, or whether
  higher-order jet coefficients dominate the correction size.
- how often source-box and neighbor-box target nodes actually require the
  singular table after the window-support test.
- among supported targets, how many can use target-centered Duffy refolding
  instead of a reference-jet table.

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
- Near-field correction reuse should target a Gaussian-windowed point-target
  singular table for targets inside or very close to each fan piece. The smooth
  remainder should use ordinary folded-decomposition quadrature. Interior targets
  should first try target-centered Duffy refolding before falling back to tables.
- Volumential should still own tree/list composition; CUTKIT should export the
  local geometry/operator payloads needed by those lists.
