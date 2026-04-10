---
created: "2026-04-10T13:48:43.323Z"
title: Rethink timezone handling strategy for date filter inputs
area: contracts
files:
  - src/omnifocus_operator/repository/hybrid/hybrid.py:131-184
  - src/omnifocus_operator/repository/hybrid/query_builder.py:14-69
  - src/omnifocus_operator/service/resolve_dates.py:215-246
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
---

## Problem

A deep dive into how OmniFocus stores dates revealed structural unknowns that affect whether our current timezone strategy is correct — independent of whether we use `AwareDatetime` or `str`.

### How OmniFocus stores dates (two different formats)

**User-set dates** (`dateDue`, `dateToStart`, `datePlanned`): stored as **naive local-time strings** (e.g., `"2026-04-01T10:00:00.000"`). Our code attaches the system timezone and converts to UTC in `_parse_local_datetime`.

**System/effective dates** (`effectiveDateDue`, `effectiveDateToStart`, etc.): stored as **Core Foundation epoch floats** (seconds since 2001-01-01 00:00:00 UTC) — UTC-absolute.

### What the SQL filter actually compares against

`_add_date_conditions` in `query_builder.py` filters against `effective*` columns only. Bounds are converted via `(after_val - _CF_EPOCH).total_seconds()` — the comparison is CF epoch to CF epoch, entirely UTC.

### The date-only input problem

When an agent sends `after: "2026-04-10"` (date-only), the resolver produces **midnight UTC** (`datetime(2026, 4, 10, tzinfo=UTC)`). But the user likely means midnight in their **local timezone**. For a user in +02:00, this is `2026-04-09T22:00:00Z` — a 2-hour discrepancy. The error is silent and bounded by `±14h` depending on timezone.

### Open unknowns about OmniFocus behavior

- **DST adjustment**: When OmniFocus computes `effectiveDateDue`, does it DST-adjust across timezone changes? If a user set "due 9am" and travels to +05:00, does `effectiveDateDue` still represent 9am local (updated) or the original UTC moment?
- **Effective vs. user-set**: `effectiveDateDue` may differ from `dateDue` (e.g., inherited from project). What semantics does it carry?

## Solution

### Questions to answer before deciding

1. Should date-only bounds use UTC midnight or local midnight? (Likely: local midnight — agents reason in user's local time.)
2. Do we need to pass user timezone into the resolver, or is system timezone (`_get_local_tz()`) sufficient?
3. Is `AwareDatetime` the right type for the filter fields, or should we accept only date-only strings and let the server determine timezone semantics internally?

### Options to evaluate

- **Keep `AwareDatetime`** (current direction): agents must send tz-aware datetimes; date-only inputs get midnight UTC. Simple for the server, pushes timezone reasoning to the agent.
- **Localize date-only to system timezone**: date-only → midnight local. Agents don't need to know the server's timezone. Implicit but correct for the common case.
- **Expose timezone in the API**: add a `timezone` field to the query so agents can express intent explicitly. Most correct, most complex.

### Note

This is a strategic decision. The companion todo `2026-04-09-design-timezone-consistency-policy-for-date-filter-inputs.md` covers the immediate fix (aligning `before`/`after` field types with write-side `AwareDatetime` policy). This todo is about whether that approach is the right long-term strategy.

Consider resolving this todo before implementing the `AwareDatetime` fix, or at least before shipping date filter support publicly.
