---
phase: 47-cross-path-equivalence-breaking-changes
fixed_at: 2026-04-09T14:15:00Z
review_path: .planning/phases/47-cross-path-equivalence-breaking-changes/47-REVIEW.md
iteration: 1
findings_in_scope: 3
fixed: 3
skipped: 0
status: all_fixed
---

# Phase 47: Code Review Fix Report

**Fixed at:** 2026-04-09T14:15:00Z
**Source review:** .planning/phases/47-cross-path-equivalence-breaking-changes/47-REVIEW.md
**Iteration:** 1

**Summary:**
- Findings in scope: 3
- Fixed: 3
- Skipped: 0

## Fixed Issues

### WR-01: Naive datetime returned by absolute date parser when input lacks timezone

**Files modified:** `src/omnifocus_operator/service/resolve_dates.py`
**Commit:** 4576e29
**Applied fix:** Added tz-inheritance to the full datetime fallback path in both `_parse_absolute_after` and `_parse_absolute_before`. When `datetime.fromisoformat(value)` returns a naive datetime and `now` is tz-aware, the result now gets `now.tzinfo` applied via `dt.replace(tzinfo=now.tzinfo)`. This matches the existing pattern already used for date-only strings.

### WR-02: SQLite seed adapter has latent incorrect sentinel dates for completed/dropped

**Files modified:** `tests/test_cross_path_equivalence.py`
**Commit:** cc0d2c7
**Applied fix:** Changed `_SQLITE_TASK_AVAILABILITY` map to default `dateCompleted` and `dateHidden` to `None` for "completed" and "dropped" entries, instead of `_to_cf_epoch(_MODIFIED)`. The explicit override block (lines 672-686) is the authoritative source for these dates when neutral data supplies them.

### WR-03: `test_errors.py` does not scan `contracts/use_cases/list/tasks.py` for inline errors

**Files modified:** `tests/test_errors.py`
**Commit:** a458139
**Applied fix:** Added `from omnifocus_operator.contracts.use_cases.list import tasks as contracts_list_tasks` import and included `contracts_list_tasks` in the `_ERROR_CONSUMERS` list, ensuring the error consolidation scanner covers that module.

## Skipped Issues

None.

---

_Fixed: 2026-04-09T14:15:00Z_
_Fixer: Claude (gsd-code-fixer)_
_Iteration: 1_
