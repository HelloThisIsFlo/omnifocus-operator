# Domain Pitfalls: Date Filtering for OmniFocus Operator

**Domain:** Adding date filtering to an existing MCP task management server
**Researched:** 2026-04-07
**Confidence:** HIGH (informed by codebase analysis, not web research)

## Critical Pitfalls

Mistakes that cause wrong results, data loss, or rewrites.

### Pitfall 1: Two Date Storage Formats in the Same Table

**What goes wrong:** The SQLite `Task` table stores dates in TWO incompatible formats:
- **TEXT (naive local ISO 8601):** `dateDue`, `dateToStart`, `datePlanned` -- e.g. `"2026-04-01T10:00:00.000"`
- **REAL (CF epoch float, UTC):** `dateCompleted`, `dateHidden`, `dateAdded`, `dateModified`, `effectiveDateDue`, `effectiveDateToStart`, `effectiveDatePlanned`, `effectiveDateCompleted`, `effectiveDateHidden`

A single date comparison function won't work for both. Applying a CF epoch comparison to a TEXT column or vice versa returns wrong results silently -- SQLite won't error, it'll just compare nonsense values.

**Why it happens:** Easy to assume "all dates in one table = one format." The codebase already has `_parse_timestamp` (CF epoch) and `_parse_local_datetime` (naive local) but the query builder hasn't needed to compare dates in SQL WHERE clauses until now.

**Consequences:** Silent wrong results. Tasks appear/disappear incorrectly. Cross-path equivalence tests might not catch it if test data doesn't exercise the format boundary.

**Prevention:**
- Map each of the 7 filter fields to its exact SQLite column AND format at the column-mapping level
- `due`/`defer`/`planned` filter on `effective*` columns (REAL, CF epoch) -- NOT the TEXT columns
- `completed` = `effectiveDateCompleted` (REAL), `dropped` = `effectiveDateHidden` (REAL), `added` = `dateAdded` (REAL), `modified` = `dateModified` (REAL)
- All 7 filter columns are REAL (CF epoch). The TEXT columns (`dateDue`, `dateToStart`, `datePlanned`) are the direct-only values -- the effective columns are what filters need. This simplifies the query builder: one format for all comparisons.

**Detection:** Cross-path equivalence tests with tasks that have inherited dates (effective != direct). If filtering by effective due date returns different results on SQL vs bridge, the wrong column or format is being used.

### Pitfall 2: "now" Evaluated Multiple Times

**What goes wrong:** If `datetime.now()` is called once per date filter clause instead of once per query, filters on the same query can see different timestamps. In a pathological case: `due: {before: "now"}` and `defer: {after: "now"}` could use timestamps milliseconds apart, creating impossible-to-reproduce edge cases where a task appears in one filter's window but not another's.

**Why it happens:** Natural to call `datetime.now()` inline wherever "now" appears in filter resolution. With 7 date fields, that's 7 potential evaluation points.

**Consequences:** Subtle inconsistency. A query with `due: {before: "now"}, completed: {after: "now"}` could theoretically return different results depending on execution timing. Hard to debug because it's timing-dependent.

**Prevention:**
- Snapshot `now` once at the service layer, before any filter resolution begins
- Pass it as a parameter to every date resolution function
- The milestone spec explicitly calls this out: "now is evaluated once at query start"

**Detection:** Unit test that mocks time, resolves two date filters with `"now"`, and asserts identical timestamps.

### Pitfall 3: Off-by-One on Date-Only `before` Boundary

**What goes wrong:** `before: "2026-03-31"` should include ALL of March 31. But if resolved naively to `2026-03-31T00:00:00`, it only includes tasks due at exactly midnight -- everything else on March 31 is excluded.

**Why it happens:** The spec says both `before` and `after` are "inclusive" but date-only values need different internal resolution:
- `after: "2026-03-01"` -> `>= 2026-03-01T00:00:00` (start of day)
- `before: "2026-03-31"` -> `< 2026-04-01T00:00:00` (start of NEXT day, exclusive internally)

