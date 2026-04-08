---
phase: 46-pipeline-query-paths
verified: 2026-04-08T12:45:00Z
status: passed
score: 13/13 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "due: 'overdue' and due: 'soon' use OmniFocus pre-computed columns (SQL) / urgency enum (bridge) — matching OmniFocus UI behavior"
    reason: "Superseded by context decisions D-12/D-16 before implementation. Pre-computed dueSoon column was rejected because it excludes overdue tasks (zero overlap), which contradicts the spec. Timestamp comparison (effectiveDateDue < now) is documented in REQUIREMENTS.md RESOLVE-11 revision and in CONTEXT.md D-16 as the correct approach. Behavior matches OmniFocus UI intent even though the mechanism differs."
    accepted_by: "gsd-verifier"
    accepted_at: "2026-04-08T12:45:00Z"
re_verification: false
---

# Phase 46: Pipeline & Query Paths — Verification Report

**Phase Goal:** Agents can filter tasks by date in `list_tasks` with correct results on both SQL and bridge paths
**Verified:** 2026-04-08T12:45:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent can pass date filters on `list_tasks` and receive correctly filtered results — SQL path uses effective CF epoch columns, bridge path uses in-memory comparison with shared resolution logic | ✓ VERIFIED | `_DATE_COLUMN_MAP` in `query_builder.py` maps 7 fields to effective CF epoch columns; `_BRIDGE_FIELD_MAP` in `bridge_only.py` maps same 7 fields to Task model attributes; both use `>=` / `<` semantics; 1853 tests pass |
| 2 | Using `completed` or `dropped` date filter automatically includes those lifecycle states in results without the agent setting availability | ✓ VERIFIED | `_resolve_date_filters()` in `service.py` appends `Availability.COMPLETED`/`DROPPED` for any set lifecycle field; `_build_repo_query()` merges via set-union; `TestListTasksDateFilterPipeline.test_completed_today_auto_includes_completed_availability` + `test_dropped_last_1w_auto_includes_dropped_availability` pass |
| 3 | `due: "overdue"` and `due: "soon"` use OmniFocus pre-computed columns (SQL) / urgency enum (bridge) — matching OmniFocus UI behavior | PASSED (override) | Implementation uses timestamp comparison (`effectiveDateDue < now`), not pre-computed columns. This was a documented design decision (CONTEXT.md D-16: "Never use the dueSoon column — it excludes overdue tasks"), explicitly overriding the roadmap SC. REQUIREMENTS.md RESOLVE-11 revised wording confirms. Test `test_due_overdue_returns_past_due_tasks` confirms "overdue" returns past-due tasks correctly. |
| 4 | `"any"` on completed/dropped includes all tasks in that state; date filters combine with AND with each other and existing base filters | ✓ VERIFIED | `test_completed_any_returns_all_completed_regardless_of_date` and `test_dropped_any_returns_all_dropped_regardless_of_date` pass; `test_date_and_base_filters_compose_with_and` (EXEC-09) passes; `test_multiple_date_filters_and_composition` (bridge path AND) passes |

**Score:** 13/13 truths verified (1 via documented override)

### Deferred Items

