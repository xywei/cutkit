## 1. Benchmark Interfaces and Result Schema

- [x] 1.1 Define benchmark configuration and result dataclasses for planar and volume Poisson runs.
- [x] 1.2 Add machine-readable output schema for benchmark metrics and metadata.
- [x] 1.3 Add profile definitions for quick and dense benchmark modes.

## 2. Planar and Volume Benchmark Runners

- [x] 2.1 Implement trimmed planar Poisson benchmark runner with manufactured-solution error evaluation.
- [x] 2.2 Implement trimmed volume Poisson benchmark runner with manufactured-solution error evaluation.
- [x] 2.3 Add explicit quadrature-backend mode selection and metadata capture in both runners.

## 3. Validation and Regression Tests

- [x] 3.1 Add unit tests for benchmark configuration validation and threshold logic.
- [x] 3.2 Add integration tests for planar benchmark output determinism and acceptance checks.
- [x] 3.3 Add integration tests for volume benchmark output determinism and acceptance checks.

## 4. Script and CI Integration

- [x] 4.1 Add script entry points for quick and dense benchmark execution.
- [x] 4.2 Add CI smoke coverage for quick benchmark profile and optional dense scheduled run.
- [x] 4.3 Document benchmark prerequisites, expected outputs, and update workflow.

## 5. Final Verification

- [x] 5.1 Run benchmark-related tests and ensure deterministic output snapshots pass.
- [x] 5.2 Run `make dev` and confirm repository checks stay green.
