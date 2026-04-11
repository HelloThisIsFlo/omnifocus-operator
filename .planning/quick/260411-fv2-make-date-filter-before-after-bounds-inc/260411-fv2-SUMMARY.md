# Quick Task 260411-fv2: Summary

**Task:** Make date filter before/after bounds inclusive for datetime
**Status:** Complete
**Date:** 2026-04-11

## Commits

| Hash | Message |
|------|---------|
| 89481da | feat(quick-260411-fv2-01): bump datetime before bounds by +1 minute |
| cfa9de8 | docs(quick-260411-fv2-01): document datetime +1 minute bump in architecture and docstring |

## Changes

- `src/omnifocus_operator/service/resolve_dates.py` — `_parse_absolute_before()` adds `+ timedelta(minutes=1)` to both naive and aware datetime return paths
- `tests/test_resolve_dates.py` — updated 2 existing assertions (18:00 → 18:01), added `test_before_datetime_naive`
- `docs/architecture.md` — date filter bounds section now documents both +1 day (date-only) and +1 minute (datetime) bumps

## Verification

- `tests/test_resolve_dates.py`: all pass
- Full suite: 1960 tests, 98% coverage, zero downstream breakage
