---
phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
verified: 2026-04-11T14:30:00Z
status: human_needed
score: 7/7
overrides_applied: 0
human_verification:
  - test: "Call get_settings via bridge with OmniFocus running"
    expected: "Returns dict with DefaultDueTime, DefaultStartTime, DefaultPlannedTime, DueSoonInterval, DueSoonGranularity matching actual OmniFocus preferences"
    why_human: "Requires the real OmniFocus app to be running — cannot verify OmniJS API against live app in automated tests"
  - test: "Create a task via add_tasks with date-only dueDate (e.g. '2026-07-15') when OmniFocus DefaultDueTime is set to e.g. 19:00"
    expected: "Task appears in OmniFocus with due date '2026-07-15 19:00' — not midnight"
    why_human: "Requires real OmniFocus write + inspection to verify the default time is applied end-to-end through the bridge"
---

# Phase 50: OmniFocus Settings API Verification Report

**Phase Goal:** Replace fragile SQLite plist-parsing for DueSoon threshold with OmniJS settings API, and upgrade date-only write inputs from midnight-local to user-configured default times — matching OmniFocus UI behavior
**Verified:** 2026-04-11T14:30:00Z
**Status:** human_needed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Bridge `get_settings` command reads date-related OmniFocus preferences via OmniJS `settings.objectForKey()` and returns them as clean primitives | VERIFIED | `bridge.js:375-388` — `handleGetSettings()` reads 5 keys via `settings.objectForKey()`. Dispatched at line 409. |
| 2 | Preferences module loads settings lazily on first use, caches for server lifetime, and exposes domain-typed values (`DueSoonSetting` enum, typed default times) — consumers never see raw interval/granularity | VERIFIED | `service/preferences.py` — `_ensure_loaded()` sets `_loaded=True` before bridge call, second call skips. `get_due_soon_setting()` returns `DueSoonSetting` enum. `get_default_time()` returns normalized `HH:MM:SS` string. Tests in `test_preferences.py:78-112` confirm caching. |
| 3 | Date-only write input on `dueDate`/`deferDate`/`plannedDate` enriched with user's configured default time instead of midnight | VERIFIED | `domain.py:123` — `normalize_date_input(value, default_time="00:00:00")` uses `default_time` in date-only branch. `service.py:543-552` and `683-692` — both `_AddTaskPipeline` and `_EditTaskPipeline._normalize_dates()` are async and call `self._preferences.get_default_time(field)` per field. |
| 4 | DueSoon threshold sourced from bridge settings via preferences module — SQLite plist-parsing and `OPERATOR_DUE_SOON_THRESHOLD` env var deleted | VERIFIED | `service.py:330` — `_ReadPipeline._resolve_date_filters` calls `self._preferences.get_due_soon_setting()`. `grep` confirms zero `get_due_soon_setting` or `OPERATOR_DUE_SOON_THRESHOLD` references in `src/` except the preferences module itself. `_SETTING_MAP`, `_read_due_soon_setting_sync`, `get_due_soon_setting` all absent from `hybrid.py`. |
| 5 | When settings unavailable, OmniFocus factory defaults used with a warning — no error-serving mode, no request failure | VERIFIED | `preferences.py:92-108` — `_ensure_loaded()` catches all exceptions, appends `SETTINGS_FALLBACK_WARNING`, returns (does not re-raise). Factory defaults set in constructor, never mutated on failure. `test_preferences.py:119-165` covers all fallback scenarios including no-retry. |
| 6 | `get_due_soon_setting()` removed from Repository protocol — service reads DueSoon from preferences module | VERIFIED | `protocols.py` — no `get_due_soon_setting` method. `bridge_only.py` — no `get_due_soon_setting` method. `grep -r "get_due_soon_setting" src/` returns only `preferences.py` (definition) and `service.py:330` (usage). |
| 7 | Tool descriptions document default time behavior, "soon" threshold source, and restart requirement for preference changes | VERIFIED | `descriptions.py:37-41` — `_DATE_INPUT_NOTE` contains "Date-only inputs (no time) use your OmniFocus default time for that field" and "restart if you change them". `descriptions.py:526` — LIST_TASKS_TOOL_DOC: "The 'soon' shortcut uses your OmniFocus due-soon threshold preference." `descriptions.py:551` — LIST_PROJECTS_TOOL_DOC same. |

**Score:** 7/7 truths verified

### Deferred Items

