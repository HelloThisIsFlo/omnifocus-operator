# Phase 47: Cross-Path Equivalence & Breaking Changes - Context

**Gathered:** 2026-04-08
**Status:** Ready for planning

<domain>
## Phase Boundary

SQL and bridge paths produce identical date filter results, availability filter is trimmed and renamed, lifecycle inclusion is expressed exclusively via date filters, and tool descriptions are updated. This is the final phase of milestone v1.3.2. No new date filter forms, no new resolution logic, no count_tasks.

</domain>

<decisions>
## Implementation Decisions

### AvailabilityFilter Trimming & Remaining Shorthand
- **D-01:** Remove `COMPLETED`, `DROPPED`, and `ALL` from `AvailabilityFilter` enum. Three values remain: `AVAILABLE`, `BLOCKED`, `REMAINING`.
- **D-02:** `REMAINING` = `AVAILABLE + BLOCKED`. Semantic shorthand borrowed from the OmniFocus UI. It names the default set of active (non-lifecycle) tasks.
- **D-03:** `REMAINING` is the **default** when the availability filter is omitted (`UNSET`). Same behavior as the current `[AVAILABLE, BLOCKED]` default, but now the shorthand has a name.
- **D-04:** Warnings for redundant combinations:
  - `["available", "remaining"]` -> warn: remaining already includes available
  - `["blocked", "remaining"]` -> warn: remaining already includes blocked
  - Empty list `[]` -> **accepted**. Returns no active tasks. Combined with `completed: "all"`, returns only completed tasks. This is the canonical way to get lifecycle-only results.
- **D-05:** `availability: "any"` -> Pydantic rejects (not a valid enum value). No custom interception needed — project is pre-release, no backward compatibility concern.

### Lifecycle Inclusion via Date Filters
- **D-06:** Completed/dropped date filters are the **sole gate** for lifecycle inclusion. Using them auto-includes the lifecycle state alongside the agent's availability selection. This is the only way to see completed/dropped tasks.
- **D-07:** Rename shortcut: `"any"` -> `"all"` on completed/dropped. `completed: "all"` reads as "all completed tasks regardless of date." Update `LifecycleDateShortcut` enum accordingly.
- **D-08:** The lifecycle expansion behavior is inherent and must be documented clearly in per-field descriptions. No special runtime warning needed for combining availability + completed — the description makes it obvious.
- **D-09:** No backward compatibility interception needed. No dummy fields, no migration errors, no `urgency` filter interception. The project is pre-release with zero external users. `extra="forbid"` handles unknown fields; Pydantic type validation handles wrong types.

### Defer Hint Mechanism
- **D-10:** Detect `defer: {after: "now"}` and `defer: {before: "now"}` in `DomainLogic.resolve_date_filters()` in `domain.py`. Same placement as the existing "soon without due_soon_setting" fallback pattern.
- **D-11:** Detection inspects the raw `DateFilter` object before resolution: `isinstance(value, DateFilter) and value.after == "now"` (or `.before == "now"`).
- **D-12:** Hints are appended to the warnings list and flow through the existing `ListResult.warnings` array. Query still executes — these are guidance, not errors.
- **D-13:** Two new warning constants in `agent_messages/warnings.py`:
  - `defer: {after: "now"}` -> "Tip: This shows tasks with a future defer date. For all unavailable tasks regardless of reason, use availability: 'blocked'. Defer is one of four blocking reasons."
  - `defer: {before: "now"}` -> "Tip: This shows tasks whose defer date has passed. For all currently available tasks, use availability: 'available'."

### Cross-Path Equivalence Tests
- **D-14:** Extend neutral test dict with explicit `effective_*` fields separate from direct fields. Inherited case = `due: None, effective_due: <value>`. No implicit sync — every field is spelled out.
- **D-15:** Representative coverage, not exhaustive. Test `due` with all filter forms (shortcuts, shorthand, absolute) + each other field with one representative form. The resolution logic is shared — real risk is adapter bugs and column mapping errors.
- **D-16:** Test data must include parent-child hierarchies where tasks inherit effective dates from container projects (task has no direct due date, but `effectiveDateDue` is set from parent).

### Tool Description Updates — Verbatim Text

