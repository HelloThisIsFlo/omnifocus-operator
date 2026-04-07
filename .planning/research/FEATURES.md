# Feature Landscape: Date Filtering (v1.3.2)

**Domain:** Date-based task filtering for OmniFocus MCP server
**Researched:** 2026-04-07

## Table Stakes

Features agents and users expect from any date-filtered task query system. Missing = the filter system feels incomplete.

| Feature | Why Expected | Complexity | Notes |
|---------|--------------|------------|-------|
| Before/after absolute ranges | Every task API (Todoist, Asana, TickTick) supports `due_before`/`due_after` with ISO8601 dates | Low | Parameterized SQL, well-understood pattern. Spec: both inclusive — deliberate deviation from half-open convention, justified by agent error rates |
| "Overdue" shortcut | Universal concept — OmniFocus, Todoist, Asana all have it. Agents instinctively reach for it | Low | Sugar for `{before: "now"}` on `due` field |
| "Due soon" with configurable threshold | OmniFocus has this as a global preference (today/24h/2d-5d/1w). Agents need parity | Medium | Must match user's OmniFocus setting. Config mechanism TBD — this is the main complexity |
| Completion date filtering | "What did I finish last week?" is a universal review question | Low | Auto-inclusion of completed tasks is the key design decision — already specified |
| Null date exclusion by default | SQL-natural behavior. Todoist/Asana do the same — tasks without due dates don't appear in "overdue" | Low | `NULL < x` is false in SQL — falls out naturally |
| "Today" shortcut | Every task tool supports "due today". Universal across all 7 date fields | Low | Equivalent to `{this: "d"}` — straightforward calendar alignment |
| Creation/modification date filters | Standard in any queryable system. "What was added recently?" is a common audit pattern | Low | `added`/`modified` always have values — no null handling needed |

## Differentiators

Features that set this date filtering apart from typical task API implementations. Not expected, but valuable for agent workflows.

| Feature | Value Proposition | Complexity | Notes |
|---------|-------------------|------------|-------|
| **Shorthand period syntax** (`{this: "w"}`, `{last: "3d"}`, `{next: "1m"}`) | No other MCP task server offers this. Todoist has natural language; Asana has raw ISO8601 only. This is a structured middle ground — agents don't need to compute dates | Medium | Three distinct resolution semantics (calendar-aligned vs rolling). The `this` vs `last`/`next` asymmetry is well-justified but needs clear implementation |
| **7 date dimensions** (due, defer, planned, completed, dropped, added, modified) | Most APIs expose 2-3 date filters (due, created, modified). 7 covers every OmniFocus date dimension | Medium | Complexity is in the combinatorics — each field x each filter form = many code paths. Shared resolution logic keeps it manageable |
| **`"none"` absence filter** | Unique — "tasks with no due date" is a real review workflow. Most APIs can't express this | Low | `IS NULL` in SQL. Field-specific validation (reject on `added`/`modified`/`completed`/`dropped`) |
| **Educational defer vs availability warnings** | Novel agent guidance — no other MCP server warns agents about semantic confusion between filter types | Low | Two specific patterns detected: `defer: {after: "now"}` and `defer: {before: "now"}`. Cheap to implement, high value |
| **`"soon"` includes overdue** | Deliberate design — OmniFocus native "Due Soon" perspective excludes overdue. This spec includes them because hiding the most urgent items when asking "what needs attention?" is wrong for agents | Low | Single upper bound `due < now + threshold`. Overdue is a subset by math — no special-casing |
| **`"now"` snapshot consistency** | Single timestamp evaluated once per query. Prevents subtle inconsistencies across multiple date filters in the same call | Low | Domain/service concern — snapshot created before filter resolution. Easy to implement, hard to notice when missing |
| **`"any"` for completed/dropped** | Clean replacement for boolean `completed: true`. Symmetric design — `completed: "any"` includes all regardless of date, `completed: {last: "1w"}` scopes to a window | Low | Replaces old boolean, cleaner contract |
| **String-or-object union per field** | Common case terse (`due: "overdue"`), full expressiveness available (`due: {after: "...", before: "..."}`) | Medium | Pydantic discriminated union. Pattern already exists in codebase (MoveAction). Validation must distinguish string shortcuts from object forms |

## Anti-Features

Features to explicitly NOT build in this milestone.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Natural language date parsing ("next Tuesday", "end of month") | Agents can compute ISO8601 themselves. NLP parsing adds a dependency and ambiguity surface. Todoist does this; it's a UI feature, not an API feature | Provide structured shortcuts (`{next: "3d"}`) that cover 90% of natural language intent |
| Calendar-aware month/year arithmetic (Feb 28/29, variable months) | Massive complexity for marginal gain. 30d/365d approximation matches `review_due_within` convention already in codebase | Naive approximation (1m=30d, 1y=365d). Document as known limitation. Future improvement |
| Timezone-aware date handling | OmniFocus stores dates in local time. Per-event timezone annotations exist but are niche. Supporting them adds complexity without clear agent benefit | Naive local time. Log warning if non-local timezone detected |
| "Older than N days" / "newer than N days" shorthand | Redundant with `{last: "Nd"}` and `{before: "<computed date>"}`. Adding more syntactic sugar increases schema surface without new capability | Agents compute absolute ISO8601 timestamps for edge cases |
| Recurring task date projection | "When is this task next due?" requires RRULE evaluation against future dates — different problem from filtering | RRULE is read-only (v1.2.3). Projection is future milestone territory |
| `"soon"` on non-due fields | "Deferred soon" is a real OmniFocus forum request, but the concept only makes semantic sense on `due`. Defer-soon = `defer: {next: "3d"}` covers the use case | Field-specific shortcut restrictions. `"soon"` only on `due` |
| Hour-rolling `last`/`next` | "Last 3 days" means calendar days, not 72 hours. Nobody thinks in rolling hours. Day-snapped boundaries are more intuitive | Snap to midnight on the distant boundary, `now` on the near boundary |
| Exclusive upper bounds | Industry convention (half-open intervals) is developer-friendly but agent-hostile. Tested: agents consistently forgot +1 day with exclusive bounds | Both bounds inclusive. Implementation handles end-of-day internally for date-only `before` values |

