---
phase: 45-date-models-resolution
plan: 03
subsystem: service
tags: [date-filter, resolver, pure-function, tdd]
dependency_graph:
  requires: [DateFilter, DueDateShortcut, LifecycleDateShortcut]
  provides: [resolve_date_filter]
  affects: [service]
tech_stack:
  added: []
  patterns: [pure-function-resolver, calendar-aligned-boundaries, naive-duration-approximation]
key_files:
  created:
    - src/omnifocus_operator/service/resolve_dates.py
    - tests/test_resolve_dates.py
  modified: []
decisions:
  - "Date-only 'before' resolves to start of next day (RESOLVE-08 inclusive) via _is_date_only length+T check"
  - "Calendar-aligned {this: m/y} uses exact boundaries; naive 30d/365d only for {last/next: m/y}"
  - "'today' shortcut delegates to _resolve_this('d') — single code path for both forms"
  - "week_start=0 default (Monday) passed through to _resolve_this even for 'today' (no effect on day unit)"
metrics:
  duration: ~4m
  completed: 2026-04-07T22:29:44Z
  tasks_completed: 1
  tasks_total: 1
  test_count: 40
  test_pass: 40
requirements_covered: [RESOLVE-01, RESOLVE-02, RESOLVE-03, RESOLVE-04, RESOLVE-05, RESOLVE-07, RESOLVE-08, RESOLVE-09, RESOLVE-10]
---

# Phase 45 Plan 03: Date Filter Resolver Summary

Pure resolve_date_filter function converting all valid DateFilter/shortcut input forms to absolute (after, before) datetime tuples, with calendar-aligned periods, configurable week start, and due-soon threshold support.

## Task Results

| Task | Name | Commit | Key Files |
|------|------|--------|-----------|
| RED | Failing tests for resolve_date_filter | 275e1f4 | tests/test_resolve_dates.py |
| GREEN | Implement resolve_date_filter | c2eb838 | src/omnifocus_operator/service/resolve_dates.py |

## Implementation Details

### resolve_date_filter Signature
- `value: StrEnum | DateFilter` — accepts both string shortcuts and DateFilter objects
- `field_name: str` — used in error messages (e.g., "any" on "completed")
- `now: datetime` — caller-provided timestamp for consistency (RESOLVE-05)
- `week_start: int = 0` — Python weekday value (0=Monday, 6=Sunday)
- `due_soon_interval/granularity` — optional, required only when "soon" is used

### Resolution Paths
- **String shortcuts**: today (midnight-to-midnight), overdue (None, now), soon (configurable threshold)
- **{this: d/w/m/y}**: Calendar-aligned — day/week/month/year boundaries. Month/year use exact calendar boundaries (first-of-month to first-of-next-month)
- **{last: duration}**: Rolling past — N days/weeks/months/years ago midnight through now. Naive 30d/365d for m/y (RESOLVE-07)
- **{next: duration}**: Rolling future — now through midnight(now) + delta + 1 day. Formula: "rest of today + N full periods"
- **Absolute {before/after}**: date-only before = start of next day (RESOLVE-08), date-only after = start of that day (RESOLVE-09), datetime = exact, "now" = passthrough

### Key Implementation Details
- `_is_date_only()` detects date-only strings via `len==10 and no 'T'` — avoids Python 3.12+ `datetime.fromisoformat()` accepting date-only strings
- "any" shortcut raises ValueError — it's an availability expansion, not a date filter (D-11)
- "soon" without both config params raises ValueError with educational message (T-45-07 mitigation)
- Duration parsing mirrors `_DATE_DURATION_PATTERN` from `_date_filter.py` — count defaults to 1

## Test Coverage

40 tests organized by input form:
- TestTodayShortcut (4): due, completed, midnight, end-of-day edge cases
- TestOverdueShortcut (1): (None, now)
- TestSoonShortcut (5): calendar-aligned, rolling, missing config (3 variants)
- TestAnyShortcut (1): raises ValueError
- TestThisDay (1), TestThisWeek (3), TestThisMonth (3), TestThisYear (1): calendar-aligned
- TestLastDuration (5): 3d, w, 1w, 1m, 1y
- TestNextDuration (4): 2d, w, 1m, 1y
- TestAbsoluteBefore (4), TestAbsoluteAfter (4), TestAbsoluteBoth (2): date-only, datetime, "now"
- TestPureFunctionContract (2): determinism, now-sensitivity

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed date-only detection for Python 3.12+ fromisoformat behavior**
- **Found during:** GREEN phase
- **Issue:** `datetime.fromisoformat("2026-04-14")` succeeds in Python 3.12+ returning `datetime(2026, 4, 14, 0, 0)`, bypassing the date-only path. The `_parse_absolute_before` function returned midnight of the same day instead of next day.
- **Fix:** Added `_is_date_only()` helper that checks `len==10 and 'T' not in value` before attempting datetime parsing.
- **Files modified:** src/omnifocus_operator/service/resolve_dates.py
- **Commit:** c2eb838

**2. [Deviation] Plan's {this: "w"} resolution table has incorrect dates**
- **Found during:** RED phase
- **Issue:** Plan says `{this: "w"} week_start=monday -> (2026-04-07T00:00, 2026-04-14T00:00)` but Apr 7 2026 is Tuesday, not Monday. The correct Monday start of that week is Apr 6.
- **Impact:** Tests use correct calendar dates (Apr 6 - Apr 13 for Monday start). Implementation is correct per the formula `(weekday - week_start) % 7`.

## Verification

- `uv run pytest tests/test_resolve_dates.py -x -q` -- 40 passed
- `uv run pytest -x -q` -- 1777 passed, 97.80% coverage

## Self-Check: PASSED
