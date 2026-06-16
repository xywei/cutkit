# Near-Field Local Model Catalogue

This note catalogs the local analytic/asymptotic models for compact residual
kernels after a DMK/Ewald-style split. The guiding rule is:

> choose the residual support so each local correction sees at most one geometric
> singular feature.

If a residual window sees multiple unrelated trim arcs, corners, faces, or
vertices, it should be shrunk, the source geometry should be subdivided, or the
case should fall back to a precomputed/direct local correction.

## Common Expansion Form

Let the compact residual kernel be radial:

$$
K_\sigma(z) = K_{\mathrm{local},\sigma}(|z|),
\qquad z = y-x.
$$

The local residual contribution is

$$
u_{\mathrm{local},\sigma}(x)
= \int_{\Omega_x} K_\sigma(y-x)a(y)\,dy,
$$

where `a` denotes density times any smooth geometric/Jacobian factor and
`Omega_x` is the source region inside the effective residual support around the
target.

Choose a local model feature `F` and local coordinates `z`. Expand the smooth
amplitude at the target or closest feature point:

$$
a(x+z)
= \sum_{|\alpha|\le K}
\frac{1}{\alpha!}\partial^\alpha a(x)z^\alpha
+ R_{K+1}(z).
$$

Then

$$
u_{\mathrm{local},\sigma}(x)
= \sum_{|\alpha|\le K}
\frac{1}{\alpha!}\partial^\alpha a(x)
M_\alpha(F,\sigma)
+ \mathcal R_{K+1},
$$

with feature moments

$$
M_\alpha(F,\sigma)
= \int_{\Omega_F} K_\sigma(z)z^\alpha\,dz.
$$

For curved features, `Omega_F` is itself expanded around a leading flat, wedge,
or cone model. The resulting moments are products or perturbations of radial
moments and angular moments.

Equivalently, introduce the scaled coordinate

$$
z = \sigma q,
\qquad K_\sigma(z)=\sigma^{-s}k(|q|),
$$

where `s` is the kernel scaling power. Then

$$
M_\alpha(F,\sigma)
= \sigma^{d-s+|\alpha|}
\int_{\widehat\Omega_F} k(|q|)q^\alpha\,dq,
$$

up to corrections from finite support and curved geometry. For the 2D log
residual used here, `s = 0`, so the leading mass is `O(sigma^2)`. For 3D kernels
whose residuals scale like `sigma^{-1} k(r/sigma)`, the leading mass is also
`O(sigma^2)`; the exact power should be attached to the selected kernel split.

In a local modal implementation, write the smooth amplitude as

$$
a(x+z) \approx \sum_{\beta\in\mathcal B_K} c_\beta \phi_\beta(z),
$$

where the modal basis may be monomials, orthogonal polynomials on the local
feature model, or chart-jet modes. The correction is then

$$
u_{\mathrm{local},\sigma}(x)
\approx \sum_{\beta\in\mathcal B_K} c_\beta
\mu_\beta(F,\sigma),
\qquad
\mu_\beta(F,\sigma)=\int_{\Omega_F}K_\sigma(z)\phi_\beta(z)\,dz.
$$

The Taylor form below is the monomial version of this modal expansion.

## Feature Catalogue

| Dimension | Feature count in support | Leading model | Parameters |
| --- | --- | --- | --- |
| 2D | none | plane | target offset, amplitude jet |
| 2D | one smooth trim | half-plane | signed distance, tangent, curvature jet |
| 2D | one corner/junction | wedge | offset, opening angle, edge curvature jets |
| 3D | none | space | target offset, amplitude jet |
| 3D | one smooth face | half-space | signed distance, frame, principal curvature jet |
| 3D | one edge | dihedral wedge | offset, dihedral angle, face/edge jets |
| 3D | one vertex | polyhedral cone | offset, incident-face cone, edge/face jets |

The catalogue is complete for one geometric singularity because local CAD/cut
features stratify by codimension: interiors, smooth boundary strata, edges or
corners, and vertices. Multi-feature windows are deliberately excluded from one
model and must be split or handled by fallback.

## 2D Log Residual Moments

