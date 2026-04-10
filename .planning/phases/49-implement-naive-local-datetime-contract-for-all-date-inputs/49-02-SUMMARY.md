---
phase: 49-implement-naive-local-datetime-contract-for-all-date-inputs
plan: 02
subsystem: service
tags: [datetime, normalization, local-time, domain-logic]
dependency_graph:
  requires: [49-01]
  provides: [normalize_date_input, local_now-adoption, str-passthrough-payload]
  affects: [service/domain.py, service/payload.py, service/service.py, service/resolve_dates.py]
tech_stack:
  added: []
  patterns: [naive-local normalization, string passthrough, local timezone helper]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/resolve_dates.py
decisions:
  - normalize_date_input placed in domain.py as product decision (D-06)
  - _to_utc_ts treats naive strings as local time (Python astimezone() behavior)
  - resolve_dates str parsing uses "T" presence to detect date-only vs datetime
metrics:
  duration_seconds: 219
  completed: "2026-04-10T21:47:16Z"
  tasks_completed: 2
  tasks_total: 2
---

# Phase 49 Plan 02: Service Layer Adaptations Summary

**One-liner:** normalize_date_input() in domain.py + payload string passthrough + resolve_dates str parsing + local_now() adoption across all pipelines.

## What Was Done

### Task 1: normalize_date_input + payload passthrough + local_now adoption
- **domain.py**: Added `normalize_date_input(value: str) -> str` handling three cases: date-only appends T00:00:00, naive passes through, aware converts to local and strips tzinfo
- **domain.py**: Rewrote `_to_utc_ts` to handle naive strings/datetimes by treating them as local time (removed assertion that required tzinfo)
- **payload.py**: Removed `.isoformat()` calls from `_add_dates_if_set` and `build_add` -- values are already str after domain normalization
- **service.py**: Replaced both `datetime.now(UTC)` with `local_now()` in `_ListTasksPipeline` and `_ListProjectsPipeline`
- **service.py**: Added `_normalize_dates()` step in both `_AddTaskPipeline` and `_EditTaskPipeline` before payload construction
- **Commit:** 1308c2d

### Task 2: Adapt resolve_dates.py to parse str inputs
- Rewrote `_parse_absolute_after` and `_parse_absolute_before` to accept `str` values
- Date-only strings (no "T") produce start-of-day datetime with now's tzinfo
- Naive datetime strings inherit now's tzinfo (local by contract)
- Aware datetime strings pass through as-is
- Removed dead `date` import
- **Commit:** 62296c9

## Deviations from Plan

None - plan executed exactly as written.

## Verification Results

All automated checks passed:
- `normalize_date_input("2026-07-15")` returns `"2026-07-15T00:00:00"`
- `normalize_date_input("2026-07-15T17:00:00")` returns `"2026-07-15T17:00:00"`
- `normalize_date_input("2026-07-15T16:00:00Z")` returns naive local string
- `_to_utc_ts("2026-07-15T17:00:00")` returns float without assertion error
- `_to_utc_ts(None)` returns None
- No `datetime.now(UTC)` in service.py
- No `.isoformat()` in payload.py
- `_parse_absolute_after`/`_parse_absolute_before` accept str without assertion errors
- `local_now()` present in `_ListTasksPipeline` source

## Self-Check: PASSED

All files exist, all commits verified.
