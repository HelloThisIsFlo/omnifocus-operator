---
created: 2026-04-11T10:05:20.916Z
title: Make date filter before/after bounds inclusive for datetime
area: service
files:
  - src/omnifocus_operator/service/resolve_dates.py
---

## Problem

The `before` bound on date filters (due, defer, planned, etc.) appears to use exclusive comparison (`<`) for datetime values. When a task's due date exactly equals the `before` bound, it's excluded from results.

Discovered during phase 49 UAT: filtering with `before: "2026-07-15T18:00:00"` (naive local) excluded a task due at exactly that time (after timezone conversion).

The schema describes both `after` and `before` as inclusive bounds. Date-only bounds already get bumped by one day to be inclusive — datetime bounds need equivalent treatment (bump by one minute or one second).

## Solution

Apply the same inclusive-bound pattern used for date-only values: bump datetime `before` bounds by a small increment (1 minute, matching the existing date bump pattern) so the SQL comparison naturally includes the boundary value.

Files: `resolve_dates.py` — `_parse_absolute_before` / `_parse_absolute_after`
