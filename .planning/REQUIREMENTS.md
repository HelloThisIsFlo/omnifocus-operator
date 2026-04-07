# Requirements: OmniFocus Operator v1.3.2

**Defined:** 2026-04-07
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.3.2 Requirements

Requirements for date filtering milestone. Each maps to roadmap phases.

### Date Filter Models & Validation

- [ ] **DATE-01**: Agent can pass string shortcut or object form for each of 7 date fields (due, defer, planned, completed, dropped, added, modified) — `string | DateFilter` union type
- [ ] **DATE-02**: Shorthand object form accepts exactly one of `this`/`last`/`next` with `[N]unit` duration (d/w/m/y, count defaults to 1)
- [ ] **DATE-03**: Absolute object form accepts one or both of `before`/`after` with ISO8601 datetime, date-only, or `"now"`
- [ ] **DATE-04**: Shorthand and absolute groups mutually exclusive per field — mixing returns educational error
- [ ] **DATE-05**: Zero or negative count in shorthand returns educational error with guidance
- [ ] **DATE-06**: Field-specific shortcuts validated — `"overdue"`/`"soon"` only on `due`, `"any"` only on `completed`/`dropped` ~~, `"none"` only on `due`/`defer`/`planned`~~ (`"none"` scoped out per 45-CONTEXT D-13)
- ~~[ ] **DATE-07**: `"none"` on `added`/`modified` returns educational error (always have values)~~ (scoped out per 45-CONTEXT D-13)
- ~~[ ] **DATE-08**: `"none"` on `completed`/`dropped` returns educational error with guidance about default exclusion behavior~~ (scoped out per 45-CONTEXT D-13)
- [ ] **DATE-09**: When both `before` and `after` specified, `after` must be earlier than `before` — equal date-only values match a single day, reversed values return educational error

### Date Resolution

- [ ] **RESOLVE-01**: `"today"` resolves to calendar-aligned current day (`{this: "d"}`) — works on all 7 fields
- [ ] **RESOLVE-02**: `{this: unit}` resolves to calendar-aligned period boundaries (start through end of day/week/month/year)
- [ ] **RESOLVE-03**: `{last: "[N]unit"}` resolves to midnight N periods ago through now (N full past days + partial today)
- [ ] **RESOLVE-04**: `{next: "[N]unit"}` resolves to now through midnight N+1 periods from now (rest of today + N full future days)
- [ ] **RESOLVE-05**: `"now"` evaluated once at query start — consistent timestamp across all date filters in same query
- [ ] **RESOLVE-06**: Week start configurable via `OPERATOR_WEEK_START` env var (monday default, sunday option) — affects `{this: "w"}` only
- [ ] **RESOLVE-07**: Month ≈ 30 days, year ≈ 365 days (naive approximation, same convention as review_due_within)
- [ ] **RESOLVE-08**: Absolute `before` with date-only resolves to start of next day internally (end-of-day inclusive)
- [ ] **RESOLVE-09**: Absolute `after` with date-only resolves to start of that day (start-of-day inclusive)
- [ ] **RESOLVE-10**: Both `before` and `after` inclusive — `{after: "2026-04-01", before: "2026-04-14"}` includes April 14
- ~~[ ] **RESOLVE-11**: `"overdue"` uses OmniFocus pre-computed `overdue` column (SQL) / urgency enum (bridge) — matches OmniFocus UI~~ (superseded per 45-CONTEXT D-04)
- [ ] **RESOLVE-11** (revised): `"overdue"` resolves to timestamp comparison `effectiveDateDue < now` — both SQL and bridge paths use identical timestamp logic
- ~~[ ] **RESOLVE-12**: `"soon"` uses OmniFocus pre-computed `dueSoon` OR `overdue` columns — includes overdue, matches OmniFocus UI~~ (superseded per 45-CONTEXT D-04/D-06)
- [ ] **RESOLVE-12** (revised): `"soon"` resolves to timestamp comparison using `DueSoonInterval` + `DueSoonGranularity` from OmniFocus Settings table — two modes: rolling (`now + interval`) and calendar-aligned (`midnight_today + interval`). Fallback to `OPERATOR_DUE_SOON_THRESHOLD` env var in bridge-only mode. Fail fast if neither available.

### Query Execution