For the 2D log split used in the first experiments,

$$
K_\sigma(r)
= \frac{1}{4\pi}E_1(r^2/\sigma^2).
$$

Define radial moments

$$
R_m(\sigma)
= \int_0^\infty K_\sigma(r)r^{m+1}\,dr.
$$

Using

$$
\int_0^\infty u^q E_1(u)\,du = \frac{\Gamma(q+1)}{q+1},
$$

and `u = r^2/sigma^2`,

$$
R_m(\sigma)
= \frac{\sigma^{m+2}}{8\pi}
\frac{\Gamma\left(\frac{m}{2}+1\right)}{\frac{m}{2}+1}.
$$

In particular,

$$
2\pi R_0(\sigma) = \frac{\sigma^2}{4},
$$

which gives the leading full-plane estimate used in the experiments:

$$
u_{\mathrm{local},\sigma}(x)
\approx \frac{\sigma^2}{4}a(x).
$$

For finite support truncation at `r <= c sigma`, replace `R_m` by

$$
R_m(c,\sigma)
= \int_0^{c\sigma} K_\sigma(r)r^{m+1}\,dr.
$$

These truncated moments can be evaluated with recurrence/incomplete-gamma forms
or precomputed as one-dimensional functions of `c`.

## 2D Local Models

### Interior Model

Condition: the residual support lies inside the source region and away from all
trim features.

Model domain:

$$
\Omega_F = \mathbb R^2.
$$

The moments are full angular moments:

$$
M_{ij}^{\mathrm{int}}
= \int_0^{2\pi}\int_0^\infty
K_\sigma(r)(r\cos\theta)^i(r\sin\theta)^j r\,dr\,d\theta.
$$

Odd moments vanish by symmetry. The first terms are

$$
\begin{aligned}
u_{\mathrm{int}}(x)
&= 2\pi R_0 a(x)
+ \frac{1}{2}\left(\partial_{xx}a+\partial_{yy}a\right)
\pi R_2 + O(\sigma^6) \\
&= \frac{\sigma^2}{4}a(x)
+ \frac{\sigma^4}{32}\Delta a(x)
+ O(\sigma^6)
\end{aligned}
$$

for the 2D log residual.

### Smooth Boundary Model

Condition: the residual support intersects one smooth trim segment and no corner.

Use local tangent-normal coordinates at the closest trim point `p`:

$$
z = \tau t + \eta n,
\qquad x-p = d_t\tau + d_n n.
$$

For a flat leading model with the source on `eta >= -d_n`, use target-centered
coordinates

$$
z = s(\cos\theta,\sin\theta),
$$

with angular/radial domain

$$
s\sin\theta \ge -d_n.
$$

Equivalently, along a ray `theta`, the lower radial limit is

$$
s_0(\theta;d_n)=
\begin{cases}
0, & \sin\theta \ge 0, \\
\frac{-d_n}{\sin\theta}, & \sin\theta < 0,
\end{cases}
$$

for an interior target with `d_n >= 0`. Exterior targets reverse which angular
sector contributes. The moments are

$$
M_{ij}^{\mathrm{half}}(d_n,\sigma)
= \int_{\Theta(d_n)}
\int_{s_0(\theta)}^\infty
K_\sigma(s)(s\cos\theta)^i(s\sin\theta)^j s\,ds\,d\theta.
$$

For `d_n = 0`, this reduces to half-plane moments. The leading term is one half
of the full-plane mass:

$$
u_{\mathrm{half}}(x)
\approx \frac{\sigma^2}{8}a(x)
$$

when the target is exactly on a straight boundary.

For curved trims, express the boundary as a graph in tangent-normal coordinates:

$$
\eta = h(\tau)
= \frac{\kappa}{2}\tau^2
+ \frac{h_3}{6}\tau^3
+ \cdots.
$$

The source condition becomes

$$
d_n + s\sin\theta
\ge h(d_t+s\cos\theta).
$$

Expand the boundary perturbation around the flat model. This produces curvature
corrections of the schematic form

