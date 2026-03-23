## Context

CUTKIT currently demonstrates folded integration accuracy via Section 6 protocols, but it does not yet include application-level Poisson workflows from the paper. Without these benchmarks, we cannot verify end-to-end solver impact or guard against regressions in application contexts.

## Goals / Non-Goals

**Goals:**
- Add reproducible Poisson benchmark workflows for trimmed planar and trimmed volume cases.
- Ensure benchmarks consume CUTKIT folded quadrature through explicit interfaces.
- Report deterministic error and convergence metrics suitable for regression testing.
- Keep benchmark configuration simple enough for CI and local smoke coverage.

**Non-Goals:**
- Build a full-featured general-purpose PDE framework in this change.
- Optimize benchmark performance for production throughput.
- Cover every geometry family from external CAD repositories.

## Decisions

1. Implement benchmark runners as dedicated eval modules with clear input/output contracts.
   - Rationale: Keeps benchmarks discoverable and avoids mixing application logic into low-level quadrature modules.
   - Alternatives considered: Embedding benchmark logic directly in scripts was rejected because it weakens testability.

2. Use manufactured-solution Poisson setups for both planar and volume cases.
   - Rationale: Provides exact-reference error metrics and deterministic pass/fail criteria.
   - Alternatives considered: Purely empirical residual-only checks were rejected because they do not provide clear accuracy targets.

3. Keep folded quadrature backend selection explicit in benchmark configs.
   - Rationale: Ensures benchmark outputs can be tied to specific integration paths (jplus vs folded, CAD-native vs fallback where relevant).
   - Alternatives considered: Hidden backend auto-selection was rejected because it obscures parity interpretation.

4. Define tiered benchmark profiles for CI and deeper runs.
   - Rationale: Fast profiles preserve developer velocity while denser profiles support numerical confidence.
   - Alternatives considered: Single heavy profile was rejected due to CI and local runtime cost.

5. Store benchmark outputs in structured machine-readable form.
   - Rationale: Enables downstream trend tracking and reproducible regression tests.
   - Alternatives considered: Console-only reporting was rejected because it is difficult to consume automatically.

## Risks / Trade-offs

- [Risk] Solver dependency setup may vary across environments. -> Mitigation: make heavy dependencies optional and provide graceful skip behavior.
- [Risk] Benchmark runtimes can become too expensive for default CI. -> Mitigation: split quick vs dense profiles and schedule dense runs separately.
- [Risk] Coupling benchmark APIs to current eval internals could limit refactors. -> Mitigation: define stable benchmark interfaces and keep internals behind adapters.

## Migration Plan

1. Add benchmark data structures and result schema.
2. Implement planar trimmed Poisson benchmark runner and tests.
3. Implement volume trimmed Poisson benchmark runner and tests.
4. Add profile-aware script entry points and documentation.
5. Add CI smoke checks and optional dense benchmark workflow.

## Open Questions

- Which optional solver stack should be the default benchmark backend in this repository?
- Should dense benchmark artifacts be versioned in-repo or published as CI artifacts only?