This asymmetry is the most common date filtering bug in every system that does it.

**Consequences:** Missing tasks at the boundary. An agent asking for "tasks due before March 31" misses everything due during March 31. This is the exact error class the spec was designed to prevent.

**Prevention:**
- Implement `before` with date-only as `< start_of_next_day` internally
- Test with a task due at `2026-03-31T23:59:00` and `before: "2026-03-31"` -- must be included
- Test with a task due at `2026-04-01T00:00:00` and `before: "2026-03-31"` -- must be excluded
- Both SQL path and bridge path must use identical resolution

**Detection:** Boundary test cases at day transitions. This needs dedicated test coverage, not just happy-path tests.

### Pitfall 4: `completed`/`dropped` Auto-Inclusion Changes Default Availability

**What goes wrong:** The default availability filter is `[available, blocked]` -- completed and dropped tasks are excluded. When an agent uses `completed: {last: "1w"}`, those tasks must be included in results despite the default availability filter excluding them. If the implementation adds the date clause without adjusting availability, zero results are returned.

**Why it happens:** The availability filter and date filters operate independently in the current query builder. They're combined with AND. Adding `completed IS NOT NULL AND completed > X` while availability says `completed IS NULL` creates a contradiction.

**Consequences:** `completed: "any"` or `completed: {last: "1w"}` returns zero results. The most confusing possible behavior -- the filter "works" but finds nothing.

**Prevention:**
- When `completed` date filter is present: auto-include `Availability.COMPLETED` in the availability list
- When `dropped` date filter is present: auto-include `Availability.DROPPED`
- This modification happens at the service layer, before the repo query is built
- The agent should NOT need to manually pass `availability: ["available", "blocked", "completed"]` -- that's terrible UX

**Detection:** Test `completed: "any"` with default availability -- must return completed tasks. Test `dropped: {last: "1w"}` without explicit availability -- must return dropped tasks.

### Pitfall 5: Cross-Path Equivalence Drift with Date Arithmetic

**What goes wrong:** The SQL path computes date boundaries as CF epoch floats and compares in SQL. The bridge path computes boundaries as Python datetime objects and compares in memory. If these two paths use even slightly different arithmetic (e.g., different rounding, different midnight calculation, different month approximation), cross-path equivalence breaks.

**Why it happens:** Two codepaths implementing the same logic independently. The existing 32 cross-path tests don't cover date filtering yet. New date-specific tests must be added.

**Consequences:** Bridge fallback returns different results than SQL path. Silent correctness bug that only manifests when OmniFocus SQLite is unavailable.

**Prevention:**
- Share a single date resolution module that converts filter expressions to `(lower_bound, upper_bound)` pairs as Python datetimes
- SQL path converts these bounds to CF epoch floats for the WHERE clause
- Bridge path uses the same bounds for Python comparisons
- The resolution logic is tested once; the paths only differ in how they apply the resolved bounds
- Add cross-path equivalence tests for every date filter variant: shorthand, absolute, string shortcuts

**Detection:** Parametrized cross-path tests with tasks at boundary timestamps. If any test passes on one path but fails on the other, the resolution is diverging.

## Moderate Pitfalls

### Pitfall 6: NULL Handling in SQL Date Comparisons

**What goes wrong:** `effectiveDateDue < ?` in SQL returns NULL (not false) when `effectiveDateDue` is NULL. SQLite treats NULL as falsy in WHERE, so NULL-dated tasks are correctly excluded. But `effectiveDateDue IS NOT NULL` must be explicit in some compound clauses, and forgetting it in OR expressions can include NULL rows.

