# Phase 45: Date Models & Resolution - Context

**Gathered:** 2026-04-07
**Status:** Ready for planning

<domain>
## Phase Boundary

All date filter input forms can be validated and resolved to absolute DateRange timestamps. This phase delivers: contract types (DateFilter + field-specific shortcut enums), a pure date resolver function, config for week start and due-soon threshold, and educational error messages. No SQL queries, no bridge calls, no pipeline integration (that's Phase 46).

</domain>

<decisions>
## Implementation Decisions

### Date Filter Contract Shape
- **D-01:** DateFilter is a flat model with validators, following the MoveAction/Frequency codebase convention. Five optional keys: `this`, `last`, `next`, `before`, `after`. Model validator enforces mutual exclusion between shorthand group (`this`/`last`/`next`) and absolute group (`before`/`after`). Inherits `QueryModel`, lives in `contracts/use_cases/list/`.
- **D-02:** String shortcuts use field-specific StrEnum/Literal types, NOT plain `str`. Each date field on `ListTasksQuery` has its own shortcut type so the JSON Schema shows agents exactly which shortcuts are valid per field. E.g. `due: Patch[DueDateShortcut | DateFilter]`, `completed: Patch[LifecycleDateShortcut | DateFilter]`, `defer: Patch[Literal["today"] | DateFilter]`.
- **D-03:** Shortcut grouping by field:
  - `due`: overdue, soon, today (richest set)
  - `completed`, `dropped`: any, today
  - `defer`, `planned`, `added`, `modified`: today only

### "soon" / "overdue" Resolution Strategy
- **D-04:** Both resolve to timestamp-based DateRange values, NOT OmniFocus pre-computed columns. This contradicts RESOLVE-11/12 in REQUIREMENTS.md — those requirements assumed column deferral was viable, but the database deep-dive invalidated that approach (`dueSoon` column excludes overdue, `overdue` column is stale on completed tasks, bridge path has no column equivalent).
- **D-05:** `"overdue"` resolves to `DateRange(end=now)` — equivalent to `{before: "now"}` on the `due` field. Simple.
- **D-06:** `"soon"` resolves to `DateRange(end=threshold)` where threshold depends on two OmniFocus Settings table values:
  - `DueSoonInterval` — threshold in seconds (always N × 86400)
  - `DueSoonGranularity` — `0` = rolling from now, `1` = calendar-aligned (snap to midnight)
  - Granularity 0: `threshold = now + interval` (only "24 hours" UI option)
  - Granularity 1: `threshold = midnight_today + interval` (all other options: today, 2-7 days, 1 week)
  - "Today" and "24 hours" share interval=86400 but differ in granularity. At 11 PM, "today" = 1 hour left, "24 hours" = 24 hours left. This distinction is critical.

### Due-Soon Threshold Configuration
- **D-07:** Primary source: read `DueSoonInterval` + `DueSoonGranularity` from OmniFocus Settings table via SQLite (Phase 46 reads, Phase 45 resolver accepts as parameters).
- **D-08:** Fallback: `OPERATOR_DUE_SOON_THRESHOLD` env var for bridge-only mode (no SQLite access). If neither Settings table nor env var available, fail fast — no silent defaults.
- **D-09:** The resolver is a pure function that accepts threshold parameters as input — it does NOT read the database or env vars itself. Config injection is the caller's responsibility (Phase 46 pipeline).

### Resolved Output Boundary (Phase 45 → Phase 46 Contract)
- **D-10:** Resolved date filters become simple `_after`/`_before` datetime fields on `ListTasksRepoQuery`. No nested types, no union types. E.g. `due_after: datetime | None = None`, `due_before: datetime | None = None`. 7 fields × 2 = 14 new fields.
- **D-11:** `"any"` shortcut (completed/dropped only) does NOT produce date fields. It expands the `availability` list to include the lifecycle state — same mechanism as the current `availability: ["completed"]` filter. No resolver logic needed for "any", just availability manipulation in the service pipeline.
- **D-12:** `"overdue"` and `"soon"` resolve to the same `_before` field as any other date filter. No special representation — they're just timestamps.

### "none" Shortcut — Scoped Out
- **D-13:** `"none"` (IS NULL filtering) is removed from v1.3.2 scope. UNSET already means "don't filter on this dimension" and agents rarely need "only tasks WITHOUT a due date." Requirements DATE-06/07/08 and EXEC-08 need updating to remove "none" references. Can be added in a future milestone if requested.

### Week Start Configuration
- **D-14:** `OPERATOR_WEEK_START` env var, default Monday. Same pattern as existing `OPERATOR_*` env vars in the codebase. Affects `{this: "w"}` calendar alignment only.

### Requirements Updates Needed
- **D-15:** RESOLVE-11 and RESOLVE-12 must be rewritten — replace "pre-computed column" approach with timestamp resolution using Settings table values. Add DueSoonGranularity awareness.
- **D-16:** DATE-06, DATE-07, DATE-08, EXEC-08 must be updated to remove all "none" references.

### Claude's Discretion
- Exact StrEnum class names and grouping (how many enum types, shared vs per-field)
- Whether DurationUnit from `contracts/use_cases/list/projects.py` is reused or a new one created for date filters
- Internal structure of the resolver module (single function vs class)
- Error message wording (follows existing educational tone in `agent_messages/errors.py`)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & Requirements
- `.research/updated-spec/MILESTONE-v1.3.2.md` — full milestone spec (NOTE: "soon" threshold approach is superseded by D-04/D-06)
- `.planning/REQUIREMENTS.md` — requirements (NOTE: RESOLVE-11/12, DATE-06/07/08 need updating per D-15/D-16)

### Database Research
- `.research/deep-dives/direct-database-access-date-filters/FINDINGS.md` — database column validation, overdue equivalence proof (570/570)
- `.research/deep-dives/direct-database-access-date-filters/6-due-soon-spike/FINDINGS.md` — **CRITICAL** due-soon spike: DueSoonGranularity discovery, two-mode threshold formula, complete UI-to-database mapping

### Architecture & Conventions
- `docs/model-taxonomy.md` — model naming rules, DateFilter is a `<noun>Filter` (QueryModel), Scenario F is the exact pattern for this phase
- `docs/architecture.md` — three-layer architecture, method object pattern, show-more principle, agent message conventions
- `docs/structure-over-discipline.md` — design philosophy for agent-safe architecture

### Codebase Precedents
- `src/omnifocus_operator/contracts/shared/actions.py` — MoveAction: flat model with exactly-one-key validator (DateFilter follows same pattern)
- `src/omnifocus_operator/models/repetition_rule.py:182-215` — Frequency: flat model with cross-type field validation, `exclude_defaults` handling via parent field_serializer
- `src/omnifocus_operator/contracts/use_cases/list/projects.py:32-74` — ReviewDueFilter + DurationUnit + `_DURATION_PATTERN`: duration parsing precedent
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — current ListTasksQuery/ListTasksRepoQuery: the models being extended
- `src/omnifocus_operator/contracts/use_cases/list/_enums.py` — AvailabilityFilter StrEnum: enum convention for filter shortcuts

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `DurationUnit(StrEnum)` in `contracts/use_cases/list/projects.py` — d/w/m/y enum, may be reusable for DateFilter's shorthand units
- `_DURATION_PATTERN = re.compile(r"^(\d+)([dwmy])$")` — parsing pattern for `[N]unit` format
- `parse_review_due_within()` — duration string parser with educational error messages
- `_expand_review_due()` in service — converts duration to concrete datetime threshold
- `reject_null_filters()` validator — existing pattern for rejecting null on Patch fields

### Established Patterns
- **Flat model + model_validator**: MoveAction (mutual exclusion), Frequency (cross-type field validation) — DateFilter follows this
- **Patch[T] on agent-facing query**: `UNSET` = no filter, value = filter. Date fields follow same convention
- **Service resolves → RepoQuery carries concrete types**: e.g. `project: Patch[str]` → `project_ids: list[str] | None`. Date filters follow: `due: Patch[Shortcut | DateFilter]` → `due_after: datetime | None, due_before: datetime | None`
- **Agent messages as centralized constants**: `agent_messages/errors.py` + `descriptions.py`. All new error/description strings go here
- **StrEnum for filter options**: `AvailabilityFilter(StrEnum)` in `_enums.py` — shortcut enums follow this

### Integration Points
- `ListTasksQuery` in `contracts/use_cases/list/tasks.py` — add 7 date filter fields
- `ListTasksRepoQuery` in same file — add 14 `_after`/`_before` fields
- `_ListTasksPipeline` in `service/service.py` — add date resolution step (calls pure resolver)
- `agent_messages/descriptions.py` — add date filter field descriptions + shortcut docstrings
- `agent_messages/errors.py` — add date filter validation error constants
- `config.py` — add `OPERATOR_WEEK_START` env var reading

</code_context>

<specifics>
## Specific Ideas

- Frequency model precedent: flat model survived the tagged-union alternative because `interval=1` default caused `exclude_defaults` issues. DateFilter has no such issue (no non-None defaults), but the flat pattern is confirmed as codebase convention.
- Show-More principle applies to boundary cases (e.g., `{last: "3d"}` = 3 full past days + partial today). Already captured in milestone spec.
- Field-specific Literal types produce clean JSON Schema — agents see exactly which shortcuts are valid per field, no need to read error messages to learn restrictions.

</specifics>

<deferred>
## Deferred Ideas

- **"none" shortcut (IS NULL filtering)** — scoped out of v1.3.2. Use case: "find tasks without due dates." Can be added in future milestone if requested. Would require `_is_null: bool` fields on RepoQuery.
- **pydantic-settings consolidation** — the codebase has 3-6 `OPERATOR_*` env vars scattered across modules. A `pydantic_settings.BaseSettings` class could centralize them with typed validation. Not blocking for this phase — note as future improvement.

</deferred>

---

*Phase: 45-date-models-resolution*
*Context gathered: 2026-04-07*
