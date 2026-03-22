## 1. Result Schema and Fixture Plumbing

- [x] 1.1 Define a machine-readable Section 6 result schema and add serializer support in reproduction scripts.
- [x] 1.2 Add fixture directories and naming conventions for mode/profile-specific baselines.
- [x] 1.3 Generate initial baseline fixtures for polygonized quick, CAD-native quick, and selected 3D profiles.

## 2. Parity Engine and Script Integration

- [x] 2.1 Implement a parity checker that compares manifests to fixtures using absolute/relative tolerances.
- [x] 2.2 Add CAD-unavailable handling with explicit unavailable status messaging.
- [x] 2.3 Integrate parity checks into `scripts/reproduce_antolin_2022_examples.py` and related wrappers.

## 3. Tests and CI Hooks

- [x] 3.1 Add unit tests for manifest schema validation and tolerance logic.
- [x] 3.2 Add integration tests that verify pass/fail behavior for in-tolerance and out-of-tolerance cases.
- [x] 3.3 Wire parity checks into CI jobs that satisfy required environment prerequisites.

## 4. Diagnostics and Documentation

- [x] 4.1 Add row-level and metric-level parity diff reporting in failure output.
- [x] 4.2 Document fixture update workflow and review expectations.
- [x] 4.3 Run `make dev` and ensure checks pass with parity tooling enabled.