**D-17:** Use these descriptions verbatim. The agent-facing descriptions are drafted to match the existing `descriptions.py` philosophy: teach semantics, not just syntax. Per-field descriptions explain *when* to use the filter and *what to watch out for*. Tool-level description covers cross-cutting concerns only.

**D-17a: LIST_TASKS_TOOL_DOC addition** (append to existing tool doc):

```python
"\n"
"Filters use effective (inherited) values -- tasks inherit dates and flags\n"
"from parent projects/tasks. The effective* output fields show these values.\n"
"\n"
"completed/dropped filters include those lifecycle states in results\n"
"(excluded by default). All other filters only restrict.\n"
"\n"
"availability vs defer: 'available'/'blocked' answers 'can I act on this?'\n"
"(covers all four blocking reasons). defer filter answers 'what becomes\n"
"available when?' (timing only -- one of four blocking reasons)."
```

**D-17b: Per-field date filter descriptions** (replace existing constants):

```python
DUE_FILTER_DESC = (
    "Filter by due date (effective/inherited). "
    "'overdue' = due before now. "
    "'soon' = due within threshold (includes overdue). "
    "'today' = due today. Or use DateFilter for range/shorthand."
)

DEFER_FILTER_DESC = (
    "Filter by defer date (effective/inherited). "
    "For timing questions ('what becomes available this week?'), "
    "not availability state -- use availability: 'blocked' for all unavailable tasks. "
    "'today' = deferred to today. Or use DateFilter for range/shorthand."
)

PLANNED_FILTER_DESC = (
    "Filter by planned date (effective/inherited). "
    "'today' = planned for today. Or use DateFilter for range/shorthand."
)

COMPLETED_FILTER_DESC = (
    "Filter by completion date. Includes completed tasks in results "
    "(excluded by default). 'all' = every completed task regardless of date. "
    "'today' = completed today. Or use DateFilter for a date range."
)

DROPPED_FILTER_DESC = (
    "Filter by drop date. Includes dropped tasks in results "
    "(excluded by default). 'all' = every dropped task regardless of date. "
    "'today' = dropped today. Or use DateFilter for a date range."
)

ADDED_FILTER_DESC = (
    "Filter by date added. 'today' = added today. "
    "Or use DateFilter for range/shorthand."
)

MODIFIED_FILTER_DESC = (
    "Filter by date modified. 'today' = modified today. "
    "Or use DateFilter for range/shorthand."
)
```

**D-17c: Availability filter field description** (new or updated constant):

```python
AVAILABILITY_FILTER_DESC = (
    "Which lifecycle states to include. "
    "'remaining' (default) = available + blocked. "
    "Empty list [] = no active tasks (combine with completed/dropped filters for lifecycle-only results). "
    "Completed/dropped tasks are included via their own date filters, not here."
)
```

### Claude's Discretion
- Exact placement of the tool-level description addition (within the existing `LIST_TASKS_TOOL_DOC` string)
- Internal `_expand_remaining()` implementation (how REMAINING expands to [AVAILABLE, BLOCKED])
- Warning message wording for redundant availability combos (follows existing patterns in `warnings.py`)
- Cross-path test class organization and parametrization strategy
- Whether to update `LIST_PROJECTS_TOOL_DOC` with the same effective-date note (projects also have effective dates)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone & Requirements
- `.research/updated-spec/MILESTONE-v1.3.2.md` -- full milestone spec (NOTE: "breaking changes" framing is misleading -- project is pre-release, treat all changes as cleanups/new features, no migration paths)
- `.planning/REQUIREMENTS.md` -- requirements EXEC-10, EXEC-11, BREAK-01 through BREAK-08 (NOTE: BREAK-01/02 are moot -- urgency filter never existed, completed boolean never existed. No interception needed. BREAK-03/06/08 = enum cleanup. BREAK-04/05 = defer hints. BREAK-07 = description updates.)

### Architecture & Conventions
- `docs/architecture.md` -- three-layer architecture, method object pattern, show-more principle, product decisions vs plumbing
- `docs/model-taxonomy.md` -- model naming conventions (if enum/model changes needed)

