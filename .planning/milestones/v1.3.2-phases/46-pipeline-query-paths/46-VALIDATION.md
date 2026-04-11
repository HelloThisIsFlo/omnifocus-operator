---
phase: 46
slug: pipeline-query-paths
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-08
audited: 2026-04-08
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run pytest tests/ -x -q --no-header` |
| **Full suite command** | `uv run pytest tests/ -q --no-header` |
| **Estimated runtime** | ~25 seconds |
| **Suite size** | 1,853 tests |
| **Coverage** | 97.78% |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --no-header`
- **After every plan wave:** Run `uv run pytest tests/ -q --no-header`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 25 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | RESOLVE-11 | — | N/A | unit + integration | `uv run pytest tests/test_resolve_dates.py::TestOverdueShortcut tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_due_overdue_returns_past_due_tasks -x` | ✓ | ✅ green |
| 46-01-02 | 01 | 1 | RESOLVE-12 | — | N/A | unit + integration | `uv run pytest tests/test_due_soon_setting.py -x` | ✓ (16 tests) | ✅ green |
| 46-02-01 | 02 | 1 | EXEC-01 | T-46-04 | Parameterized `?` placeholders | unit | `uv run pytest tests/test_query_builder.py::TestDatePredicates -x` | ✓ (13 tests) | ✅ green |
| 46-02-02 | 02 | 1 | EXEC-07 | — | N/A | unit + integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFiltering::test_due_before_filters_and_excludes_null tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_null_effective_dates_excluded_from_date_filters -x` | ✓ | ✅ green |
| 46-03-01 | 03 | 1 | EXEC-02 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFiltering -x` | ✓ (5 tests) | ✅ green |
| 46-03-02 | 03 | 1 | EXEC-03 | T-46-07 | By design: lifecycle expansion | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_completed_today_auto_includes_completed_availability -x` | ✓ | ✅ green |
| 46-03-03 | 03 | 1 | EXEC-04 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_dropped_last_1w_auto_includes_dropped_availability -x` | ✓ | ✅ green |
| 46-03-04 | 03 | 1 | EXEC-05 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_completed_any_returns_all_completed_regardless_of_date -x` | ✓ | ✅ green |
| 46-03-05 | 03 | 1 | EXEC-06 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_dropped_any_returns_all_dropped_regardless_of_date -x` | ✓ | ✅ green |
| 46-03-06 | 03 | 1 | EXEC-09 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py::TestListTasksDateFilterPipeline::test_date_and_base_filters_compose_with_and tests/test_query_builder.py::TestDatePredicates::test_date_predicates_combine_with_existing_filters -x` | ✓ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_query_builder.py::TestDatePredicates` — 13 date predicate tests (EXEC-01, EXEC-07)
- [x] `tests/test_list_pipelines.py::TestListTasksDateFiltering` — 5 bridge date filtering tests (EXEC-02, EXEC-07)
- [x] `tests/test_list_pipelines.py::TestListTasksDateFilterPipeline` — 11 pipeline integration tests (EXEC-03 through EXEC-06, EXEC-09, RESOLVE-11)
- [x] `tests/test_due_soon_setting.py` — 16 tests for HybridRepository + BridgeOnlyRepository + protocol (RESOLVE-12)
- [x] Test fixtures use `effectiveCompletionDate`, `effectiveDropDate`, `completionDate`, `dropDate` fields

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DueSoonSetting read from live OmniFocus Settings table | RESOLVE-12 | Requires real OmniFocus database | UAT: call `list_tasks(due="soon")` against live DB, verify results match OmniFocus UI |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 25s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-04-08

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** All 10 requirements were fully covered during plan execution via TDD workflow. Wave 0 test files were created as part of Plans 01-03 (not retroactively). 45 new tests across 3 test files cover all requirements with automated verification. 1 manual-only verification remains (live OmniFocus `due="soon"` round-trip, SAFE-01/02 constraint).
