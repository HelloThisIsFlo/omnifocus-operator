---
phase: 46-pipeline-query-paths
verified: 2026-04-08T15:00:00Z
status: passed
score: 4/4 must-haves verified
overrides_applied: 1
overrides:
  - must_have: "due: 'overdue' and due: 'soon' use OmniFocus pre-computed columns (SQL) / urgency enum (bridge) — matching OmniFocus UI behavior"
    reason: "Superseded by context decisions D-12/D-16 before implementation. Pre-computed dueSoon column was rejected because it excludes overdue tasks (zero overlap), which contradicts the spec. Timestamp comparison (effectiveDateDue < now) is documented in REQUIREMENTS.md RESOLVE-11 revision and in CONTEXT.md D-16 as the correct approach. Behavior matches OmniFocus UI intent even though the mechanism differs."
    accepted_by: "gsd-verifier"
    accepted_at: "2026-04-08T12:45:00Z"
re_verification:
  previous_status: passed
  previous_score: 13/13
  gaps_closed:
    - "Invalid OPERATOR_DUE_SOON_THRESHOLD should fail at startup not at query time (UAT gap: plan 04)"
    - "resolve_date_filter should return rich ResolvedDateBounds type with warnings (UAT gap: plan 05)"
    - "Due-soon None fallback with agent warning should live in domain resolver (UAT gap: plan 05)"
    - "Inline noqa imports in _resolve_date_filters should be moved to top-level (UAT gap: plan 05)"
  gaps_remaining: []
  regressions: []
---

# Phase 46: Pipeline & Query Paths — Verification Report

**Phase Goal:** Agents can filter tasks by date in `list_tasks` with correct results on both SQL and bridge paths
**Verified:** 2026-04-08T15:00:00Z
**Status:** PASSED
**Re-verification:** Yes — after UAT gap closure (plans 04 and 05)

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Agent can pass date filters on `list_tasks` and receive correctly filtered results — SQL path uses effective CF epoch columns, bridge path uses in-memory comparison with shared resolution logic | ✓ VERIFIED | `_DATE_COLUMN_MAP` (7 entries) in `query_builder.py`; `_BRIDGE_FIELD_MAP` (7 entries) in `bridge_only.py`; both use `>=`/`<` semantics; 1861 tests pass |
| 2 | Using `completed` or `dropped` date filter automatically includes those lifecycle states in results without the agent setting availability | ✓ VERIFIED | `_resolve_date_filters()` appends `Availability.COMPLETED`/`DROPPED`; `_build_repo_query()` merges via set-union; `test_completed_today_auto_includes_completed_availability` and `test_dropped_last_1w_auto_includes_dropped_availability` pass |
| 3 | `due: "overdue"` and `due: "soon"` use OmniFocus pre-computed columns (SQL) / urgency enum (bridge) — matching OmniFocus UI behavior | PASSED (override) | Implementation uses timestamp comparison (`effectiveDateDue < now`), not pre-computed columns. Design decision CONTEXT.md D-16: pre-computed `dueSoon` column excludes overdue tasks. REQUIREMENTS.md RESOLVE-11 revised wording confirms timestamp approach. `test_due_overdue_returns_past_due_tasks` confirms correct behavior. |
| 4 | `"any"` on completed/dropped includes all tasks in that state; date filters combine with AND with each other and existing base filters | ✓ VERIFIED | `test_completed_any_returns_all_completed_regardless_of_date`, `test_dropped_any_returns_all_dropped_regardless_of_date`, `test_date_and_base_filters_compose_with_and` (EXEC-09), `test_multiple_date_filters_and_composition` all pass |

**Score:** 4/4 truths verified (1 via documented override)

### Deferred Items

