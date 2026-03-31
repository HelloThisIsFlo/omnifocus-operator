---
phase: 36-service-orchestration-cross-path-equivalence-merged-from-old-phases-36-37
verified: 2026-03-31T14:00:00Z
status: passed
score: 13/13 must-haves verified
gaps: []
---

# Phase 36: Service Orchestration + Cross-Path Equivalence Verification Report

**Phase Goal:** Service layer adds validation, defaults, and duration parsing to existing pipelines; cross-path equivalence tests prove BridgeRepository matches SQL path
**Verified:** 2026-03-31
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

Plan 01 (INFRA-06):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | `ListTasksQuery(offset=5)` without limit raises ValueError with educational message | VERIFIED | `@model_validator` on `ListTasksQuery` calls `validate_offset_requires_limit`; error constant `OFFSET_REQUIRES_LIMIT` in `errors.py:110` |
| 2 | `ListProjectsQuery(offset=5)` without limit raises ValueError with educational message | VERIFIED | Same validator pattern on `ListProjectsQuery`; test suite passes |
| 3 | `ListProjectsQuery(review_due_within='1w')` parses to `ReviewDueFilter(amount=1, unit='w')` | VERIFIED | `@field_validator("review_due_within", mode="before")` calls `parse_review_due_within`; `_DURATION_PATTERN` regex parses correctly |
| 4 | `ListProjectsQuery(review_due_within='now')` parses to `ReviewDueFilter(amount=None, unit=None)` | VERIFIED | `parse_review_due_within` handles "now" special case explicitly |
| 5 | `ListProjectsQuery(review_due_within='banana')` raises ValueError with valid formats listed | VERIFIED | `parse_review_due_within` raises `REVIEW_DUE_WITHIN_INVALID` with format listing |
| 6 | `_ListProjectsPipeline` expands `ReviewDueFilter` to a datetime in `ListProjectsRepoQuery.review_due_before` | VERIFIED | `_build_repo_query` calls `_expand_review_due`; field is `review_due_before: datetime | None` in `ListProjectsRepoQuery` |
| 7 | `BridgeRepository.list_projects` filters by `review_due_before` datetime | VERIFIED | `bridge.py:189-195` — filters `p.next_review_date <= query.review_due_before` |
| 8 | SQL query builder converts `review_due_before` datetime to CF epoch float for comparison | VERIFIED | `query_builder.py:202-205` — `(query.review_due_before - _CF_EPOCH).total_seconds()` |

Plan 02 (INFRA-03):

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 9 | Same `ListTasksRepoQuery` returns identical task items from BridgeRepository and HybridRepository | VERIFIED | 7 task tests pass for both `[bridge]` and `[sqlite]` params |
| 10 | Same `ListProjectsRepoQuery` returns identical project items from both repos | VERIFIED | 4 project tests pass for both params, including `review_due_before` filter |
| 11 | Same `ListTagsRepoQuery` returns identical tag items from both repos | VERIFIED | 2 tag tests pass for both params |
| 12 | Same `ListFoldersRepoQuery` returns identical folder items from both repos | VERIFIED | 2 folder tests pass for both params |
| 13 | Same perspectives query returns identical items from both repos | VERIFIED | 1 perspective test passes for both params |

