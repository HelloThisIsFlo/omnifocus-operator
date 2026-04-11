# Technology Stack: Date Filtering (v1.3.2)

**Project:** OmniFocus Operator
**Researched:** 2026-04-07
**Scope:** Stack additions for 7-field date filtering on list_tasks/count_tasks

## TL;DR — No New Dependencies

Everything needed is in Python 3.12 stdlib + existing codebase patterns. Zero new runtime deps. Zero new dev deps.

## What's Needed and Where It Lives

### Date Parsing (Agent Input -> Python datetime)

| Capability | Module | Method | Notes |
|-----------|--------|--------|-------|
| ISO 8601 full datetime | `datetime` | `datetime.fromisoformat()` | Python 3.11+ handles `Z` suffix, timezone offsets, date-only — all natively |
| Date-only (`"2026-03-01"`) | `datetime` | `date.fromisoformat()` or `datetime.fromisoformat()` | Returns `date` or `datetime(2026,3,1,0,0)` respectively |
| `"now"` keyword | n/a | Custom — just `datetime.now()` once per query | Already patterned in `_expand_review_due` |

**Why `datetime.fromisoformat` is sufficient:**
- Python 3.12 target means full ISO 8601 support including `Z`, `+HH:MM`, date-only, datetime
- No need for `dateutil.parser.parse` or any third-party parser
- Handles all formats the spec requires: `"2026-03-01T14:00:00"`, `"2026-03-01"`, `"2026-03-01T14:00:00Z"`, `"2026-03-01T14:00:00+02:00"`
- Confidence: HIGH (verified via Python 3.11 release notes, already used in `_parse_local_datetime`)

### Date Arithmetic (Period Resolution)

| Capability | Module | Method | Notes |
|-----------|--------|--------|-------|
| Day/week offsets | `datetime` | `timedelta(days=N)` | `last/next` day-snapped rolling |
| Month approximation | `datetime` | `timedelta(days=N*30)` | Spec says 1 month ~ 30 days |
| Year approximation | `datetime` | `timedelta(days=N*365)` | Spec says 1 year ~ 365 days |
| Calendar-aligned week start | `datetime` | `datetime.weekday()` → compute Monday offset | `{this: "w"}` — Monday=0 in Python |
| Calendar-aligned month/year | `datetime` | `.replace(day=1)` / `.replace(month=1, day=1)` | `{this: "m"}`, `{this: "y"}` |
| Month-end (days in month) | `calendar` | `calendar.monthrange(year, month)` | Already imported in `service.py` for `_expand_review_due` |

**Key decision: Naive approximation for `last`/`next`, NOT calendar-aware arithmetic.**
- Spec explicitly says: "1 month ~ 30 days, 1 year ~ 365 days. Same convention as `review_due_within`."
- `_expand_review_due` already uses calendar-aware month math for `review_due_within` — but that's a *different* semantic (deadline threshold, needs precision)
- For `last`/`next` rolling windows, the spec chose naive approximation deliberately — "calendar-aware is a future improvement"
- **Only `{this: "m"}` and `{this: "y"}` need calendar alignment** — they snap to calendar boundaries (1st of month, Jan 1), no arithmetic needed, just `.replace()`

### SQLite Date Comparisons

| Capability | How | Notes |
|-----------|-----|-------|
| Compare dates | Raw float comparison (`<`, `<=`, `>=`, `>`) | OmniFocus stores all dates as Core Foundation epoch seconds (float, seconds since 2001-01-01 UTC) |
| Convert Python datetime to CF | `(dt - CF_EPOCH).total_seconds()` | Already patterned in `query_builder.py` line 220 |
| NULL handling | `IS NULL` / `IS NOT NULL` | `"none"` shortcut, null exclusion |
| No SQLite date functions needed | n/a | Do NOT use `datetime()`, `strftime()`, `julianday()` — raw float comparison is simpler and faster |

**Why raw float comparison, not SQLite date functions:**
- OmniFocus dates are already stored as CF epoch floats — they're directly comparable
- `query_builder.py` already converts `datetime` to CF seconds for `review_due_before` (line 220)
- Same pattern extends to all 7 date fields: resolve period to `datetime`, convert to CF float, compare with `<`/`<=`/`>=`/`>`
- SQLite `datetime()` functions would require string conversion — unnecessary overhead and complexity
- Confidence: HIGH (existing proven pattern in the codebase)

### CF Epoch Column Mapping

| Filter field | SQLite column | Storage format | Notes |
|-------------|---------------|----------------|-------|
| `due` | `t.effectiveDateDue` | CF epoch float | Inherited from parent project |
| `defer` | `t.effectiveDateToStart` | CF epoch float | Inherited |
| `planned` | `t.effectiveDatePlanned` | CF epoch float | Inherited |
| `completed` | `t.effectiveDateCompleted` | CF epoch float | Effective (inherited) |
| `dropped` | `t.effectiveDateHidden` | CF epoch float | Effective (inherited) |
| `added` | `t.dateAdded` | CF epoch float | Always present |
| `modified` | `t.dateModified` | CF epoch float | Always present |

**Important:** `dateDue` and `dateToStart` are stored as naive local-time ISO strings (different format!), but the `effective*` columns are CF epoch floats. The filters use `effective*` columns (per spec: "all date filters use effective values").

### Week Start Configuration