$$
M_\alpha^{\mathrm{bdry}}
= M_\alpha^{\mathrm{half}}
+ \kappa C_{\alpha,1}(d/\sigma)\sigma^{|\alpha|+3}
+ h_3 C_{\alpha,2}(d/\sigma)\sigma^{|\alpha|+4}
+ \cdots.
$$

The functions `C` are universal coefficient maps in normalized target offset and
can be tabulated.

### Corner Model

Condition: the residual support intersects one polygon corner or one trim
junction, and no other geometric singular feature.

The leading model is a wedge with opening angle `omega`:

$$
\Omega_F = \{(r,\theta): r\ge 0,
\theta_0\le \theta\le \theta_1\},
\qquad \omega = \theta_1-\theta_0.
$$

For a target at the corner, moments are separable:

$$
M_{ij}^{\mathrm{wedge}}
= R_{i+j}(\sigma)
\int_{\theta_0}^{\theta_1}
(\cos\theta)^i(\sin\theta)^j\,d\theta.
$$

The leading mass term is

$$
u_{\mathrm{wedge}}(x)
\approx \frac{\omega}{2\pi}\frac{\sigma^2}{4}a(x).
$$

For a target offset from the corner, rays have angle-dependent entry and exit
limits from the two boundary rays. The same formula applies with radial limits
`s_0(theta), s_1(theta)`. Curved edges meeting at the corner introduce two graph
perturbations and a corner-angle perturbation series.

## 3D Local Models

The same taxonomy applies in 3D. Let

$$
z = r\omega,
\qquad \omega\in S^2.
$$

Define radial moments

$$
R_m^{3D}(\sigma)
= \int_0^\infty K_\sigma(r)r^{m+2}\,dr.
$$

Then feature moments are radial moments times angular moments over subsets of
the sphere, plus curvature corrections.

### Interior Model

Condition: support lies inside the source volume and away from faces, edges, and
vertices.

Model domain:

$$
\Omega_F = \mathbb R^3.
$$

Moments are

$$
M_\alpha^{\mathrm{int},3D}
= R_{|\alpha|}^{3D}(\sigma)
\int_{S^2}\omega^\alpha\,d\omega.
$$

Odd moments vanish. The first correction is proportional to the Laplacian of the
amplitude.

### Smooth Face Model

Condition: support intersects one smooth boundary face and no edge.

Use local coordinates `(u,v,n)` at the closest face point. The flat leading model
is a half-space:

$$
n \ge -d_n.
$$

Moments are spherical cap moments:

$$
M_\alpha^{\mathrm{face}}
= \int_{S^2}\int_{s_0(\omega)}^\infty
K_\sigma(s)(s\omega)^\alpha s^2\,ds\,d\omega.
$$

For a target exactly on a flat face, the leading mass term is half of the
full-space mass. Curvature corrections use the face graph

$$
n = h(u,v)
= \frac{1}{2}(\kappa_1 u^2 + \kappa_2 v^2)
+ \cdots.
$$

The coefficient maps depend on normalized offset `d/sigma` and the principal
curvatures scaled by `sigma`.

### Edge Model

Condition: support intersects one edge where two faces meet and no vertex.

The leading model is a dihedral wedge extruded along the edge tangent. In local
cylindrical coordinates around the edge,

$$
z = z_e e + r(\cos\theta n_1 + \sin\theta n_2),
\qquad \theta_0\le\theta\le\theta_1.
$$

Equivalently, the angular domain on `S^2` is a lune determined by the two face
planes. Moments are

$$
M_\alpha^{\mathrm{edge}}
= \int_{\Omega_{\mathrm{dihedral}}}
K_\sigma(|z|)z^\alpha\,dz.
$$

For a target on a straight edge, the leading mass is the solid-angle fraction of
the full-space mass:

$$
u_{\mathrm{edge}}(x)
\approx \frac{\Omega_{\mathrm{edge}}}{4\pi}M_0^{\mathrm{full}}a(x),
$$

where `Omega_edge` is the solid angle of the dihedral wedge. Higher terms depend
on angular monomial moments of the spherical lune. Curved faces and curved edge
tangents add perturbation terms from the two surface graphs and the edge curve.

### Vertex Model