## Feature Dependencies

```
Existing v1.3 SQL WHERE builder → Date predicate extension (core dependency)
Existing v1.3 bridge fallback path → In-memory date filter (shared resolution logic)
Existing Patch[T] / UNSET infrastructure → Date filter field modeling (same pattern)
Existing AvailabilityFilter enum pattern → DateFilter union type modeling
Existing MoveAction discriminated-key pattern → {this/last/next} shorthand modeling
Existing review_due_within [N]unit format → Period string parsing (reuse/extend)
Existing cross-path equivalence tests → Date filter equivalence tests (extend)
Existing description centralization → Date filter descriptions in agent_messages/

Due-soon threshold config → "soon" shortcut resolution
"now" snapshot → All shorthand/absolute resolution (must happen first)
Completed/dropped auto-inclusion → Availability filter trimming (coordinated change)
Urgency filter removal → Due date filter replaces urgency semantics
```

## MVP Recommendation

Prioritize (in dependency order):

1. **Date resolution core** — `"now"` snapshot, shorthand period resolution (`this`/`last`/`next`), absolute bound parsing. Shared utility functions used by both SQL and bridge paths. This is the foundation everything else depends on.
2. **SQL date predicates** — Extend WHERE builder with date comparisons. 7 fields x parameterized queries. Most of the milestone's value ships here.
3. **String shortcuts** — `"today"`, `"overdue"`, `"soon"`, `"any"`, `"none"`. Each resolves to the core forms before hitting SQL. `"soon"` depends on threshold config.
4. **Existing filter changes** — Remove `urgency`, convert `completed` boolean to date filter, trim `availability`. Breaking changes that need coordinated implementation.
5. **Bridge fallback** — Same resolution logic, in-memory filtering. Cross-path equivalence tests.
6. **Warnings and validation** — Defer vs availability guidance, field-specific shortcut restrictions, educational errors.

Defer:
- **Due-soon threshold config mechanism decision** can be made during planning (env var is simplest, matches existing patterns like `OPERATOR_WEEK_START`)
- **`count_tasks` extension** — shares code path with `list_tasks`, add after list works

## Complexity Assessment

### Standard patterns (low risk)
- Absolute before/after ranges — parameterized SQL, well-understood
- String shortcuts — resolution to existing forms, lookup table
- Null handling — SQL-natural `IS NULL` / comparison behavior
- `"now"` snapshot — one `datetime.now()` call at service entry
- `"today"`, `"any"`, `"none"` — simple rewrites to core forms

### Novel design choices (medium risk, need careful implementation)
- **`this` vs `last`/`next` asymmetry** — calendar-aligned vs day-snapped rolling. Three different resolution paths. The spec is very precise about boundary behavior (midnight snapping, partial today inclusion). Implementation must match exactly or cross-path equivalence tests will fail.
- **`"soon"` includes overdue** — deviates from OmniFocus native behavior. The math is clean (single upper bound) but agents familiar with OmniFocus may be surprised. Tool descriptions must be crystal clear.
- **Inclusive both-bounds with internal end-of-day** — `before: "2026-03-31"` means `< 2026-04-01T00:00:00` internally. Agent sees "inclusive", implementation uses exclusive-end. This is a documentation/contract boundary — get it wrong and off-by-one errors appear.
- **String-or-object union type** — Pydantic needs to discriminate between `"overdue"` (string) and `{this: "w"}` (object). Pattern exists (MoveAction) but date filters have more variants. Validation error messages must be educational.
- **Completed/dropped auto-inclusion** — using a `completed` date filter must override the default exclusion of completed tasks. This is a cross-cutting concern touching availability filtering and the SQL builder.

### Integration complexity (medium risk)
- **Existing filter changes** — removing `urgency`, converting `completed` boolean, trimming `availability`. These are breaking changes to the agent-facing schema. Agents using `urgency: "overdue"` or `completed: true` will get errors. Need clear migration guidance in error messages.
- **7 fields x multiple forms** — combinatorial test surface. Cross-path equivalence must cover each field with each form (string shortcuts, shorthand periods, absolute ranges, `"none"`). Estimate: 50-80 new test cases.

## Sources

- OmniFocus 4 Reference Manual — perspectives and "Due Soon" threshold configuration
- Todoist filter syntax — `due before:`, `due after:`, `overdue` keyword
- Asana API — `due_on.after`, `due_on.before` parameters, `completed_since`
- Apache Airflow issue #9237 — inclusive vs exclusive range debate in APIs
- API design best practices — half-open intervals `[start, end)` as convention
- OmniFocus forums — "Due Soon" vs "Overdue" are separate status states in perspectives
- Existing codebase — v1.3 SQL builder, MoveAction pattern, `review_due_within` format, Patch[T] infrastructure