**Prevention:**
- The "null dates excluded" rule is SQL-natural for simple comparisons -- no extra clause needed for basic `column < ?` or `column > ?`
- For `"none"` shortcut: explicit `column IS NULL`
- For `"any"` shortcut: no date restriction, just the auto-inclusion of the availability state
- Be cautious with OR clauses and aggregate functions where NULL propagation differs

### Pitfall 7: `{last: "1w"}` vs `{this: "w"}` Confusion in Implementation

**What goes wrong:** `{this: "w"}` is calendar-aligned (Monday 00:00 to next Monday 00:00). `{last: "1w"}` is rolling (7 days ago midnight to now). If the implementation confuses these or shares code that conflates them, ranges are wrong.

**Prevention:**
- Implement `this` and `last`/`next` as completely separate code paths
- `this` uses calendar alignment (find start-of-period, find end-of-period)
- `last`/`next` use day arithmetic (N days * 86400 seconds from midnight)
- Test on a Wednesday: `{this: "w"}` should start Monday; `{last: "1w"}` should start 7 days ago

### Pitfall 8: Month/Year Approximation Drift

**What goes wrong:** `{last: "1m"}` = 30 days. `{last: "1y"}` = 365 days. This is documented as intentional approximation. But if someone filters `{last: "1m"}` on March 3, they get Feb 1 (30 days back) -- but February only has 28 days, so they're actually getting 3 days of January too. Not a bug per se, but could confuse users expecting calendar-month alignment.

**Prevention:**
- Document the approximation clearly in tool descriptions (the spec already does)
- Use `{this: "m"}` for calendar-month alignment
- This is a design choice, not a bug -- just ensure consistency between SQL and bridge paths

### Pitfall 9: Breaking Change -- Removing `urgency` and `completed` Boolean Filters

**What goes wrong:** Agents already using `urgency: "overdue"` or `completed: true` get validation errors after the upgrade. This is a breaking change for any agent that learned the v1.3 API.

**Why it happens:** The spec explicitly removes these filters. But existing agents (or cached tool schemas) won't know about the change.

**Prevention:**
- Return educational errors that guide to the replacement: `"urgency filter removed in v1.3.2. Use due: 'overdue' for overdue tasks, due: 'soon' for due-soon tasks."`
- Same for `completed: true` -> `"completed boolean removed. Use completed: 'any' to include all completed tasks, or completed: {last: '1w'} for a date range."`
- These are validation errors, not silent breakage -- the agent learns the new API on first call

**Detection:** Explicit test that the old filter names produce educational errors, not crashes.

### Pitfall 10: `availability` Trimming -- Removing `completed`/`dropped` Values

**What goes wrong:** The spec says `availability` is trimmed to `available`/`blocked` only. But `AvailabilityFilter` currently has `COMPLETED`, `DROPPED`, and `ALL`. Removing these changes the schema. An agent passing `availability: ["completed"]` should get an educational error, not a generic validation failure.

**Prevention:**
- `availability: "completed"` -> educational error: `"Use completed date filter (e.g., completed: 'any') to include completed tasks."`
- `availability: "dropped"` -> same pattern
- `availability: "ALL"` -> educational error: `"Use 'available' and 'blocked'. To include completed/dropped tasks, use their date filters."`
- Update the `AvailabilityFilter` enum to only have `AVAILABLE` and `BLOCKED`, with a model validator that catches old values and returns guidance

**Detection:** Test old enum values produce the right educational error message.

### Pitfall 11: Timezone/DST Edge Cases in `_parse_local_datetime`

**What goes wrong:** The existing `_parse_local_datetime` uses `_LOCAL_TZ` (system timezone) to convert naive local timestamps. During DST transitions, a time like `2026-03-08T02:30:00` (US spring forward) doesn't exist. Python's `replace(tzinfo=...)` handles this, but the behavior may not match what OmniFocus intended.

