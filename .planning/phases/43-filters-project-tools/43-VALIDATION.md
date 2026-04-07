---
phase: 43
slug: filters-project-tools
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-07
validated: 2026-04-07
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 43-01-01 | 01 | 1 | FILT-01 | unit+integration | `uv run pytest tests/test_service_resolve.py tests/test_list_pipelines.py -x -q -k "dollar_inbox_consumed or dollar_inbox_returns"` | ✅ green |
| 43-01-02 | 01 | 1 | FILT-02 | integration | `uv run pytest tests/test_list_pipelines.py -x -q -k "bare_inbox_matches"` | ✅ green |
| 43-01-03 | 01 | 1 | FILT-03, FILT-04, FILT-05 | unit+integration | `uv run pytest tests/ -x -q -k "contradictory or redundant or in_inbox_true_with_project"` | ✅ green |
| 43-02-01 | 02 | 2 | PROJ-01, PROJ-02 | unit | `uv run pytest tests/test_service_resolve.py -x -q -k "LookupProjectInboxGuard"` | ✅ green |
| 43-02-02 | 02 | 2 | PROJ-03 | integration | `uv run pytest tests/test_list_pipelines.py -x -q -k "ListProjectsInboxWarning"` | ✅ green |
| 43-03-01 | 02 | 2 | NRES-07 | n/a | Inherited — no new code | ✅ green |
| 43-04-01 | 02 | 2 | DESC-03, DESC-04 | schema | `uv run pytest tests/test_output_schema.py tests/test_descriptions.py -x -q` | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Test Evidence

| Requirement | Test File | Test Name(s) |
|-------------|-----------|--------------|
| FILT-01 | `tests/test_service_resolve.py` | `test_dollar_inbox_consumed` |
| FILT-01 | `tests/test_list_pipelines.py` | `test_dollar_inbox_returns_inbox_tasks` |
| FILT-02 | `tests/test_list_pipelines.py` | `test_bare_inbox_matches_project_name_not_system` |
| FILT-03 | `tests/test_service_resolve.py` | `test_dollar_inbox_with_in_inbox_false_contradictory` |
| FILT-03 | `tests/test_list_pipelines.py` | `test_dollar_inbox_with_in_inbox_false_raises` |
| FILT-04 | `tests/test_service_resolve.py` | `test_dollar_inbox_with_in_inbox_true_redundant` |
| FILT-04 | `tests/test_list_pipelines.py` | `test_dollar_inbox_with_in_inbox_true_redundant` |
| FILT-05 | `tests/test_service_resolve.py` | `test_in_inbox_true_with_real_project_contradictory`, `test_in_inbox_true_with_project_id_contradictory` |
| FILT-05 | `tests/test_list_pipelines.py` | `test_in_inbox_true_with_project_raises` |
| PROJ-01 | `tests/test_service_resolve.py` | `test_dollar_inbox_raises`, `test_dollar_trash_raises` |
| PROJ-02 | n/a | No-code: inbox is virtual, never in SQLite or bridge |
| PROJ-03 | `tests/test_list_pipelines.py` | `test_search_inbox_warns`, `test_search_inbox_case_insensitive` |
| NRES-07 | n/a | Inherited — already done before phase 43 |
| DESC-03 | n/a | Intentional no-op per D-21 |
| DESC-04 | `tests/test_output_schema.py` | Schema validation covers description changes |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-04-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Full suite: 1628 passed in 15.29s