None — all planned requirements for Phase 46 are implemented. EXEC-10/11 and BREAK-01 through BREAK-08 are explicitly assigned to Phase 47 in REQUIREMENTS.md.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/protocols.py` | Repository protocol with `get_due_soon_setting` method | ✓ VERIFIED | Line 106: `async def get_due_soon_setting(self) -> DueSoonSetting \| None: ...` |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | HybridRepository reads from SQLite Setting table | ✓ VERIFIED | `_SETTING_MAP` (7 entries) at line 67; `_read_due_soon_setting_sync` at line 1004; `get_due_soon_setting` at line 1034 |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` | BridgeOnlyRepository reads from env var + date filtering loop | ✓ VERIFIED | `get_due_soon_setting` at line 308; `_BRIDGE_FIELD_MAP` at line 52; date filter loop at line 204 |
| `src/omnifocus_operator/repository/hybrid/query_builder.py` | Date predicate generation for all 14 `_after`/`_before` fields | ✓ VERIFIED | `_DATE_COLUMN_MAP` at line 24 (7 entries); `_add_date_conditions` at line 35; called in `build_list_tasks_sql` at line 207 |
| `src/omnifocus_operator/service/service.py` | `_resolve_date_filters()` method and updated `_build_repo_query()` | ✓ VERIFIED | `_resolve_date_filters` at line 401; called in `execute()` at line 358; `_build_repo_query` passes all 14 bounds at lines 500-513 |
| `src/omnifocus_operator/config.py` | `due_soon_threshold: str \| None = None` field | ✓ VERIFIED | Line 59 |
| `tests/test_due_soon_setting.py` | Tests for both repository `get_due_soon_setting` implementations | ✓ VERIFIED | 16 tests: `TestHybridGetDueSoonSetting` (11), `TestRepositoryProtocolIncludesGetDueSoonSetting` (1), `TestBridgeOnlyGetDueSoonSetting` (5) |
| `tests/test_query_builder.py` | SQL date predicate tests | ✓ VERIFIED | `TestDatePredicates` class at line 496; covers all 7 date dimensions, CF epoch conversion, combined filters, count query parity |
| `tests/test_list_pipelines.py` | Bridge and pipeline date filter tests | ✓ VERIFIED | `TestListTasksDateFiltering` at line 917 (5 bridge tests); `TestListTasksDateFilterPipeline` at line 1133 (11 pipeline tests) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/protocols.py` | `DueSoonSetting` enum | return type annotation | ✓ WIRED | TYPE_CHECKING import at line 26; annotation at line 106 |
| `hybrid.py` | SQLite Setting table | `SELECT key, value FROM Setting WHERE key IN (...)` | ✓ WIRED | `_read_due_soon_setting_sync` executes the query at line 1016; maps result via `_SETTING_MAP` |
| `bridge_only.py` | `Settings.due_soon_threshold` | `get_settings().due_soon_threshold` | ✓ WIRED | Line 317; inline import guards against circular imports |
| `query_builder.py` | `ListTasksRepoQuery` | reads `due_after`/`due_before` etc. fields | ✓ WIRED | `_add_date_conditions` uses `getattr(query, f"{field_name}_after", None)` for all 7 field prefixes |
| `bridge_only.py` | Task model fields | compares against `effective_due_date` etc. | ✓ WIRED | Date filter loop at line 204 uses `_BRIDGE_FIELD_MAP` to map field names to `Task` model attributes |
| `service.py _resolve_date_filters()` | `resolve_dates.resolve_date_filter()` | function call per date field | ✓ WIRED | Inline import at line 414; called at line 472 for each non-"any", non-UNSET date field |
| `service.py _resolve_date_filters()` | `repository.get_due_soon_setting()` | conditional call when `due="soon"` | ✓ WIRED | Lines 439-444: checks `isinstance(self._query.due, StrEnum) and self._query.due.value == "soon"` before calling |
| `service.py _build_repo_query()` | `ListTasksRepoQuery` | sets 14 `_after`/`_before` fields + merged availability | ✓ WIRED | Lines 490-513: all 14 fields passed; set-union merge at lines 486-488 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_add_date_conditions()` | `after_val`, `before_val` from `ListTasksRepoQuery` | Pipeline via `_resolve_date_filters()` → `resolve_date_filter()` | Yes — resolved from agent query, not hardcoded | ✓ FLOWING |
| Bridge date filter loop | `after_val`, `before_val` from `ListTasksRepoQuery` | Same pipeline | Yes | ✓ FLOWING |
| `_resolve_date_filters()` | `_now`, 14 `_after`/`_before` bounds | `datetime.now(UTC)` + `resolve_date_filter()` | Yes — live datetime, not mocked | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| All 1853 tests pass (no regressions) | `uv run pytest tests/ -x -q --no-header --no-cov` | `1853 passed in 15.60s` | ✓ PASS |
| Date predicate tests pass | `uv run pytest tests/test_due_soon_setting.py tests/test_query_builder.py --no-cov -q` | `84 passed` | ✓ PASS |
| Pipeline date filter tests pass | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFiltering tests/test_list_pipelines.py::TestListTasksDateFilterPipeline --no-cov -q` | `16 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| RESOLVE-11 | 46-01 / 46-03 | `"overdue"` resolves to `effectiveDateDue < now` (timestamp, not pre-computed column) | ✓ SATISFIED | `resolve_dates.py` line 77-78: `if value == "overdue": return (None, now)`; `test_due_overdue_returns_past_due_tasks` passes |
| RESOLVE-12 | 46-01 / 46-03 | `"soon"` resolves using `DueSoonInterval`/`DueSoonGranularity` from SQLite (Hybrid) or env var (BridgeOnly) | ✓ SATISFIED | `get_due_soon_setting()` in both repos; `_compute_soon_threshold()` in `resolve_dates.py`; conditional call in pipeline |
| EXEC-01 | 46-02 | SQL path adds date predicates on effective CF epoch columns for all 7 date fields | ✓ SATISFIED | `_DATE_COLUMN_MAP` + `_add_date_conditions()` in `query_builder.py`; 13 SQL predicate tests |
| EXEC-02 | 46-02 | Bridge fallback applies identical date filtering in-memory | ✓ SATISFIED | `_BRIDGE_FIELD_MAP` + filter loop in `bridge_only.py`; 5 bridge filter tests |
| EXEC-03 | 46-03 | Using `completed` date filter auto-includes completed tasks | ✓ SATISFIED | `Availability.COMPLETED` appended at service.py line 453; `test_completed_today_auto_includes_completed_availability` passes |
| EXEC-04 | 46-03 | Using `dropped` date filter auto-includes dropped tasks | ✓ SATISFIED | `Availability.DROPPED` appended at service.py line 454; `test_dropped_last_1w_auto_includes_dropped_availability` passes |
| EXEC-05 | 46-03 | `completed: "any"` includes all completed tasks regardless of date | ✓ SATISFIED | "any" skips date resolution, only adds lifecycle availability; `test_completed_any_returns_all_completed_regardless_of_date` passes |
| EXEC-06 | 46-03 | `dropped: "any"` includes all dropped tasks regardless of date | ✓ SATISFIED | Same pattern as EXEC-05; `test_dropped_any_returns_all_dropped_regardless_of_date` passes |
| EXEC-07 | 46-02 | Tasks with no value for a filtered date field are excluded | ✓ SATISFIED | Both SQL (`t.column >= ?` is false for NULL) and bridge (`getattr(t, attr_name) is not None` check); `test_null_effective_dates_excluded_from_date_filters` and `test_due_before_filters_and_excludes_null` pass |
| EXEC-09 | 46-02 / 46-03 | Date filters combine with AND with each other and existing base filters | ✓ SATISFIED | Sequential `conditions.append()` in `_add_date_conditions` (SQL AND); sequential list comprehensions (bridge AND); `test_date_and_base_filters_compose_with_and` and `test_multiple_date_filters_and_composition` pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `service.py` | 408-416 | Inline imports with `# noqa: PLC0415` | Info | Intentional pattern documented in SUMMARY: `from __future__ import annotations` causes linter to strip top-level imports that appear unused; inline imports in `_resolve_date_filters` avoid this. Not a stub or regression. |

No blockers or warnings found. The one Info item is a documented, intentional pattern.

### Human Verification Required

None — all observable truths can be verified programmatically through the test suite and code inspection.

### Gaps Summary

No gaps. All 10 requirements assigned to Phase 46 (RESOLVE-11, RESOLVE-12, EXEC-01 through EXEC-07, EXEC-09) are satisfied. All artifacts are substantive and wired. The full test suite passes at 1853 tests.

Roadmap SC #3 mentions "pre-computed columns" — this was superseded before implementation by a documented design decision (CONTEXT.md D-16) that is strictly better: timestamp comparison avoids the `dueSoon` column's known flaw (it excludes overdue tasks). The override is applied above.

---

_Verified: 2026-04-08T12:45:00Z_
_Verifier: Claude (gsd-verifier)_