None — all planned requirements for Phase 46 are implemented. EXEC-10/11 and BREAK-01 through BREAK-08 are explicitly assigned to Phase 47 in REQUIREMENTS.md.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/protocols.py` | Repository protocol with `get_due_soon_setting` method | ✓ VERIFIED | Line 106: `async def get_due_soon_setting(self) -> DueSoonSetting \| None: ...` |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | HybridRepository reads from SQLite Setting table | ✓ VERIFIED | `_SETTING_MAP` (7 entries) at line 67; `_read_due_soon_setting_sync` at line 1004; `get_due_soon_setting` at line 1034 |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` | BridgeOnlyRepository simplified get_due_soon_setting + date filtering loop | ✓ VERIFIED | `get_due_soon_setting` at line 309 is a one-liner returning `get_settings().due_soon_threshold`; `_BRIDGE_FIELD_MAP` at line 53; date filter loop at line 205 |
| `src/omnifocus_operator/repository/hybrid/query_builder.py` | Date predicate generation for all 14 `_after`/`_before` fields | ✓ VERIFIED | `_DATE_COLUMN_MAP` at line 24 (7 entries); `_add_date_conditions` at line 35; called in `build_list_tasks_sql` at line 207 |
| `src/omnifocus_operator/service/service.py` | `_resolve_date_filters()` method with top-level imports + updated `_build_repo_query()` | ✓ VERIFIED | `_resolve_date_filters` at line 405; called in `execute()` at line 362; no inline `# noqa: PLC0415` imports; `_build_repo_query` passes all 14 bounds |
| `src/omnifocus_operator/config.py` | `field_validator` on `due_soon_threshold` converting str to `DueSoonSetting` at startup | ✓ VERIFIED | `due_soon_threshold: Any = None` at line 61; `@field_validator("due_soon_threshold", mode="before")` at line 63; raises `ValueError` on invalid values (wrapped into `ValidationError` by pydantic) |
| `src/omnifocus_operator/service/resolve_dates.py` | `ResolvedDateBounds` dataclass + fallback for due-soon None case | ✓ VERIFIED | `class ResolvedDateBounds` at line 22 (frozen dataclass with `after`, `before`, `warnings`); `_resolve_shortcut` falls back to TODAY + `DUE_SOON_THRESHOLD_NOT_DETECTED` warning at line 99 |
| `src/omnifocus_operator/agent_messages/warnings.py` | `DUE_SOON_THRESHOLD_NOT_DETECTED` warning constant | ✓ VERIFIED | Defined at line 128 in `# --- Date Resolution ---` section |
| `tests/test_due_soon_setting.py` | Tests for both repos + new `TestSettingsDueSoonValidation` class | ✓ VERIFIED | `TestSettingsDueSoonValidation` at line 193 (4 tests); `TestBridgeOnlyGetDueSoonSetting` updated at line 152; total 20 tests in file |
| `tests/test_query_builder.py` | SQL date predicate tests | ✓ VERIFIED | `TestDatePredicates` class covers all 7 date dimensions, CF epoch conversion, combined filters, count query parity |
| `tests/test_list_pipelines.py` | Bridge + pipeline date filter tests including due-soon fallback | ✓ VERIFIED | `TestListTasksDateFiltering` (5 bridge tests); `TestListTasksDateFilterPipeline` (12 pipeline tests including `test_due_soon_none_threshold_falls_back_to_today_with_warning`) |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/protocols.py` | `DueSoonSetting` enum | TYPE_CHECKING import + return type annotation | ✓ WIRED | `DueSoonSetting` in TYPE_CHECKING block; method signature at line 106 |
| `hybrid.py` | SQLite Setting table | `SELECT key, value FROM Setting WHERE key IN (...)` | ✓ WIRED | `_read_due_soon_setting_sync` executes the query; maps via `_SETTING_MAP` |
| `config.py field_validator` | `DueSoonSetting` enum | lazy import inside `_validate_due_soon_threshold` + `DueSoonSetting[value.upper()]` | ✓ WIRED | Lazy import at line 66 to avoid circular dependency; case-insensitive lookup; converts at Settings construction time |
| `bridge_only.py get_due_soon_setting()` | `Settings.due_soon_threshold` (pre-validated `DueSoonSetting \| None`) | `get_settings().due_soon_threshold` | ✓ WIRED | One-liner at line 316; no enum conversion logic (moved to config.py validator) |
| `query_builder.py` | `ListTasksRepoQuery` date fields | `getattr(query, f"{field_name}_after/before", None)` in `_add_date_conditions` | ✓ WIRED | `_add_date_conditions` called at line 207; iterates `_DATE_COLUMN_MAP` generating CF-epoch parameterized predicates |
| `bridge_only.py` | `Task` model fields | `_BRIDGE_FIELD_MAP` dict + `getattr(t, attr_name)` with None check | ✓ WIRED | Loop at line 205; `is not None` guard ensures NULL exclusion (EXEC-07) |
| `service.py _resolve_date_filters()` | `resolve_date_filter()` in `resolve_dates.py` | top-level import + function call per date field | ✓ WIRED | Top-level import at line 65; called at line 467 consuming `ResolvedDateBounds` attributes |
| `service.py _resolve_date_filters()` | `repository.get_due_soon_setting()` | conditional call when `due.value == "soon"` | ✓ WIRED | Lines 434-439: isinstance + value check before calling |
| `resolve_dates.py _resolve_shortcut()` | `DUE_SOON_THRESHOLD_NOT_DETECTED` warning | lazy import inside `_resolve_shortcut` | ✓ WIRED | Import at line 85; used at line 105 when `due_soon_setting is None` |
| `service.py _resolve_date_filters()` | `self._warnings` | `self._warnings.extend(resolved.warnings)` | ✓ WIRED | Line 477; propagates warnings from `ResolvedDateBounds` to pipeline warnings → agent response |
| `service.py _build_repo_query()` | `ListTasksRepoQuery` | passes all 14 `_after`/`_before` fields + merged lifecycle availability | ✓ WIRED | Lines 486-510: set-union merge at 483-484; all 14 bounds at 496-509 |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `_add_date_conditions()` | `after_val`/`before_val` from `ListTasksRepoQuery` | Pipeline via `_resolve_date_filters()` → `resolve_date_filter()` → `ResolvedDateBounds` | Yes — resolved from agent query via live datetime, not hardcoded | ✓ FLOWING |
| Bridge date filter loop | `after_val`/`before_val` from `ListTasksRepoQuery` | Same pipeline | Yes | ✓ FLOWING |
| `_resolve_date_filters()` | `_now`, 14 `_after`/`_before` bounds | `datetime.now(UTC)` captured once + `resolve_date_filter()` returning `ResolvedDateBounds` | Yes — live timestamp, warnings flow through | ✓ FLOWING |
| `get_due_soon_setting()` (BridgeOnly) | `Settings.due_soon_threshold` | Pre-validated at `Settings` construction via `field_validator` | Yes — startup-time validation, stored as `DueSoonSetting \| None` | ✓ FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Full test suite passes (1861 tests) | `uv run pytest tests/ -x -q --no-header --no-cov` | `1861 passed in 15.61s` | ✓ PASS |
| Plan 04 gap closure: startup-time validation | `uv run python -c "from pydantic import ValidationError; from omnifocus_operator.config import Settings; ..."` | Valid values store as `DueSoonSetting`; invalid raises `ValidationError`; None accepted | ✓ PASS |
| Plan 04 + 05 targeted tests | `uv run pytest tests/test_due_soon_setting.py::TestSettingsDueSoonValidation tests/test_due_soon_setting.py::TestBridgeOnlyGetDueSoonSetting` | `9 passed` | ✓ PASS |
| Plan 05 gap closure: fallback + warning | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_due_soon_none_threshold_falls_back_to_today_with_warning` | `1 passed` | ✓ PASS |
| No inline noqa in service.py | `grep -n "noqa: PLC0415" src/omnifocus_operator/service/service.py` | No matches | ✓ PASS |
| Lint clean on service.py | `uv run ruff check src/omnifocus_operator/service/service.py` | `All checks passed!` | ✓ PASS |
| Key phase 46 tests | `uv run pytest tests/test_due_soon_setting.py tests/test_query_builder.py tests/test_list_pipelines.py::TestListTasksDateFiltering tests/test_list_pipelines.py::TestListTasksDateFilterPipeline --no-cov -q` | `105 passed` | ✓ PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| RESOLVE-11 | 46-03 | `"overdue"` resolves to `effectiveDateDue < now` (timestamp comparison) | ✓ SATISFIED | `resolve_dates.py` line 96: `return ResolvedDateBounds(after=None, before=now)`; `test_due_overdue_returns_past_due_tasks` passes |
| RESOLVE-12 | 46-01, 46-04 | `"soon"` uses SQLite Setting table (Hybrid) or env var (BridgeOnly); invalid env var fails at startup | ✓ SATISFIED | `get_due_soon_setting()` in both repos; `field_validator` in `config.py` validates at construction; `TestSettingsDueSoonValidation` passes; fallback to TODAY + warning via plan 05 |
| EXEC-01 | 46-02 | SQL path adds date predicates on effective CF epoch columns for all 7 date fields | ✓ SATISFIED | `_DATE_COLUMN_MAP` + `_add_date_conditions()` in `query_builder.py`; 13 SQL predicate tests pass |
| EXEC-02 | 46-02, 46-05 | Bridge fallback applies identical date filtering in-memory; resolver returns rich type | ✓ SATISFIED | `_BRIDGE_FIELD_MAP` + filter loop in `bridge_only.py`; `resolve_date_filter` returns `ResolvedDateBounds`; 5 bridge tests pass |
| EXEC-03 | 46-03 | Using `completed` date filter auto-includes completed tasks | ✓ SATISFIED | `Availability.COMPLETED` appended in `_resolve_date_filters`; set-union merge; `test_completed_today_auto_includes_completed_availability` passes |
| EXEC-04 | 46-03 | Using `dropped` date filter auto-includes dropped tasks | ✓ SATISFIED | `Availability.DROPPED` appended; same mechanism; `test_dropped_last_1w_auto_includes_dropped_availability` passes |
| EXEC-05 | 46-03 | `completed: "any"` includes all completed tasks regardless of date | ✓ SATISFIED | "any" skips date resolution, only adds lifecycle availability; `test_completed_any_returns_all_completed_regardless_of_date` passes |
| EXEC-06 | 46-03 | `dropped: "any"` includes all dropped tasks regardless of date | ✓ SATISFIED | Same pattern as EXEC-05; `test_dropped_any_returns_all_dropped_regardless_of_date` passes |
| EXEC-07 | 46-02 | Tasks with no value for a filtered date field are excluded | ✓ SATISFIED | SQL: `t.column >= ?` is false for NULL values; bridge: `getattr(t, attr_name) is not None` guard; `test_null_effective_dates_excluded_from_date_filters` and `test_due_before_filters_and_excludes_null` pass |
| EXEC-09 | 46-02, 46-03 | Date filters combine with AND with each other and existing base filters | ✓ SATISFIED | SQL: sequential `conditions.append()` in `_add_date_conditions`; bridge: sequential list comprehensions; `test_date_and_base_filters_compose_with_and` and `test_multiple_date_filters_and_composition` pass |

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `resolve_dates.py` | 85 | `from omnifocus_operator.agent_messages.warnings import ... # noqa: PLC0415` inside `_resolve_shortcut()` | Info | Intentional lazy import inside private function — avoids a circular import at module load time. Not a stub; the import is used immediately at line 105. The warning constant flows correctly into `ResolvedDateBounds.warnings`. Not in `_resolve_date_filters` which was the plan 05 cleanup target. |