Condition: support intersects one vertex and no other independent feature.

The leading model is a polyhedral cone:

$$
\Omega_F = \{r\omega: r\ge 0,
\omega\in A\subset S^2\}.
$$

Moments are

$$
M_\alpha^{\mathrm{vertex}}
= R_{|\alpha|}^{3D}(\sigma)
\int_A \omega^\alpha\,d\omega.
$$

The leading mass term is again the solid-angle fraction of the full-space mass:

$$
u_{\mathrm{vertex}}(x)
\approx \frac{|A|}{4\pi}M_0^{\mathrm{full}}a(x).
$$

For curved CAD vertices, the cone receives perturbations from all incident face
charts and edge curves. These are likely table-driven rather than hand-derived in
early experiments.

## Routing Rules

Each residual correction should be routed by the local feature set inside the
effective support radius `R_sigma = c sigma`:

1. No physical feature in support: use interior moments.
2. Exactly one smooth boundary face or trim segment: use smooth-boundary moments.
3. Exactly one corner in 2D or edge in 3D: use wedge or dihedral moments.
4. Exactly one vertex in 3D: use cone moments.
5. More than one feature or ambiguous classification: shrink `sigma`, subdivide
   the source region, or use a direct/precomputed local fallback.

The normalized parameters for reusable tables are:

- normalized target offset `d/sigma`;
- opening angle or solid-angle data for wedges/cones;
- curvature coefficients scaled by powers of `sigma`;
- amplitude and Jacobian jets;
- chart orientation and sign.

## Complement-Subtraction Route

For cut boxes with an ambient tensor-product density representation, a useful
alternative to direct boundary-aware singular moments is to subtract the outside
of-domain complement from an existing full-box singular table. For a box `B`,
physical region `Omega_B = Omega cap B`, source mode `p_alpha`, and target `x`,

$$
\int_{\Omega_B} K(x,y)p_\alpha(y)\,dy
= \int_B K(x,y)p_\alpha(y)\,dy
- \int_{B\setminus\Omega}K(x,y)p_\alpha(y)\,dy.
$$

The first term is the standard interior-box moment. The complement term can be
evaluated by folded decomposition as an ordinary smooth integral if

$$
\operatorname{dist}(x, B\setminus\Omega) > 0.
$$

This condition holds for targets strictly inside the cut cell with a positive
distance to the cut boundary. It fails, or becomes numerically fragile, when the
target lies on the physical boundary, when the complement closure contains the
target, or when the target-complement distance is small relative to the requested
accuracy and quadrature order.

For the small-distance case, the preferred fix is a QBX-style expansion of the
complement potential rather than direct high-resolution quadrature at the target.
Although the integrand `K(x,y)` is nearly singular when `x` approaches the cut
boundary, the complement potential is smooth on the physical side away from the
complement sources. Choose an expansion center `c` in `Omega_B` and a radius `r`
such that

$$
|x-c| < r < \operatorname{dist}(c, B\setminus\Omega).
$$

Then compute local expansion coefficients for

$$
u_{\mathrm{comp}}(x)=\int_{B\setminus\Omega}K(x,y)p_\alpha(y)\,dy
$$

by folded quadrature over the complement with target/center `c`, where the
coefficient integrands are smooth. The expansion is then evaluated at the actual
near-boundary target `x` and subtracted from the full-box singular moment.

This is a volume-potential analogue of QBX: the expansion is not used to represent
the singular self term on `Omega_B`; that part is already in the full-box table.
It is used only to avoid nearly singular evaluation of the smooth complement
field near the boundary.

Routing for this route is:

1. If the target is target-separated from the complement, use full-box table minus
   folded complement.
2. If the target is close to the complement boundary but covered by a safe
   expansion ball, use full-box table minus complement-QBX evaluation.
3. If no safe complement expansion center exists and the target lies on one
   smooth boundary feature, use smooth-boundary moments or a boundary table.
4. If the target lies on an edge, corner, or vertex, route to the corresponding
   wedge/cone model or refine.
5. If multiple complement pieces approach the target, shrink the box/window,
   subdivide the geometry, or use a target-centered fallback.