| Capability | Module | Method | Notes |
|-----------|--------|--------|-------|
| Read env var | `os` | `os.environ.get("OPERATOR_WEEK_START", "monday")` | Affects `{this: "w"}` only |
| Validate | n/a | Literal check `monday` / `sunday` | Educational error on invalid |
| Compute week start offset | `datetime` | `weekday()` returns 0=Monday, 6=Sunday | Monday: offset=`weekday()`. Sunday: offset=`(weekday()+1)%7` |

**Where to put it:** `omnifocus_operator/config.py` — alongside existing config constants (`DEFAULT_LIST_LIMIT`, etc.). Read once at module load, not per-query.

### "Now" Snapshot

| Capability | Module | Method | Notes |
|-----------|--------|--------|-------|
| Single timestamp for query | `datetime` | `datetime.now()` | Captured once at service layer before filter resolution |
| Pass through pipeline | n/a | Parameter to resolution functions | Not a global — explicit argument |

**Where:** Service layer `_ListTasksPipeline` captures `now = datetime.now()` at the start of `_resolve_date_filters()`, passes it to all period resolution calls. Same pattern as `_expand_review_due` using `datetime.now(UTC)`.

**Timezone question:** `_expand_review_due` uses `datetime.now(UTC)` because CF epoch is UTC-based. Date filters need the same — all comparisons happen in UTC/CF epoch space. The spec says "naive local time" for user-facing semantics, but internal resolution should work in UTC to match column storage. The `{this: "d"}` (today) must compute local midnight boundaries, then convert to UTC for CF comparison.

### Due-Soon Threshold Configuration

| Capability | Module | Method | Notes |
|-----------|--------|--------|-------|
| Read threshold | `os` | `os.environ.get("OPERATOR_DUE_SOON", "3d")` | Matches OmniFocus default |
| Parse threshold | existing | Reuse `_DURATION_PATTERN` from `projects.py` | Same `[N]unit` format |
| Resolve to timedelta | existing | Same logic as `_expand_review_due` | Add to shared utility |

**Supported values per spec:** `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. Parse with existing duration pattern. Store in `config.py`.

## Shared Utility: Period Resolution

The period resolution logic (shorthand -> datetime bounds) should live in a **shared module** used by both the query builder (SQL path) and bridge fallback (in-memory path). This is the cross-path equivalence requirement.

**Recommended location:** `omnifocus_operator/date_filter.py` or `omnifocus_operator/dates/` package
- Input: filter spec (string shortcut or DateFilter object) + `now` timestamp + config (week start, due-soon threshold)
- Output: `DateBounds(after: datetime | None, before: datetime | None, is_null: bool)` — a resolved pair of absolute timestamps
- Both SQL and bridge paths consume the same `DateBounds`, just apply them differently (SQL: WHERE clause params, bridge: Python comparison)

## What NOT to Add

| Don't add | Why |
|-----------|-----|
| `python-dateutil` | `datetime.fromisoformat` handles all needed formats in Python 3.12 |
| `arrow` / `pendulum` | Overkill for period math that's mostly `timedelta` and `.replace()` |
| `dateparser` | Natural language parsing not needed — agent sends structured input |
| SQLite `datetime()` / `strftime()` | Raw CF float comparison is simpler, faster, and already patterned |
| `zoneinfo` beyond existing usage | Already imported in `hybrid.py` for local TZ detection; no new usage needed |
| `calendar` beyond existing usage | Already imported in `service.py`; `monthrange` for end-of-month only |

## Existing Patterns to Reuse

| Pattern | Location | Reuse for |
|---------|----------|-----------|
| CF epoch conversion | `query_builder.py:220` | All 7 date column comparisons |
| Duration parsing `[N]unit` | `projects.py:32-74` | `last`/`next` count+unit parsing (same regex) |
| Duration expansion | `service.py:472-495` | Period resolution (adapt for `last`/`next`/`this`) |
| `_DURATION_PATTERN` regex | `projects.py:32` | Extract to shared location or duplicate (small) |
| Parameterized WHERE builder | `query_builder.py:113-195` | Add date condition branches |
| `Patch[T]` + UNSET pattern | `contracts/base.py` | All 7 date filter fields on ListTasksQuery |
| `_build_availability_clause` | `query_builder.py:95-105` | Pattern for composable SQL clause generation |
| `_CF_EPOCH` constant | `hybrid.py:79`, `query_builder.py:14` | Already in both files where needed |

## Installation

```bash
# No new packages needed
# Existing: uv sync (pulls fastmcp>=3.1.1 only)
```

## Confidence Assessment

| Area | Confidence | Basis |
|------|-----------|-------|
| `datetime.fromisoformat` capabilities | HIGH | Python 3.11+ release notes, already used in codebase |
| CF epoch float comparison in SQLite | HIGH | Existing pattern in query_builder.py, proven in production |
| `timedelta` for day/week arithmetic | HIGH | stdlib, trivial |
| Naive month/year approximation (30d/365d) | HIGH | Spec explicitly chose this, matches `review_due_within` |
| Calendar-aligned `{this: "w/m/y"}` via `.replace()` | HIGH | stdlib datetime, straightforward |
| No new deps needed | HIGH | All capabilities verified in Python 3.12 stdlib |

## Sources

- [Python datetime.fromisoformat — ISO 8601 parsing](https://note.nkmk.me/en/python-datetime-isoformat-fromisoformat/)
- [SQLite Date and Time Functions](https://sqlite.org/lang_datefunc.html)
- Existing codebase: `query_builder.py`, `hybrid.py`, `projects.py`, `service.py`
- MILESTONE-v1.3.2.md spec (month/year approximation decision, week start config)