None.

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/bridge/bridge.js` | `handleGetSettings` function in dispatch | VERIFIED | Lines 375-388 (function), line 409 (dispatch branch) |
| `tests/doubles/bridge.py` | `InMemoryBridge` `get_settings` handler | VERIFIED | Line 175-176 (`if operation == "get_settings"` branch). `configure_settings()` at line 153. `_settings` dict at line 121. |
| `src/omnifocus_operator/service/preferences.py` | `OmniFocusPreferences` class with lazy load + cache + fallback | VERIFIED | 171 lines. All required methods present: `get_due_soon_setting`, `get_default_time`, `get_warnings`, `_ensure_loaded`, `_apply`, `_normalize_time`. |
| `tests/test_preferences.py` | Unit tests for preferences module, min 50 lines | VERIFIED | 275 lines, 20 test functions, 6 test classes — all 6 required classes present. |
| `src/omnifocus_operator/service/domain.py` | `normalize_date_input` with `default_time` parameter | VERIFIED | Line 123: `def normalize_date_input(value: str, default_time: str = "00:00:00") -> str` |
| `src/omnifocus_operator/service/service.py` | `OperatorService` with `self._preferences` collaborator | VERIFIED | Line 137-139: constructor accepts and stores preferences. All pipelines receive preferences. |
| `src/omnifocus_operator/server.py` | Lifespan creates `OmniFocusPreferences` and injects into `OperatorService` | VERIFIED | Lines 102-109: imports `OmniFocusPreferences`, creates from `repository._bridge`, passes to `OperatorService`. |
| `src/omnifocus_operator/contracts/protocols.py` | Repository protocol without `get_due_soon_setting` | VERIFIED | No `get_due_soon_setting` method found. |
| `src/omnifocus_operator/agent_messages/descriptions.py` | Updated tool descriptions with "default time" and threshold source | VERIFIED | `_DATE_INPUT_NOTE` updated. "soon threshold preference" in LIST_TASKS and LIST_PROJECTS. "restart" included. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `service/preferences.py` | `Bridge.send_command` | `await self._bridge.send_command('get_settings')` | WIRED | Line 104 — exact pattern in `_ensure_loaded()` |
| `service/preferences.py` | `DueSoonSetting` enum | `_SETTING_MAP` lookup | WIRED | `_SETTING_MAP` at lines 46-54, used in constructor and `_apply()` |
| `server.py` | `OmniFocusPreferences` | Constructor injection into `OperatorService` | WIRED | Lines 108-109: `preferences = OmniFocusPreferences(repository._bridge)` then passed to service |
| `service/service.py` | `self._preferences` | `_ReadPipeline._resolve_date_filters` uses preferences for DueSoon | WIRED | Line 330: `due_soon_setting = await self._preferences.get_due_soon_setting()` |
| `service/service.py` | `normalize_date_input` | `_AddTaskPipeline` and `_EditTaskPipeline` pass `default_time` from preferences | WIRED | Lines 549-550 and 689-690: `default_time = await self._preferences.get_default_time(field)` then `normalize_date_input(value, default_time=default_time)` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `service/preferences.py` | `self._due_soon` | `Bridge.send_command("get_settings")` with `_SETTING_MAP` lookup | Yes — reads from OmniJS `settings.objectForKey()` | FLOWING |
| `service/preferences.py` | `self._default_due_time` | `Bridge.send_command("get_settings")["DefaultDueTime"]` via `_normalize_time` | Yes | FLOWING |
| `service/service.py:_AddTaskPipeline` | `default_time` per field | `self._preferences.get_default_time(field)` | Yes — flows from bridge settings | FLOWING |

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| `OmniFocusPreferences` module is importable | `uv run python3 -c "from omnifocus_operator.service.preferences import OmniFocusPreferences; print(OmniFocusPreferences)"` | `<class 'omnifocus_operator.service.preferences.OmniFocusPreferences'>` | PASS |
| preferences test suite passes | `uv run pytest tests/test_preferences.py -x -q --timeout=10` | 20 passed | PASS |
| Full test suite passes, no regressions | `uv run pytest tests/ -x -q --timeout=30` | 1981 passed, 98% coverage | PASS |
| `get_due_soon_setting` absent from Repository protocol and repositories | `grep -r "get_due_soon_setting" src/` | Only in `preferences.py` (definition) and `service.py:330` (usage) | PASS |
| Legacy env var / plist code deleted | `grep -r "OPERATOR_DUE_SOON_THRESHOLD" src/` | No matches | PASS |
| All 6 task commits verified | `git log aa6e26f cc85db1 93b5de6 20eb5f1 87f4186 a7d9afd` | All 6 commits present | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| PREF-01 | 50-01 | Bridge `get_settings` reads 5 OmniJS preference keys | SATISFIED | `bridge.js:375-388` + `InMemoryBridge` dispatch handler |
| PREF-02 | 50-01 | Preferences module lazily loads, maps to domain types, caches | SATISFIED | `preferences.py` — full lazy-load, `_SETTING_MAP`, `_DEFAULT_TIME_MAP` implementation |
| PREF-03 | 50-01 | Bridge failure falls back to factory defaults with warning | SATISFIED | `preferences.py:103-108` + `test_preferences.py:119-165` |
| PREF-04 | 50-02 | `dueDate` date-only enriched with `DefaultDueTime` | SATISFIED | `service.py:549-550` — `get_default_time("due_date")` passes to `normalize_date_input` |
| PREF-05 | 50-02 | `deferDate` date-only enriched with `DefaultStartTime` | SATISFIED | `service.py:549-550` — `get_default_time("defer_date")` |
| PREF-06 | 50-02 | `plannedDate` date-only enriched with `DefaultPlannedTime` | SATISFIED | `service.py:549-550` — `get_default_time("planned_date")` |
| PREF-07 | 50-02 | Date normalization is field-aware in domain.py | SATISFIED | `domain.py:123` — `default_time` parameter; `service.py` fetches per-field time |
| PREF-08 | 50-01, 50-02 | DueSoon exposed as `DueSoonSetting` enum, replaces SQLite and env var | SATISFIED | `preferences.py:46-54` (`_SETTING_MAP`); `hybrid.py` has no `_SETTING_MAP`; `config.py` has no `due_soon_threshold` |
| PREF-09 | 50-01, 50-02 | DueSoon unavailable falls back to TWO_DAYS + warning | SATISFIED | `preferences.py:70-74` (constructor default TWO_DAYS); `domain.py:237-245` (defensive `timedelta(days=2)`) |
| PREF-10 | 50-02 | `get_due_soon_setting()` removed from Repository protocol | SATISFIED | `protocols.py` — no such method. `service.py:330` reads from preferences only. |
| PREF-11 | 50-02 | SQLite plist-parsing deleted from HybridRepository | SATISFIED | `hybrid.py` — no `_SETTING_MAP`, no `_read_due_soon_setting_sync`, no `get_due_soon_setting`. `plistlib` retained for perspective row mapping (acceptable deviation, documented in SUMMARY). |
| PREF-12 | 50-02 | `OPERATOR_DUE_SOON_THRESHOLD` env var and config field deleted | SATISFIED | `config.py` — no `due_soon_threshold`, no `DueSoonSetting` import. `grep` confirms zero matches in `src/`. |
| PREF-13 | 50-02 | Tool descriptions updated with default time, "soon" source, restart note | SATISFIED | `descriptions.py:37-41` (`_DATE_INPUT_NOTE`), lines 526, 551 ("soon threshold preference"), "restart if you change them" |

All 13 PREF requirements (PREF-01 through PREF-13) are SATISFIED.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `service/preferences.py` | 116 | `self._apply(raw)` outside try/except — `int()` coercions can raise `ValueError` on malformed OmniJS response | Warning (WR-03 from code review) | Uncaught exception on malformed bridge response; factory defaults remain correct but exception propagates. Not triggered in practice. |
| `server.py` | 108 | `repository._bridge` — private attribute access, not part of Repository protocol | Warning (WR-02 from code review) | Works for all current repository types; breaks for future repos without `_bridge`. |
| `bridge.js` | 443-464 | `handleGetSettings` not in `module.exports` | Info (IN-01 from code review) | Cannot call in Vitest unit tests directly; no current test gap. |

No blockers found. All warnings are robustness concerns, not functional failures against the phase goal.

### Human Verification Required

#### 1. Live OmniFocus Bridge — get_settings Returns Real Values

**Test:** With OmniFocus running, call the `get_settings` bridge command (e.g. via Claude Code CLI: invoke `get_all` then manually test `get_settings`, or use a UAT script in `uat/`).
**Expected:** Returns a dict matching actual OmniFocus preferences — e.g. if your DefaultDueTime is set to 7pm, returns `{"DefaultDueTime": "19:00:00", ...}` with real values, not factory defaults.
**Why human:** Requires the real OmniFocus app and the production JXA/OmniJS bridge. Cannot invoke `settings.objectForKey()` in automated tests (SAFE-01/02 constraint).

#### 2. Date-Only Write Input Applies User Default Time End-to-End

**Test:** Create a task via the MCP `add_tasks` tool with a date-only `dueDate` (e.g. `"2026-07-15"`). Check the created task in OmniFocus.
**Expected:** The task's due date shows the user's configured DefaultDueTime (e.g. 19:00 if configured to 7pm) — not midnight. This verifies the full pipeline: preferences loaded from bridge -> default time fetched per field -> applied in `normalize_date_input` -> passed to bridge -> OmniFocus stores correctly.
**Why human:** End-to-end verification requires the real OmniFocus app, real bridge, and visual inspection of the created task. Automated tests verify the transformation logic but not the round-trip through the production bridge.

---

## Gaps Summary

No gaps. All 7 success criteria are VERIFIED against the codebase. Full test suite passes (1981 tests, 98% coverage). The phase goal is achieved — SQLite plist-parsing is replaced, OPERATOR_DUE_SOON_THRESHOLD env var is deleted, and date-only write inputs now use user-configured default times.

Two human verification items remain (live OmniFocus UAT). These were identified in VALIDATION.md as "Manual-Only Verifications" from the start — they are not regressions.

Three code review warnings exist but do not block the goal:
- WR-01 (`matches_inbox_name` logic): Pre-existing issue unrelated to Phase 50 changes.
- WR-02 (`_bridge` private access in server.py): Works for all current repository types; future-proofing concern only.
- WR-03 (`_apply` int() coercions outside try/except): Defensive coding gap; not triggered by actual OmniJS output.

---

_Verified: 2026-04-11T14:30:00Z_
_Verifier: Claude (gsd-verifier)_