- [ ] **EXEC-01**: SQL path adds date predicates on effective CF epoch REAL columns for all 7 date fields
- [ ] **EXEC-02**: Bridge fallback applies identical date filtering in-memory using shared resolution logic
- [ ] **EXEC-03**: Using `completed` date filter automatically includes completed tasks in results
- [ ] **EXEC-04**: Using `dropped` date filter automatically includes dropped tasks in results
- [ ] **EXEC-05**: `completed: "any"` includes all completed tasks regardless of completion date
- [ ] **EXEC-06**: `dropped: "any"` includes all dropped tasks regardless of drop date
- [ ] **EXEC-07**: Tasks with no value for a filtered date field are excluded (NULL dates don't match)
- ~~[ ] **EXEC-08**: `due: "none"` / `defer: "none"` / `planned: "none"` returns tasks with IS NULL for that field~~ (scoped out per 45-CONTEXT D-13)
- [ ] **EXEC-09**: Date filters combine with AND with each other and with existing v1.3 base filters
- [ ] **EXEC-10**: Cross-path equivalence tests prove SQL and bridge paths identical for date filters
- [ ] **EXEC-11**: Cross-path test data includes tasks with inherited effective dates (direct NULL, effective non-NULL) for all 5 inheritable fields

### Breaking Changes & Agent Guidance

- [ ] **BREAK-01**: `urgency` filter parameter removed — educational error if agent uses it
- [ ] **BREAK-02**: `completed` field rejects boolean input — educational error guiding to string/object date filter form
- [ ] **BREAK-03**: `COMPLETED` and `DROPPED` removed from `AvailabilityFilter` enum — lifecycle state expressed exclusively via date filters
- [ ] **BREAK-04**: `defer: {after: "now"}` returns guidance hint suggesting `availability: "blocked"`
- [ ] **BREAK-05**: `defer: {before: "now"}` returns guidance hint suggesting `availability: "available"`
- [ ] **BREAK-06**: `availability: "any"` returns educational error suggesting to omit the filter
- [ ] **BREAK-07**: Tool descriptions updated with date filter syntax and availability vs defer distinction
- [ ] **BREAK-08**: `availability: "all"` returns educational error — after trimming, ALL equals the default; guide to `completed: "any"` / `dropped: "any"` for lifecycle inclusion

## Future Requirements

### count_tasks Date Filters

- **COUNT-01**: `count_tasks` gains same 7 date filter parameters as `list_tasks`

### Advanced Date Features

- **ADV-01**: Calendar-aware month/year arithmetic (handling Feb 28/29, variable month lengths)
- **ADV-02**: Non-local timezone support with per-event timezone annotations

## Out of Scope

| Feature | Reason |
|---------|--------|
| `count_tasks` date filters | Removed from v1.3.2 scope — future milestone |
| ~~Due-soon threshold configuration~~ | ~~Using OmniFocus pre-computed columns — matches UI exactly, zero config needed~~ Reinstated: reads `DueSoonInterval` + `DueSoonGranularity` from Settings table (45-CONTEXT D-06/D-07) |
| `"none"` IS NULL filtering | Scoped out of v1.3.2 — niche use case, can be added later if requested (45-CONTEXT D-13) |
| Calendar-aware month/year arithmetic | Explicitly deferred — naive 30d/365d approximation sufficient |
| Timezone handling | Naive local time only — non-local TZ is future improvement |
| NLP date parsing | Anti-feature — structured input only, agents pass structured objects |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DATE-01 | Phase 45 | Pending |
| DATE-02 | Phase 45 | Pending |
| DATE-03 | Phase 45 | Pending |
| DATE-04 | Phase 45 | Pending |
| DATE-05 | Phase 45 | Pending |
| DATE-06 | Phase 45 | Revised (removed "none") |
| ~~DATE-07~~ | ~~Phase 45~~ | Scoped out |
| ~~DATE-08~~ | ~~Phase 45~~ | Scoped out |
| DATE-09 | Phase 45 | Pending |
| RESOLVE-01 | Phase 45 | Pending |
| RESOLVE-02 | Phase 45 | Pending |
| RESOLVE-03 | Phase 45 | Pending |
| RESOLVE-04 | Phase 45 | Pending |
| RESOLVE-05 | Phase 45 | Pending |
| RESOLVE-06 | Phase 45 | Pending |
| RESOLVE-07 | Phase 45 | Pending |
| RESOLVE-08 | Phase 45 | Pending |
| RESOLVE-09 | Phase 45 | Pending |
| RESOLVE-10 | Phase 45 | Pending |
| RESOLVE-11 | Phase 46 | Revised (timestamp, not column) |
| RESOLVE-12 | Phase 46 | Revised (two-mode threshold) |
| EXEC-01 | Phase 46 | Pending |
| EXEC-02 | Phase 46 | Pending |
| EXEC-03 | Phase 46 | Pending |
| EXEC-04 | Phase 46 | Pending |
| EXEC-05 | Phase 46 | Pending |
| EXEC-06 | Phase 46 | Pending |
| EXEC-07 | Phase 46 | Pending |
| ~~EXEC-08~~ | ~~Phase 46~~ | Scoped out |
| EXEC-09 | Phase 46 | Pending |
| EXEC-10 | Phase 47 | Pending |
| EXEC-11 | Phase 47 | Pending |
| BREAK-01 | Phase 47 | Pending |
| BREAK-02 | Phase 47 | Pending |
| BREAK-03 | Phase 47 | Pending |
| BREAK-04 | Phase 47 | Pending |
| BREAK-05 | Phase 47 | Pending |
| BREAK-06 | Phase 47 | Pending |
| BREAK-07 | Phase 47 | Pending |
| BREAK-08 | Phase 47 | Pending |

**Coverage:**
- v1.3.2 requirements: 40 total → 37 active (3 scoped out: DATE-07, DATE-08, EXEC-08)
- Revised: 3 (DATE-06, RESOLVE-11, RESOLVE-12)
- Mapped to phases: 37
- Unmapped: 0

---
*Requirements defined: 2026-04-07*
*Last updated: 2026-04-07 after Phase 45 context discussion*
