# Docs Anchor-Level Link Validation

## Objective

Extend docs freshness checks to validate markdown heading anchors for local
in-file and in-repo markdown links so stale `#anchor` references fail quality
gates early.

## Scope

- Parse heading IDs from markdown files in the existing freshness scan scope.
- Validate `#anchor` fragments for links to the same file.
- Validate cross-file markdown fragments for links to other local docs.
- Keep error reporting actionable (source file + reference + unresolved anchor).
- Integrate into existing checker/tests without broad workflow changes.

## Non-Goals

- Full markdown spec conformance for every renderer-specific anchor algorithm.
- Validation of external URLs and non-markdown link targets.
- A full documentation linter beyond anchor freshness.

## Acceptance Criteria

- Broken in-file anchor links are detected by docs freshness checks.
- Broken cross-file markdown anchor links are detected by docs freshness checks.
- Existing docs freshness behavior for path existence remains stable.
- `make dev` passes.

## Implementation Checklist

- [x] Add OpenSpec proposal/design/spec/tasks for anchor-level freshness checks.
- [x] Add markdown heading anchor extraction helper(s) and normalization.
- [x] Validate in-file `#anchor` references.
- [x] Validate cross-file markdown `#anchor` references.
- [x] Add tests for valid/invalid anchor references and edge cases.
- [x] Update docs for anchor-validation coverage and limitations.
- [x] Run focused tests and `make dev`.

## Risks

- Anchor normalization can differ across markdown ecosystems.
- Overly strict parsing could produce false positives for uncommon heading forms.
- Performance may regress if anchor extraction repeatedly reparses large files.
