---
phase: 50
slug: use-omnifocus-settings-api-for-date-preferences-and-due-soon
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-11
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~26 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test File | Status |
|---------|------|------|-------------|-----------|-------------------|-----------|--------|
| 50-01-01 | 01 | 1 | PREF-01 | unit | `uv run pytest tests/test_bridge.py -x -q -k "get_settings"` | tests/test_bridge.py | ✅ green |
| 50-01-02 | 01 | 1 | PREF-02 | unit | `uv run pytest tests/test_preferences.py -x -q -k "Lazy"` | tests/test_preferences.py | ✅ green |
| 50-01-02 | 01 | 1 | PREF-03 | unit | `uv run pytest tests/test_preferences.py -x -q -k "Fallback"` | tests/test_preferences.py | ✅ green |
| 50-01-02 | 01 | 1 | PREF-08 | unit | `uv run pytest tests/test_preferences.py -x -q -k "seven_due_soon"` | tests/test_preferences.py | ✅ green |
| 50-01-02 | 01 | 1 | PREF-09 | unit+integ | `uv run pytest tests/test_preferences.py tests/test_list_pipelines.py -x -q -k "unknown_pair or two_days or due_soon_uses"` | tests/test_preferences.py, tests/test_list_pipelines.py | ✅ green |
| 50-02-01 | 02 | 2 | PREF-04 | integration | `uv run pytest tests/test_preferences_pipeline_integration.py -x -q -k "DueDate"` | tests/test_preferences_pipeline_integration.py | ✅ green |
| 50-02-01 | 02 | 2 | PREF-05 | integration | `uv run pytest tests/test_preferences_pipeline_integration.py -x -q -k "DeferDate"` | tests/test_preferences_pipeline_integration.py | ✅ green |
| 50-02-01 | 02 | 2 | PREF-06 | integration | `uv run pytest tests/test_preferences_pipeline_integration.py -x -q -k "PlannedDate"` | tests/test_preferences_pipeline_integration.py | ✅ green |
| 50-02-01 | 02 | 2 | PREF-07 | integration | `uv run pytest tests/test_preferences_pipeline_integration.py -x -q -k "FieldAware or field_specific"` | tests/test_preferences_pipeline_integration.py | ✅ green |
| 50-02-02 | 02 | 2 | PREF-10 | structural | `grep -r "get_due_soon_setting" src/omnifocus_operator/contracts/` (no matches) | N/A — deletion verified | ✅ green |
| 50-02-02 | 02 | 2 | PREF-11 | structural | `grep -r "_read_due_soon_setting_sync\|_SETTING_MAP" src/omnifocus_operator/repository/hybrid/` (no matches) | N/A — deletion verified | ✅ green |
| 50-02-02 | 02 | 2 | PREF-12 | structural | `grep -r "OPERATOR_DUE_SOON_THRESHOLD\|due_soon_threshold" src/` (no matches) | N/A — deletion verified | ✅ green |
| 50-02-02 | 02 | 2 | PREF-13 | unit | `uv run pytest tests/test_descriptions.py -x -q` | tests/test_descriptions.py | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_preferences.py` — 20 tests covering PREF-01/02/03/08/09
- [x] `tests/test_bridge.py` — 5 tests covering bridge get_settings (PREF-01)
- [x] `tests/conftest.py` — service fixture with OmniFocusPreferences wiring

*Existing infrastructure covers most phase requirements. Wave 0 adds preferences-specific test stubs and InMemoryBridge handler.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge reads live OmniFocus settings | PREF-01 | Requires real OmniFocus app | UAT: call `get_settings` via Claude Code CLI, verify returned values match OmniFocus preferences |
| Date-only write applies user's default time | PREF-05 | Requires real OmniFocus to verify task creation time | UAT: add task with date-only dueDate, verify in OmniFocus that configured default time is applied |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-11

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Gaps found | 4 |
| Resolved | 4 |
| Escalated | 0 |

**Details:** PREF-04/05/06/07 lacked integration tests for write pipeline date-only enrichment. Added `tests/test_preferences_pipeline_integration.py` (13 tests) verifying _AddTaskPipeline and _EditTaskPipeline fetch per-field default times from OmniFocusPreferences.