The complement folded quadrature should use open quadrature rules on fan or cone
coordinates. Lobatto endpoint nodes are useful for interpolation and element
interfaces, but they are undesirable for this smooth-complement integral because a
fan endpoint, clipped-boundary endpoint, or coning apex may lie on the target or
on a nearly singular geometric feature. Open rules keep all quadrature nodes in
the smooth interior of each complement piece.

This route is attractive for List 1 matrix generation because the singular part
is geometry independent and can reuse the same full-box tables as uncut boxes.
The geometry-dependent object is the complement moment matrix, which is smooth
under the separation condition and can be built by folded quadrature, by
QBX-style local expansion coefficients, or compressed over cut-geometry
parameters.

## Precomputed Smooth-Boundary Moment Scheme

For a target on or near one smooth boundary feature, introduce local
tangent-normal coordinates at the closest boundary point:

$$
y = x + s\tau + n\nu,
$$

where `tau` is tangent and `nu` is the inward normal. The flat model is the
half-plane `n >= 0`. The curved boundary is represented as a local graph

$$
n = h(s)
= c_2 s^2 + c_3 s^3 + c_4 s^4 + \cdots.
$$

The local source domain is

$$
n \ge h(s).
$$

For a compact residual kernel `K_sigma`, the local correction is

$$
I_\sigma
= \int_{n\ge h(s)} K_\sigma(s,n)a(s,n)\,ds\,dn,
$$

where `a` is density times Jacobian and any smooth chart factor. Rewrite this as
a flat half-plane moment minus the curved strip excluded by the boundary:

$$
I_\sigma
= \int_{n\ge 0} K_\sigma(s,n)a(s,n)\,ds\,dn
- \int_{0\le n\le h(s)}K_\sigma(s,n)a(s,n)\,ds\,dn.
$$

This identity is the conceptual split. The final implementation should not do a
naive online tensor quadrature over the strip; the logarithmic endpoint at the
target makes that too slow for machine precision. Instead, normalize by the
residual scale:

$$
s = \sigma q,
\qquad n = \sigma p.
$$

Then the scaled boundary is

$$
p = H(q;\lambda)
= \lambda_2 q^2 + \lambda_3 q^3 + \lambda_4 q^4 + \cdots,
$$

with normalized geometry coefficients

$$
\lambda_m = c_m\sigma^{m-1}.
$$

For the 2D log residual, `K_sigma(s,n) = k(q,p)` after scaling, and

$$
I_\sigma
= \sigma^2
\int_{p\ge H(q;\lambda)} k(q,p)
a(x+\sigma(q\tau+p\nu))\,dq\,dp.
$$

Expand the smooth amplitude in the same local coordinates:

$$
a(x+\sigma(q\tau+p\nu))
= \sum_{i+j\le A} a_{ij}\sigma^{i+j}q^i p^j
+ O(\sigma^{A+1}).
$$

The correction becomes a finite contraction:

$$
I_\sigma
\approx
\sum_{i+j\le A}a_{ij}\sigma^{2+i+j}
M_{ij}(\lambda),
$$

where the normalized smooth-boundary moments are

$$
M_{ij}(\lambda)
= \int_{p\ge H(q;\lambda)} k(q,p)q^i p^j\,dq\,dp.
$$

These `M_ij(lambda)` are the reusable objects. They can be represented in either
of two equivalent ways:

1. tabulate `M_ij(lambda)` over normalized boundary-jet parameters and
   interpolate;
2. expand the moment function itself in geometry parameters:

$$
M_{ij}(\lambda)
= M_{ij}^{\mathrm{half}}
+ \lambda_2 M_{ij}^{(2)}
+ \lambda_3 M_{ij}^{(3)}
+ \lambda_2^2 M_{ij}^{(22)}
+ \cdots.
$$

The current prototype tests the first representation on a rational quarter-circle
trim. Seven precomputed samples in the normalized scale interpolate intermediate
smooth-boundary moment values below `1e-10` relative error.

### Offline Table Generation

For each kernel split, expansion order, and model family:

