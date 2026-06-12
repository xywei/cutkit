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

This is the cheapest diagnostic path because it isolates source-piece mapping,
source density, and target location before introducing target basis functions.
For target pieces with a second map `T_f(eta)`, the bilinear template integral is

$$
A_{fe} = \int_{[0,1]^2}\int_{[0,1]^2}
\psi_f(\eta)G(T_f(\eta),T_e(\xi))\phi_e(\xi)
J_f(\eta)J_e(\xi)\,d\xi\,d\eta.
$$

For the self-piece case, this specializes to

$$
I = \int_{[0,1]^2}\int_{[0,1]^2}
G(T(r,t),T(r',t'))J(r,t)J(r',t')\,dr\,dt\,dr'\,dt'.
$$

The experiment should classify interactions as:

- self piece, `e = f`;
- edge-adjacent pieces sharing a boundary segment;
- vertex or seed-adjacent pieces;
- near but disjoint pieces;
- well-separated pieces, where ordinary tensor-product quadrature should already work.

## Singular Split

Near a non-apex diagonal point `z=(r,t)`, write `delta = z' - z`. Then

$$
T(z+\delta)-T(z) = DT(z)\delta + O(|\delta|^2),
$$

$$
|T(z+\delta)-T(z)| = \sqrt{\delta^T M(z)\delta}\,(1+O(|\delta|)),
\qquad M(z) = DT(z)^TDT(z).
$$

Therefore

$$
G(T(z),T(z+\delta))
= -\frac{1}{2\pi}\log\sqrt{\delta^T M(z)\delta}
+ \text{lower-order correction}.
$$

The reusable part would be template-space singular model integrals or correction
operators. The runtime payload remains map coefficients, Jacobian data, source
coefficients, target metadata, and correction moment/interpolation data. For a
Bezier fan map, `T(r,t)` is polynomial in `(r,t)` and contains mixed higher-order
terms from `rC(t)`. Subtracting only the local metric model leaves an
`O(|delta|)` correction whose first derivative at the diagonal can depend on
approach direction. A smooth-remainder expansion should therefore either include
higher-order distance terms in the singular model or treat this first prototype
as a leading singular split plus a bounded local correction.

## Metric-Field Expansion Tables

The table-building objective is to separate fixed singular template integrals
from per-chart smooth geometry coefficients. For a self or adjacent chart
interaction, use local source/target coordinates near the singular set and write
`z' = z + delta`. The singular distance model is

$$
|T(z')-T(z)|^2 = \delta^T M(z)\delta + \text{higher-order chart terms},
\qquad M(z)=DT(z)^TDT(z).
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
G_{\mathrm{sing}}(z,z+\delta)
\approx \sum_\alpha c_\alpha(z)S_\alpha(\delta;M_0),
$$

where `S_alpha` are fixed singular template functions for the selected reference
metric and `c_alpha(z)` are smooth functions of the entries of `Delta M(z)`.
The expansion can be truncated either by polynomial order in `Delta M`, by
interpolation in metric-entry space, or by a learned/empirical low-rank basis.
For full smooth-remainder tables near a chart diagonal, the singular model should
also include enough higher-order chart-distance terms to remove direction-
dependent local corrections.

For a bilinear self interaction with template basis functions `psi_i` and
`phi_j`, the singular contribution becomes

$$
A_{ij}^{\mathrm{sing}} \approx \sum_\alpha \int\!\int
\psi_i(z)\phi_j(z')c_\alpha(z)S_\alpha(z'-z;M_0)
J(z)J(z')\,dz'\,dz.
$$

Expand the smooth per-chart factor in a template basis `p_beta`:

$$
c_\alpha(z)J(z)J(z') \approx \sum_\beta q_{\alpha\beta}p_\beta(z,z').
$$

Then

$$
A_{ij}^{\mathrm{sing}} \approx
\sum_{\alpha,\beta}q_{\alpha\beta}T_{ij\alpha\beta},
$$

$$
T_{ij\alpha\beta} = \int\!\int
\psi_i(z)\phi_j(z')p_\beta(z,z')S_\alpha(z'-z;M_0)\,dz'\,dz.
$$

The tensors `T_{ij alpha beta}` are precomputed on fixed template domains. At
runtime, each folded chart only supplies the coefficients `q_{alpha beta}` from
its smooth metric/Jacobian fields and any higher-order correction or remainder
representation.

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
- `self_interaction_laplace(...)` for a direct high-order mapped self integral.
- `diagonal_remainder_sample(...)` for the metric singular split.
- `run_nearfield_template_experiment(...)` for the baseline feasibility check.

The script wrapper is:

```bash
uv run python scripts/run_nearfield_template_experiment.py --order 12
```

The current smoke-test experiment checks the exact scale law for the 2D log
kernel. If the fan is scaled by `lambda`, then

$$
I_\lambda = \lambda^4\left(I - \frac{\log(\lambda)A^2}{2\pi}\right),
$$

where `A` is the signed area of the unscaled fan piece. It also records diagonal
remainder samples that shrink as the source/target template coordinates coalesce
and a point-target low-order-vs-reference error.

## Next Decision

The idea is feasible as a CUTKIT experiment, with these limits:

- Far-field source clouds can remain ordinary signed quadrature sources.
- Near-field correction reuse should target template singular bases plus
  functional expansions in the smooth metric field `M(z)` and higher geometry
  terms.
- Volumential should still own tree/list composition; CUTKIT should export the
  local geometry/operator payloads needed by those lists.