**Score:** 13/13 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/agent_messages/errors.py` | `OFFSET_REQUIRES_LIMIT` and `REVIEW_DUE_WITHIN_INVALID` constants | VERIFIED | Both present at lines 110 and 112-115 |
| `src/omnifocus_operator/service/validate.py` | `validate_offset_requires_limit` and `parse_review_due_within` helpers | VERIFIED | Both functions defined, in `__all__`; 80 lines, substantive |
| `src/omnifocus_operator/contracts/use_cases/list/projects.py` | `ReviewDueFilter`, `DurationUnit`, validators, `review_due_before` in RepoQuery | VERIFIED | 71 lines; `DurationUnit(StrEnum)`, `ReviewDueFilter(QueryModel)`, `review_due_within: ReviewDueFilter | None`, `review_due_before: datetime | None` all present |
| `src/omnifocus_operator/contracts/use_cases/list/tasks.py` | `@model_validator` calling `validate_offset_requires_limit` | VERIFIED | Lines 26-31; model validator wired |
| `src/omnifocus_operator/service/service.py` | `_expand_review_due` static method; `review_due_before` in `_build_repo_query` | VERIFIED | `_expand_review_due` present; no raw `review_due_within` pass-through |
| `src/omnifocus_operator/repository/query_builder.py` | `review_due_before` with CF epoch conversion | VERIFIED | Lines 202-205; `total_seconds()` conversion confirmed |
| `src/omnifocus_operator/repository/bridge.py` | `review_due_before` filter in `list_projects` | VERIFIED | Lines 189-195 |
| `tests/test_cross_path_equivalence.py` | 831-line cross-path equivalence test file | VERIFIED | File exists, 831 lines, `params=["bridge", "sqlite"]` fixture at line 608, both `BridgeRepository` and `HybridRepository` seeded |

---

### Key Link Verification

Plan 01:

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/use_cases/list/tasks.py` | `service/validate.py` | `@model_validator` calling `validate_offset_requires_limit` | WIRED | Pattern found at lines 26-31 |
| `contracts/use_cases/list/projects.py` | `service/validate.py` | `@field_validator` calling `parse_review_due_within` | WIRED | Pattern found at lines 42-51 |
| `service/service.py _ListProjectsPipeline` | `contracts/use_cases/list/projects.py ListProjectsRepoQuery` | `_build_repo_query` expands `ReviewDueFilter` to `review_due_before` datetime | WIRED | `review_due_before` assigned in `_build_repo_query` at line 370 |

Plan 02:

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `tests/test_cross_path_equivalence.py` | `src/omnifocus_operator/repository/bridge.py` | `BridgeRepository` seeded with `InMemoryBridge` | WIRED | `BridgeRepository` imported at line 28; `seed_bridge_repo` builds it |
| `tests/test_cross_path_equivalence.py` | `src/omnifocus_operator/repository/hybrid.py` | `HybridRepository` seeded with SQLite test DB | WIRED | `HybridRepository` imported at line 29; `seed_sqlite_repo` builds it |

---

### Data-Flow Trace (Level 4)

The cross-path equivalence tests assert against expected data from neutral test data (not dynamic DB reads), so Level 4 is not applicable here — the artifacts are test infrastructure, not dynamic rendering components. The validation pipeline (string -> ReviewDueFilter -> datetime -> CF epoch) was traced end-to-end via code inspection and confirmed by the passing test suite.

---

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| Phase 36 plan 01 target tests | 169 tests pass in `test_list_contracts`, `test_list_pipelines`, `test_query_builder` | PASS |
| Cross-path equivalence (all 5 entity types, both paths) | 32 runs (16 tests x bridge + sqlite) — all PASSED | PASS |
| Full regression suite | 1337 tests pass, 97.98% coverage | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| INFRA-06 | 36-01 | Educational error messages for invalid filter values | SATISFIED | `OFFSET_REQUIRES_LIMIT` and `REVIEW_DUE_WITHIN_INVALID` constants wired into validators on both query models; 16 new tests in `test_list_contracts.py` |
| INFRA-03 | 36-02 | Bridge fallback produces identical results to SQL path for same filters | SATISFIED | 32 parametrized tests (`[bridge]` + `[sqlite]`) prove equivalence across tasks, projects, tags, folders, perspectives |

No orphaned requirements — REQUIREMENTS.md maps INFRA-03 and INFRA-06 to Phase 36 (merged), both claimed and satisfied.

---

### Anti-Patterns Found

No anti-patterns detected in modified files:
- No `TODO`/`FIXME`/placeholder comments in any key file
- `parse_review_due_within` return type is annotated `object` (not `ReviewDueFilter`) — this is a minor type annotation gap but does not affect runtime behavior. The function always returns a `ReviewDueFilter` instance or raises. Tests pass, mypy is not configured to strict on this annotation.
- No empty implementations, hardcoded empty returns, or stub patterns found

---

### Human Verification Required

None. All goal behaviors are verifiable programmatically and confirmed passing.

---

### Gaps Summary

No gaps. Phase goal fully achieved:

- INFRA-06: Both `ListTasksQuery` and `ListProjectsQuery` validate `offset-without-limit` and raise educational errors. `review_due_within` string input is parsed end-to-end from agent string to CF epoch float through three layers.
- INFRA-03: 32 cross-path equivalence tests (16 unique test cases x 2 repo paths) confirm `BridgeRepository` and `HybridRepository` return identical results for tasks, projects, tags, folders, and perspectives. Full test suite is green at 1337 tests / 97.98% coverage.

---

_Verified: 2026-03-31_
_Verifier: Claude (gsd-verifier)_