No blockers or warnings. The one noqa in `resolve_dates.py` is scoped to a private helper inside the domain module, is correctly used, and is outside the scope of plan 05's cleanup (which targeted `service.py`'s `_resolve_date_filters`).

### Human Verification Required

None — all observable truths verifiable programmatically through the test suite and code inspection.

### Gaps Summary

No gaps. All 10 requirements assigned to Phase 46 (RESOLVE-11, RESOLVE-12, EXEC-01 through EXEC-07, EXEC-09) are satisfied. The two UAT issues identified after the initial verification have been fully resolved by plans 04 and 05:

1. **Plan 04 gap (RESOLVE-12 completeness):** `OPERATOR_DUE_SOON_THRESHOLD` now validated at startup via `field_validator` in `Settings`. Invalid values produce `ValidationError` at `Settings` construction (server startup), triggering error-serving mode. `BridgeOnlyRepository.get_due_soon_setting()` simplified to a one-liner returning the pre-validated `DueSoonSetting | None` field.

2. **Plan 05 gap (EXEC-01/02 / architecture quality):** `resolve_date_filter` now returns `ResolvedDateBounds` (frozen dataclass with `after`, `before`, `warnings`). Due-soon None fallback (defaulting to TODAY + agent warning) lives in the domain resolver (`resolve_dates.py`), not the service pipeline. All four inline `# noqa: PLC0415` imports removed from `_resolve_date_filters` — four imports moved to top-level runtime imports section of `service.py`; lint passes clean.

Full suite: 1861 tests passing.

---

_Verified: 2026-04-08T15:00:00Z_
_Verifier: Claude (gsd-verifier)_
