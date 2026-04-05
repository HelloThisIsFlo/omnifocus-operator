---
status: complete
phase: 36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37
source: [36-01-SUMMARY.md, 36-02-SUMMARY.md]
started: 2026-03-31T14:30:00Z
updated: 2026-03-31T14:45:00Z
---

## Current Test

[testing complete]

## Tests

### 1. ReviewDueFilter Parsing Tests
expected: Tests in test_list_contracts.py cover all documented formats ("1w", "2m", "30d", "1y", "now") and reject invalid inputs with educational errors. ReviewDueFilter stores correct amount/unit.
result: pass

### 2. Educational Error Messages
expected: OFFSET_REQUIRES_LIMIT and REVIEW_DUE_WITHIN_INVALID in errors.py are agent-friendly — they explain what went wrong, what to do instead, and list valid formats.
result: pass

### 3. Pipeline End-to-End: String → CF Epoch
expected: Tests in test_list_pipelines.py prove _expand_review_due converts ReviewDueFilter to datetime. Tests in test_query_builder.py prove datetime converts to CF epoch float. The chain: "1w" → ReviewDueFilter(1, 'w') → datetime → CF epoch float.
result: pass

### 4. Cross-Path Equivalence: All 5 Entity Types
expected: test_cross_path_equivalence.py has parametrized tests running against both BridgeRepository and HybridRepository. All 5 entity types covered: tasks, projects, tags, folders, perspectives. 16 test cases × 2 paths = 32 runs.
result: pass

### 5. Cross-Path Seed Adapters
expected: Neutral test data defined once, then dual seed adapters translate to bridge format (camelCase, ISO dates, inline tags) and SQLite format (CF epoch floats, int booleans, join tables). Tests assert against expected values from neutral data, not against each other.
result: pass

### 6. Full Test Suite Green
expected: `uv run pytest` passes all tests (1337+), no failures, no warnings that indicate real issues.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none — error message assertion gap was fixed inline during UAT (commit 1d9ef4b)]