1. choose a normalized parameter box for `lambda`;
2. choose a monomial or modal basis `q^i p^j` up to amplitude order `A`;
3. for each table node in `lambda`, evaluate `M_ij(lambda)` using a robust
   high-order method such as exact ray clipping and finite radial moments;
4. store interpolation coefficients or a compressed modal representation;
5. validate the table against direct high-order local references on curved CAD
   fixtures.

The expensive ray-exit solves belong in this offline generation step, not in the
main runtime path.

### Runtime Evaluation

For each target/source local residual interaction:

1. classify the support as interior, one smooth boundary, corner/wedge, or
   fallback;
2. if smooth-boundary, find the closest local boundary point and frame
   `(tau, nu)`;
3. compute the scaled boundary coefficients `lambda_m = c_m sigma^(m-1)`;
4. compute the amplitude jet coefficients `a_ij` for density, Jacobian, and chart
   factors;
5. interpolate or evaluate the precomputed moments `M_ij(lambda)`;
6. return the contraction

$$
\sum_{i+j\le A}a_{ij}\sigma^{2+i+j}M_{ij}(\lambda).
$$

For higher dimensions, the same idea applies with local coordinates split into
tangential variables and one normal variable. Smooth faces use graph moments;
edges use wedge/dihedral graph moments; vertices use cone-sector moments.

## Experiment Order

The recommended implementation sequence is:

1. 2D interior full-space moments. Done for the leading term.
2. 2D straight-boundary half-plane moments.
3. 2D polygon-corner wedge moments.
4. 2D curved-boundary perturbations.
5. 3D face half-space moments.
6. 3D edge dihedral moments.
7. 3D vertex cone moments.

At each stage, compare the analytic model against the high-order local residual
reference and only add precomputed tables where closed-form or low-dimensional
moment evaluation is not sufficient.

## Implemented Checks

The first executable checks cover straight-feature 2D moments for the log Ewald
residual:

- full-plane mass and second moments;
- boundary-point half-plane sector moments;
- corner-point wedge sector moments.

The implementation exposes the radial moment and angular-sector monomial moment
helpers in `cutkit.evals.nearfield_templates`. Tests compare closed-form sector
moments against direct polar quadrature of the local residual kernel.

A second practical check uses an exact rational quadratic quarter-circle cut cell
with one curved trim and two straight cell faces. For targets on the smooth curved
trim and `sigma = 0.02, 0.04`, the leading flat half-plane local model is only a
zeroth-order diagnostic: it is percent-level accurate, while the full-plane model
is worse than `100%` relative error because it includes outside-domain mass.

The production-quality boundary-aware model must include the local curved
geometry. For the same rational curved cut cell, the implemented target-centered
model clips each ray against the exact curved cell and evaluates the radial Ewald
moments analytically along each ray. The remaining angular integral is adaptively
resolved, and the test requires refinement agreement below `1e-10` relative
error. This is the practical conclusion: flat half-plane moments are useful for
routing and leading-order estimates, but machine precision requires exact or
high-order curved boundary geometry plus finite radial moments.

The first high-order boundary-model experiment confirms this route on the same
smooth rational trim. The local circular boundary is replaced by an order-`K`
Taylor graph in tangent-normal coordinates. Along each target-centered ray, the
model solves for the positive graph exit distance and uses finite radial Ewald
moments. For `sigma = 0.02`, the relative error against the exact circular
boundary model decreases from `O(1e-6)` at quadratic order to `O(1e-11)` at order
6 and below `1e-10` at order 8. For smaller windows `sigma = 0.005, 0.01`, order
6 is already below `1e-10` relative error.

The first precomputation-style check tabulates the high-order smooth-boundary
moment value as a function of the normalized local boundary scale. Seven table
samples over `sigma = 0.004..0.028` interpolate intermediate samples at
`sigma = 0.010, 0.018, 0.026` with maximum relative error below `1e-10`. This is
not yet the final modal table format, but it shows that the online ray solve can
move into an offline/table-generation phase. A direct tensor graph-strip
quadrature was also tested and is not sufficient for machine precision near the
target logarithmic endpoint; the precomputed object should be a normalized moment
or coefficient table, not a naive online strip quadrature.