### Phase 45-46 Outputs (Upstream Dependencies)
- `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` -- DateFilter contract model
- `src/omnifocus_operator/contracts/use_cases/list/_enums.py` -- AvailabilityFilter (to be trimmed), DueDateShortcut, LifecycleDateShortcut (to rename ANY->ALL)
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` -- ListTasksQuery (7 date fields), ListTasksRepoQuery (14 _after/_before fields)
- `src/omnifocus_operator/service/resolve_dates.py` -- pure date resolver
- `src/omnifocus_operator/service/domain.py` -- DomainLogic.resolve_date_filters() (add defer hint detection here)

### Agent Messages
- `src/omnifocus_operator/agent_messages/descriptions.py` -- all agent-facing descriptions (update per D-17)
- `src/omnifocus_operator/agent_messages/warnings.py` -- warning constants (add defer hints per D-13, add availability redundancy warnings per D-04)
- `src/omnifocus_operator/agent_messages/errors.py` -- error constants

### Cross-Path Equivalence
- `tests/test_cross_path_equivalence.py` -- existing 23 cross-path tests, seed adapters, `cross_repo` fixture pattern

### Database Research
- `.research/deep-dives/direct-database-access-date-filters/FINDINGS.md` -- column type map, inheritance rates, null distribution

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `cross_repo` fixture in `test_cross_path_equivalence.py` -- creates both BridgeOnlyRepository and HybridRepository from same neutral data
- Seed adapters (`_seed_bridge_repo`, `_seed_sqlite_repo`) -- translate neutral dicts to bridge/SQLite formats
- `DomainLogic.resolve_date_filters()` in `domain.py` -- already has "soon" fallback warning pattern; defer hints follow same shape
- `_expand_availability()` in `domain.py` -- existing availability expansion logic; adapt for REMAINING shorthand
- Warning infrastructure: `ListResult.warnings` array flows through the entire pipeline

### Established Patterns
- **AvailabilityFilter.ALL expansion:** ALL currently expands to full list at service layer. REMAINING follows same pattern but expands to [AVAILABLE, BLOCKED] only.
- **Lifecycle auto-include:** Phase 46 pipeline adds COMPLETED/DROPPED to availability list when date filter is used. This mechanism stays, but is now the SOLE path to lifecycle inclusion.
- **Cross-path parametrized tests:** fixture creates both repos, same query runs against both, assert results identical.
- **Warning constants:** centralized in `warnings.py`, used in `domain.py` and pipeline code.

### Integration Points
- `AvailabilityFilter` enum in `_enums.py` -- remove COMPLETED, DROPPED, ALL; add REMAINING
- `LifecycleDateShortcut` enum in `_enums.py` -- rename ANY to ALL
- `DomainLogic.resolve_date_filters()` in `domain.py` -- add defer hint detection
- `_expand_availability()` in `domain.py` -- handle REMAINING expansion, redundancy warnings
- `descriptions.py` -- update per-field and tool-level descriptions
- `warnings.py` -- add defer hint constants, availability redundancy warning constants
- `test_cross_path_equivalence.py` -- add date filter tests with inherited effective dates

</code_context>

<specifics>
## Specific Ideas

### Description Philosophy
Per-field descriptions teach semantics, not just syntax. They explain *when* to use the filter and *what to watch out for*. The three existing date field descriptions (DUE_DATE, DEFER_DATE, PLANNED_DATE) set the standard: each positions itself relative to the others. The filter descriptions must match this depth.

The tool-level description covers only cross-cutting concerns that can't live on any single field:
1. Effective (inherited) values -- applies to 5 of 7 date fields AND the flagged filter
2. Availability vs defer -- relationship between two parameters
3. Lifecycle expansion -- completed/dropped filters expand results, unlike every other filter

### "Remaining" as OmniFocus Vocabulary
The OmniFocus UI uses "Remaining" for the filter that shows available + on-hold tasks (which maps to available + blocked in our model). Using the same term aligns with OmniFocus vocabulary.

### "Only Completed Tasks" — Solved
`availability: [], completed: "all"` returns only completed tasks. Empty availability = no active tasks; completed filter adds lifecycle state. Clean, no special mode needed.

</specifics>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope.

</deferred>

---

*Phase: 47-cross-path-equivalence-breaking-changes*
*Context gathered: 2026-04-08*