**Prevention:**
- The spec says "naive local time, system timezone" -- this is the correct approach
- DST ambiguity: OmniFocus stores the time it displayed to the user. If the user set a due date at 2:30 AM during spring forward, OmniFocus would have shown a different time. The naive conversion is correct.
- Don't try to be smarter than the source data
- Test with a date during DST transition to verify no crashes

## Minor Pitfalls

### Pitfall 12: `{next: "Nd"}` Upper Bound Off-by-One

**What goes wrong:** The spec says `{next: "3d"}` = now through midnight 4 days from now. The "4" is N+1 because today counts as a partial bonus day. Easy to implement as midnight N days from now (missing the +1).

**Prevention:** The spec has explicit examples:
- Wednesday at 14:00, `{next: "3d"}` -> `>= now, < Sunday 00:00` (Wed partial + Thu + Fri + Sat = 4 calendar days)
- Implement as: upper bound = `midnight(today + N + 1 days)`
- Test against the spec's concrete examples table

### Pitfall 13: `"soon"` Threshold Not Configured -> Silent Default

**What goes wrong:** If the due-soon threshold isn't configured, the system needs a sensible default. Using OmniFocus's default (2 days) without documentation could confuse users who changed their OmniFocus preference.

**Prevention:**
- Default to a reasonable value (3 days?) and document it
- Log a warning on startup if the threshold isn't explicitly configured
- The spec notes this is TBD -- decide during planning

### Pitfall 14: CF Epoch Conversion Precision

**What goes wrong:** Converting between Python datetime and CF epoch float can lose precision due to floating-point arithmetic. For date comparisons at day boundaries (midnight), this is unlikely to matter. But for "now" comparisons, a task completed at exactly the boundary timestamp could be included/excluded based on float rounding.

**Prevention:**
- Use `(dt - _CF_EPOCH).total_seconds()` which is standard and precise enough for second-level comparisons
- Don't compare with `==` on floats -- always use `<` or `>=`
- The existing codebase already uses this pattern correctly (see `review_due_before` in query builder)

### Pitfall 15: Test Data Without Inherited Dates

**What goes wrong:** Cross-path equivalence tests currently don't have tasks with inherited dates. The neutral test data sets `effectiveDateDue` etc. to NULL on all test tasks. Date filter tests that only use direct dates miss the primary use case -- effective/inherited dates.

**Prevention:**
- Add test tasks with projects that have due/defer dates, and child tasks that inherit them
- Test that filtering by `due: "overdue"` picks up a task with no direct due date but an inherited one from its project
- This is the highest-value test scenario for date filtering correctness

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Date model/contract | #3 (off-by-one before), #12 (next N+1) | Implement resolution as a shared module, test against spec's concrete examples table |
| SQL WHERE clauses | #1 (two formats), #6 (NULL handling) | All 7 filter columns are CF epoch REAL -- verify column mapping early |
| Service layer integration | #2 (now snapshot), #4 (auto-inclusion) | `now` passed as param; availability mutation at service boundary |
| Cross-path equivalence | #5 (arithmetic drift), #15 (test data) | Shared resolution module; add inherited-date test tasks |
| Breaking changes | #9 (urgency removal), #10 (availability trim) | Educational errors with migration guidance |
| Bridge fallback | #5 (drift), #7 (this vs last confusion) | Same resolution functions for both paths |
| Configuration | #13 (soon threshold) | Default + startup warning |
| Boundary conditions | #3, #11 (DST), #12, #14 (float precision) | Explicit boundary tests at day edges |

## Sources

- Codebase analysis: `repository/hybrid/hybrid.py` (date parsing, column formats)
- Codebase analysis: `repository/hybrid/query_builder.py` (existing filter infrastructure)
- Codebase analysis: `repository/bridge_only/bridge_only.py` (bridge filter path)
- Codebase analysis: `tests/test_cross_path_equivalence.py` (existing cross-path tests, neutral test data)
- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.2.md`
- Codebase analysis: `contracts/use_cases/list/tasks.py` (current query model, Patch semantics)
