# Quick Task 260411-uf3: Surface preferences warnings to agent responses

## Status: Complete

## What Changed

Wired `OmniFocusPreferences.get_warnings()` into all three pipeline families so preferences warnings flow through to agent-visible result objects.

### Files Modified

| File | Change |
|------|--------|
| `src/omnifocus_operator/service/service.py` | Added 3 `get_warnings()` drain calls |
| `tests/test_preferences_warnings_surfacing.py` | New test file (4 tests) |

### Code Changes

**`_ReadPipeline._resolve_date_filters()` (line 333)**
- Added: `self._warnings.extend(await self._preferences.get_warnings())`
- After `get_due_soon_setting()` call, drains accumulated warnings

**`_AddTaskPipeline` (lines 534, 558, 649)**
- Added: `self._preferences_warnings: list[str] = []` in `execute()`
- Added: `self._preferences_warnings.extend(await self._preferences.get_warnings())` after `_normalize_dates()`
- Modified: `_delegate()` merges `self._preferences_warnings + self._repetition_warnings`

**`_EditTaskPipeline` (lines 660, 701, 955)**
- Added: `self._preferences_warnings: list[str] = []` in `execute()`
- Added: `self._preferences_warnings.extend(await self._preferences.get_warnings())` after `_normalize_dates()`
- Modified: `_all_warnings` assembly includes `self._preferences_warnings`

## Tests

| Test | Status |
|------|--------|
| `test_fallback_warning_surfaces_in_add_task_result` | ✓ Pass |
| `test_fallback_warning_surfaces_in_edit_task_result` | ✓ Pass |
| `test_unknown_due_soon_warning_surfaces_in_list_tasks_result` | ✓ Pass |
| `test_fallback_warning_surfaces_in_list_tasks_result` | ✓ Pass |

**Full suite:** 2020 tests pass, 98.11% coverage

## Requirement Coverage

| Requirement | Status |
|-------------|--------|
| PREF-03: Preferences warnings reach agent responses | ✓ Complete |
