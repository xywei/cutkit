# Near-Field Template Experiments

This note records the first mathematical check for issue 61: whether folded
decomposition charts can support a reusable near-field template story for later
box-code or Volumential work.

## Fan Map

For one straight-edge folded 2D piece, use the fan chart

```text
T(r, t) = (1-r) V + r C(t),
C(t) = (1-t) P0 + t P1,
0 <= r,t <= 1.
```

Its Jacobian is

```text
J(r, t) = r det(C(t)-V, C'(t)) = r det(P0-V, P1-V).
```

The factor `r` is the Duffy-style apex degeneracy already used by
`cutkit.quadrature.folded2d`. It is not a new singularity for physical
integration; it cancels area at the apex.

## Mapped Kernel

For the 2D Laplace kernel

```text
G(x, y) = -log(|x-y|)/(2*pi),
```

the point-target near-field integral is

```text
u(x) = integral_[0,1]^2 G(x, T_e(r,t)) rho(T_e(r,t)) J_e(r,t) dr dt.
```

This is the cheapest diagnostic path because it isolates source-piece mapping,
source density, and target location before introducing target basis functions.
For target pieces with a second map `T_f(eta)`, the bilinear template integral is

```text
A_fe = integral_[0,1]^2 integral_[0,1]^2
       psi_f(eta) G(T_f(eta), T_e(xi)) phi_e(xi)
       J_f(eta) J_e(xi) dxi deta.
```

For the self-piece case, this specializes to

```text
I = integral_[0,1]^2 integral_[0,1]^2
    G(T(r,t), T(r',t')) J(r,t) J(r',t') dr dt dr' dt'.
```

The experiment should classify interactions as:

- self piece, `e = f`;
- edge-adjacent pieces sharing a boundary segment;
- vertex or seed-adjacent pieces;
- near but disjoint pieces;
- well-separated pieces, where ordinary tensor-product quadrature should already work.

## Singular Split

Near a non-apex diagonal point `z=(r,t)`, write `delta = z' - z`. Then

```text
T(z + delta) - T(z) = DT(z) delta + O(|delta|^2),
|T(z + delta) - T(z)| = sqrt(delta^T M(z) delta) (1 + O(|delta|)),
M(z) = DT(z)^T DT(z).
```

Therefore

```text
G(T(z), T(z+delta))
= -log(sqrt(delta^T M(z) delta))/(2*pi) + smooth remainder.
```

The reusable part would be template-space singular model integrals or correction
operators. The runtime payload remains map coefficients, Jacobian data, source
coefficients, target metadata, and smooth-remainder moment/interpolation data.

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
or a low-rank basis in `M` and the smooth remainder, may cover enough practical
cut-piece cases to make reusable near-field corrections worthwhile.

The open numerical question is therefore whether the smooth dependence on `M`,
seed location, and curve coefficients is compact enough to approximate by such a
functional expansion for useful geometry families.

## Measurements

For each geometry and interaction case, record:

- reference value;
- ordinary pulled-forward tensor-product quadrature error;
- template singular-correction error;
- smooth-remainder approximation error;
- dependence on quadrature order;
- dependence on seed location and curve coefficients;
- size, rank, and smoothness of geometry-parameterized correction data;
- how many metric-field expansion modes are needed for the observed folded
  decomposition cases.

The first geometry family is CAD-independent: straight fan pieces, then
quadratic Bezier arcs and mildly curved cubics, with seed locations chosen to
produce positive, negative, and folded orientations. OpenCascade should only be
used later as a stress-test backend.

## Prototype

`cutkit.evals.nearfield_templates` implements:

- `FanTemplateMap2D` for the analytic fan map.
- `point_target_laplace_potential(...)` for point-target source integrals with
  polynomial template densities.
- `self_interaction_laplace(...)` for a direct high-order mapped self integral.
- `diagonal_remainder_sample(...)` for the metric singular split.
- `run_nearfield_template_experiment(...)` for the baseline feasibility check.

The script wrapper is:

```bash
uv run python scripts/run_nearfield_template_experiment.py --order 12
```

The experiment checks the exact scale law for the 2D log kernel. If the fan is
scaled by `lambda`, then

```text
I_lambda = lambda^4 (I - log(lambda) A^2/(2*pi)),
```

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
