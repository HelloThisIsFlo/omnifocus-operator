# Phase 47: Cross-Path Equivalence & Breaking Changes - Research

**Researched:** 2026-04-08
**Domain:** Enum refactoring, cross-path testing, agent-facing descriptions, warning infrastructure
**Confidence:** HIGH

## Summary

Phase 47 is the final phase of milestone v1.3.2. It touches four distinct areas: (1) cross-path equivalence tests proving SQL and bridge paths produce identical date filter results, (2) AvailabilityFilter enum trimming (remove COMPLETED, DROPPED, ALL; add REMAINING), (3) defer hint detection in the domain layer, and (4) tool description updates with verbatim text from CONTEXT.md.

All changes are internal to the existing codebase with well-understood patterns. No new libraries needed. The cross-path tests extend an existing 46-test parametrized fixture. The enum changes are mechanical (remove values, update expansion logic). The defer hints follow the exact same pattern as the "soon" fallback warning already in `DomainLogic.resolve_date_filters()`. Descriptions are verbatim from CONTEXT.md.

**Primary recommendation:** Structure work in four waves: (1) AvailabilityFilter enum + expansion logic + tests, (2) LifecycleDateShortcut rename + descriptions + defer hints, (3) cross-path equivalence tests with inherited dates, (4) cleanup existing tests that reference removed enum values.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Remove `COMPLETED`, `DROPPED`, and `ALL` from `AvailabilityFilter` enum. Three values remain: `AVAILABLE`, `BLOCKED`, `REMAINING`.
- **D-02:** `REMAINING` = `AVAILABLE + BLOCKED`. Semantic shorthand borrowed from the OmniFocus UI.
- **D-03:** `REMAINING` is the **default** when the availability filter is omitted (`UNSET`). Same behavior as the current `[AVAILABLE, BLOCKED]` default.
- **D-04:** Warnings for redundant combinations: `["available", "remaining"]` warns, `["blocked", "remaining"]` warns. Empty list `[]` accepted.
- **D-05:** `availability: "any"` -> Pydantic rejects (not valid enum). No custom interception.
- **D-06:** Completed/dropped date filters are the sole gate for lifecycle inclusion.
- **D-07:** Rename shortcut: `"any"` -> `"all"` on completed/dropped. Update `LifecycleDateShortcut` enum.
- **D-08:** Lifecycle expansion documented in per-field descriptions. No special runtime warning.
- **D-09:** No backward compatibility interception. No dummy fields, no migration errors, no urgency filter interception. Pre-release with zero external users.
- **D-10:** Detect `defer: {after: "now"}` and `defer: {before: "now"}` in `DomainLogic.resolve_date_filters()`.
- **D-11:** Detection inspects raw `DateFilter` object before resolution: `isinstance(value, DateFilter) and value.after == "now"`.
- **D-12:** Hints appended to warnings list. Query still executes.
- **D-13:** Two new warning constants in `warnings.py` with specific wording.
- **D-14:** Extend neutral test dict with explicit `effective_*` fields. Inherited case = `due: None, effective_due: <value>`.
- **D-15:** Representative coverage, not exhaustive.
- **D-16:** Test data includes parent-child hierarchies with inherited effective dates.
- **D-17:** Use verbatim description text from CONTEXT.md (D-17a tool doc, D-17b per-field, D-17c availability).

### Claude's Discretion
- Exact placement of tool-level description addition within `LIST_TASKS_TOOL_DOC`
- Internal `_expand_remaining()` implementation
- Warning message wording for redundant availability combos
- Cross-path test class organization and parametrization strategy
- Whether to update `LIST_PROJECTS_TOOL_DOC` with same effective-date note

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| EXEC-10 | Cross-path equivalence tests prove SQL and bridge paths identical for date filters | Existing `cross_repo` fixture + seed adapters; extend neutral data with effective dates, add date filter queries |
| EXEC-11 | Cross-path test data includes tasks with inherited effective dates (direct NULL, effective non-NULL) | Neutral data format supports explicit `effective_*` fields; SQLite schema has separate columns; bridge format has separate fields |
| BREAK-01 | `urgency` filter parameter removed -- educational error if agent uses it | **Moot per D-09**: urgency filter never existed, `extra="forbid"` rejects unknown fields. No work needed. |
| BREAK-02 | `completed` field rejects boolean input -- educational error | **Moot per D-09**: `completed` is typed as `LifecycleDateShortcut \| DateFilter`, Pydantic type validation rejects booleans. No work needed. |
| BREAK-03 | `COMPLETED` and `DROPPED` removed from AvailabilityFilter enum | Remove enum values, update expansion logic, update default, remove empty-list validator |
| BREAK-04 | `defer: {after: "now"}` returns guidance hint | Add defer hint detection in `DomainLogic.resolve_date_filters()`, new warning constant |
| BREAK-05 | `defer: {before: "now"}` returns guidance hint | Same mechanism as BREAK-04, second warning constant |
| BREAK-06 | `availability: "any"` returns educational error | **Moot per D-05**: Pydantic rejects "any" as invalid enum value. No custom interception. |
| BREAK-07 | Tool descriptions updated with date filter syntax | Verbatim text in D-17a/b/c replaces existing constants in `descriptions.py` |
| BREAK-08 | `availability: "all"` returns educational error | **Moot per D-09/D-05**: After removing ALL from enum, Pydantic rejects "ALL". No custom interception. |
</phase_requirements>

## Architecture Patterns

### Change Map

All modifications fit within the existing three-layer architecture. No new files needed -- only modifications to existing files.

```
src/omnifocus_operator/
├── contracts/use_cases/list/
│   ├── _enums.py              # AvailabilityFilter: remove 3, add REMAINING
│   │                          # LifecycleDateShortcut: rename ANY->ALL
│   ├── tasks.py               # Remove empty-availability validator, update default
│   └── projects.py            # Remove empty-availability validator, update default
├── service/
│   ├── domain.py              # expand_task_availability: handle REMAINING + warnings
│   │                          # resolve_date_filters: add defer hint detection
│   └── service.py             # _ListProjectsPipeline also calls expand_task_availability
├── agent_messages/
│   ├── descriptions.py        # Replace 7 filter descriptions + tool doc + availability doc
│   └── warnings.py            # Add 2 defer hint constants + availability redundancy warnings
tests/
├── test_cross_path_equivalence.py  # Extend neutral data, add date filter test class
└── test_service_domain.py          # Update availability expansion tests, add defer hint tests
```

### Pattern 1: AvailabilityFilter Enum Trimming

**What:** Remove COMPLETED, DROPPED, ALL; add REMAINING. Update all expansion logic.

**Integration points:** [VERIFIED: all codebase grep]
- `_enums.py` line 23-30: `AvailabilityFilter` definition -- remove 3 values, add REMAINING
- `tasks.py` line 69-71: `availability` field default -- change to `[AvailabilityFilter.REMAINING]`
- `tasks.py` line 108-113: `_reject_empty_availability` validator -- **remove entirely** (D-04 accepts empty list)
- `projects.py` line 69-71: `availability` field default -- change to `[AvailabilityFilter.REMAINING]` (same enum)
- `projects.py` line 97-102: `_reject_empty_availability` validator -- **remove entirely** (same pattern as tasks)
- `domain.py` line 213-232: `expand_task_availability()` -- replace ALL expansion with REMAINING expansion + redundancy warnings
- `service.py` line 484: `_ListProjectsPipeline` also calls `expand_task_availability()` -- will work after domain change
- `errors.py` line 178: `AVAILABILITY_EMPTY` -- no longer used after both validators removed
- `warnings.py` line 160-162: `AVAILABILITY_MIXED_ALL` -- no longer used after expansion rewrite

**Current expansion logic (domain.py:222-229):**
```python
has_all = AvailabilityFilter.ALL in filters
if has_all:
    if len(filters) > 1:
        warnings.append(AVAILABILITY_MIXED_ALL)
    result_set = set(Availability)
else:
    result_set = {Availability(f.value) for f in filters}
```
[VERIFIED: codebase grep]

**New expansion logic must handle:**
- `REMAINING` -> expand to `{AVAILABLE, BLOCKED}`
- `[AVAILABLE, REMAINING]` -> warn redundancy, expand as REMAINING
- `[BLOCKED, REMAINING]` -> warn redundancy, expand as REMAINING
- `[]` -> empty set (no remaining tasks; combine with lifecycle for lifecycle-only results)

### Pattern 2: Defer Hint Detection

**What:** Detect `defer: {after: "now"}` and `defer: {before: "now"}` and append guidance warnings.

**Placement:** In `DomainLogic.resolve_date_filters()` (domain.py line 154-209), inside the per-field loop, after the field name check but before resolution. Follows the exact same pattern as the "soon without due_soon_setting" fallback (lines 187-193).

**Detection per D-11:**
```python
if field_name == "defer" and isinstance(value, DateFilter):
    if value.after == "now":
        warnings.append(DEFER_AFTER_NOW_HINT)
    if value.before == "now":
        warnings.append(DEFER_BEFORE_NOW_HINT)
# Continue with normal resolution -- hints are non-blocking
```
[VERIFIED: codebase -- DateFilter has .after and .before string attributes]

**Key detail:** The hint fires even when the DateFilter has other fields set (e.g., `{after: "now", before: "2026-05-01"}`). The hint is about the `"now"` boundary specifically, not the filter shape.

### Pattern 3: Cross-Path Equivalence Tests

**What:** Extend existing test infrastructure with date filter coverage including inherited effective dates.

**Existing infrastructure (test_cross_path_equivalence.py):**
- `_build_neutral_test_data()` returns dict with tasks, projects, tags, etc.
- `seed_bridge_repo()` translates neutral -> bridge format (camelCase, ISO dates) -> BridgeOnlyRepository
- `seed_sqlite_repo()` translates neutral -> SQLite format (CF epoch, int booleans, join tables) -> HybridRepository
- `cross_repo` parametrized fixture runs each test against both repo types
- 46 tests currently (23 test functions x 2 params)

**What needs extending for date filter tests:**
1. **Neutral test data:** Add `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified` + their `effective_*` variants to task/project dicts
2. **Inherited effective dates:** At least one task with `due: None, effective_due: <value>` (inheriting from parent project)
3. **Bridge seed adapter:** Map neutral date fields to bridge format (`dueDate`, `effectiveDueDate`, ISO strings)
4. **SQLite seed adapter:** Map neutral date fields to SQLite columns (`dateDue` as text ISO, `effectiveDateDue` as integer CF epoch)
5. **Test queries:** Create `ListTasksRepoQuery` with date bounds, assert both repos return identical results

**SQLite column format map (critical for seed adapter):** [VERIFIED: FINDINGS.md]

| Neutral field | Bridge key | SQLite column | SQLite type |
|---------------|-----------|---------------|-------------|
| due | dueDate | dateDue | text (naive ISO) |
| defer | deferDate | dateToStart | text (naive ISO) |
| planned | plannedDate | datePlanned | text (naive ISO) |
| effective_due | effectiveDueDate | effectiveDateDue | integer (CF epoch truncated) |
| effective_defer | effectiveDeferDate | effectiveDateToStart | integer (CF epoch truncated) |
| effective_planned | effectivePlannedDate | effectiveDatePlanned | integer (CF epoch truncated) |
| completed | completionDate | dateCompleted | real (CF epoch float) |
| effective_completed | effectiveCompletionDate | effectiveDateCompleted | real (CF epoch float) |
| dropped | dropDate | dateHidden | real (CF epoch float) |
| effective_dropped | effectiveDropDate | effectiveDateHidden | real (CF epoch float) |
| added | added | dateAdded | real (CF epoch float) |
| modified | modified | dateModified | real (CF epoch float) |

**Bridge field mapping (for bridge_only repo):** [VERIFIED: bridge_only.py line 54-60]
```python
_BRIDGE_FIELD_MAP = {
    "due": "effective_due_date",
    "defer": "effective_defer_date",
    "planned": "effective_planned_date",
    "completed": "effective_completion_date",
    "dropped": "effective_drop_date",
    "added": "added",
    "modified": "modified",
}
```

**SQL column mapping (for hybrid repo):** [VERIFIED: query_builder.py line 24-32]
```python
_DATE_COLUMN_MAP = {
    "due": "effectiveDateDue",
    "defer": "effectiveDateToStart",
    "planned": "effectiveDatePlanned",
    "completed": "effectiveDateCompleted",
    "dropped": "effectiveDateHidden",
    "added": "dateAdded",
    "modified": "dateModified",
}
```

Both repos filter on **effective** date columns for the 5 inheritable fields and **direct** columns for added/modified. This is exactly what cross-path tests must verify.

### Pattern 4: LifecycleDateShortcut Rename

**What:** Rename `ANY` to `ALL` in the `LifecycleDateShortcut` enum.

**Current (_enums.py line 58-62):**
```python
class LifecycleDateShortcut(StrEnum):
    ANY = "any"
    TODAY = "today"
```

**New:**
```python
class LifecycleDateShortcut(StrEnum):
    ALL = "all"
    TODAY = "today"
```

**Impact points:**
- `domain.py` line 183: checks `value.value == "any"` -- must change to `"all"`
- `descriptions.py`: `LIFECYCLE_DATE_SHORTCUT_DOC` references "any" -- must update to "all"
- All tests referencing `LifecycleDateShortcut.ANY` -- must change to `.ALL`
- `descriptions.py`: `COMPLETED_FILTER_DESC` and `DROPPED_FILTER_DESC` -- replaced by D-17b verbatim text

### Anti-Patterns to Avoid
- **Don't add migration interceptions:** D-09 explicitly forbids backward compatibility mechanisms. Pre-release project, no external users.
- **Don't modify bridge_only.py or query_builder.py:** Date filtering logic in both repos is already complete from Phase 46. Cross-path tests verify existing behavior, not add new behavior.
- **Don't add dummy fields for urgency/completed-bool:** D-09 says `extra="forbid"` and Pydantic type validation handle these.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Cross-path test fixture | Custom repo creation per test | Existing `cross_repo` parametrized fixture | Already handles both bridge + SQLite seeding with neutral data |
| Date comparison in tests | Manual datetime arithmetic | Existing `_to_cf_epoch()` and `_dt_to_iso()` helpers | Already in test file, battle-tested |
| Warning delivery | Custom warning transport | `ListResult.warnings` pipeline | Already flows through all three layers |

## Common Pitfalls

### Pitfall 1: SQLite Column Type Mismatch for Effective Dates
**What goes wrong:** Cross-path tests fail because SQLite effective date columns use integer CF epoch (truncated) while direct date columns use text (naive ISO) or real (CF epoch float).
**Why it happens:** OmniFocus stores `effectiveDateDue`/`effectiveDateToStart`/`effectiveDatePlanned` as INTEGER, not TEXT or REAL like other date columns.
**How to avoid:** SQLite seed adapter must use `int(_to_cf_epoch(dt))` for effective date columns, not `_to_cf_epoch(dt)` (which returns float).
**Warning signs:** Tests pass on bridge but fail on SQLite with empty results (integer comparison with float parameter may behave unexpectedly).
[VERIFIED: FINDINGS.md column type map]

### Pitfall 2: Empty Availability List Rejected in BOTH Query Models
**What goes wrong:** Submitting `availability: []` raises `ValueError` instead of returning empty results.
**Why it happens:** Current validators in both `tasks.py` (line 108-113) and `projects.py` (line 97-102) explicitly reject empty lists.
**How to avoid:** Remove `_reject_empty_availability` validators from **both** `ListTasksQuery` and `ListProjectsQuery`. D-04 requires empty lists to be accepted.
**Warning signs:** Tests for "only completed tasks" pattern fail with validation error.
[VERIFIED: codebase -- both tasks.py and projects.py have identical validators]

### Pitfall 3: REMAINING Default vs Empty List Semantics
**What goes wrong:** Confusing "default" (REMAINING = available + blocked) with "empty" (no remaining tasks).
**Why it happens:** The `availability` field default is `[REMAINING]`, but `[]` is also valid.
**How to avoid:** Default `[AvailabilityFilter.REMAINING]` expands to [AVAILABLE, BLOCKED]. Empty `[]` expands to empty set. Both paths through `expand_task_availability()` must be correct.
**Warning signs:** Empty availability returns all tasks or raises an error instead of returning none.

### Pitfall 4: LifecycleDateShortcut Value String Change
**What goes wrong:** Domain logic checks `value.value == "any"` but the enum now has `ALL = "all"`.
**Why it happens:** The domain layer compares the string value, not the enum member name.
**How to avoid:** Update the string comparison in `resolve_date_filters()` from `"any"` to `"all"`.
**Warning signs:** `completed: "all"` returns date-filtered results instead of expanding availability only (the "all" shortcut should add lifecycle without date bounds).
[VERIFIED: domain.py line 183]

### Pitfall 5: Description Constants Used as Enum Docstrings
**What goes wrong:** Changing description constants breaks enum `__doc__` that imports them.
**Why it happens:** `AvailabilityFilter.__doc__ = AVAILABILITY_DOC`, `DueDateShortcut.__doc__ = DUE_DATE_SHORTCUT_DOC`, `LifecycleDateShortcut.__doc__ = LIFECYCLE_DATE_SHORTCUT_DOC` are set at class definition via imports from descriptions.py.
**How to avoid:** Update `AVAILABILITY_DOC`, `DUE_DATE_SHORTCUT_DOC`, and `LIFECYCLE_DATE_SHORTCUT_DOC` to reflect the new enum values and semantics.
**Warning signs:** Agent sees stale or misleading docstrings in JSON Schema output.
[VERIFIED: _enums.py lines 14-19, 23-24, 50-51, 58-59]

### Pitfall 6: ListProjectsPipeline Uses Same Expansion
**What goes wrong:** Projects pipeline breaks after availability enum changes.
**Why it happens:** `_ListProjectsPipeline` (service.py line 484) calls `expand_task_availability()` with the same `AvailabilityFilter` list. If expansion logic changes are incomplete, projects break too.
**How to avoid:** After updating `expand_task_availability()`, run both task and project pipeline tests.
**Warning signs:** `list_projects` returns wrong results or raises `ValueError` on "remaining".
[VERIFIED: service.py line 484]

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_cross_path_equivalence.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EXEC-10 | SQL and bridge paths identical for date filters | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "date"` | Partially (extend existing) |
| EXEC-11 | Test data includes inherited effective dates | integration | Same as EXEC-10 | No -- Wave 0 gap |
| BREAK-01 | urgency filter rejected | unit | Moot -- `extra="forbid"` handles it | Existing coverage |
| BREAK-02 | completed boolean rejected | unit | Moot -- Pydantic type validation | Existing coverage |
| BREAK-03 | COMPLETED/DROPPED removed from enum | unit | `uv run pytest tests/test_service_domain.py -x -q -k "availability"` | Partially (update existing) |
| BREAK-04 | defer after:now hint | unit | `uv run pytest tests/test_service_domain.py -x -q -k "defer_hint"` | No -- Wave 0 gap |
| BREAK-05 | defer before:now hint | unit | Same as BREAK-04 | No -- Wave 0 gap |
| BREAK-06 | availability "any" rejected | unit | Moot -- Pydantic validates | Existing (after enum change) |
| BREAK-07 | Descriptions updated | unit | `uv run pytest tests/test_output_schema.py -x -q` | Existing coverage |
| BREAK-08 | availability "ALL" rejected | unit | Moot -- Pydantic validates (after enum change) | Existing (after enum change) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_cross_path_equivalence.py tests/test_service_domain.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Cross-path date filter tests in `tests/test_cross_path_equivalence.py` -- covers EXEC-10, EXEC-11
- [ ] Defer hint detection tests in `tests/test_service_domain.py` -- covers BREAK-04, BREAK-05
- [ ] Update existing availability expansion tests for REMAINING semantics -- covers BREAK-03

## Code Examples

### AvailabilityFilter After Trimming
```python
# Source: D-01 through D-04
class AvailabilityFilter(StrEnum):
    __doc__ = AVAILABILITY_DOC  # Update this constant too

    AVAILABLE = "available"
    BLOCKED = "blocked"
    REMAINING = "remaining"
```

### REMAINING Expansion in DomainLogic
```python
# Source: D-02, D-03, D-04
def expand_task_availability(
    self,
    filters: list[AvailabilityFilter],
    lifecycle_additions: list[Availability],
) -> tuple[list[Availability], list[str]]:
    warnings: list[str] = []
    result_set: set[Availability] = set()

    has_remaining = AvailabilityFilter.REMAINING in filters
    if has_remaining:
        result_set |= {Availability.AVAILABLE, Availability.BLOCKED}
        # Redundancy warnings
        if AvailabilityFilter.AVAILABLE in filters:
            warnings.append(AVAILABILITY_REMAINING_INCLUDES_AVAILABLE)
        if AvailabilityFilter.BLOCKED in filters:
            warnings.append(AVAILABILITY_REMAINING_INCLUDES_BLOCKED)
    # Non-REMAINING values map directly
    for f in filters:
        if f != AvailabilityFilter.REMAINING:
            result_set.add(Availability(f.value))

    result_set |= set(lifecycle_additions)
    return list(result_set), warnings
```

### ListTasksQuery Default After Enum Change
```python
# Source: D-03, D-04
availability: list[AvailabilityFilter] = Field(
    default=[AvailabilityFilter.REMAINING]
)
# NOTE: Remove _reject_empty_availability validator from BOTH tasks.py AND projects.py
```

### Defer Hint Detection in resolve_date_filters
```python
# Source: D-10, D-11, D-12 -- add inside the per-field loop
if field_name == "defer" and isinstance(value, DateFilter):
    if value.after == "now":
        warnings.append(DEFER_AFTER_NOW_HINT)
    if value.before == "now":
        warnings.append(DEFER_BEFORE_NOW_HINT)
```

### Cross-Path Neutral Data with Inherited Dates
```python
# Source: D-14, D-16 -- extend _build_neutral_test_data()
# Project with due date (source of inheritance)
{
    "id": "proj-due",
    "name": "Project With Due",
    "due": datetime(2026, 3, 15, 17, 0, 0, tzinfo=UTC),
    "effective_due": datetime(2026, 3, 15, 17, 0, 0, tzinfo=UTC),
    # ... other fields
}
# Child task inheriting due from project (direct NULL, effective non-NULL)
{
    "id": "task-inherited-due",
    "name": "Inherited Due Task",
    "due": None,  # direct is NULL
    "effective_due": datetime(2026, 3, 15, 17, 0, 0, tzinfo=UTC),  # inherited
    "project_id": "proj-due",
    "parent_id": "proj-due",
    # ... other fields
}
```

## Assumptions Log

> All assumptions from initial research have been verified against the codebase.

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| -- | (none remaining) | -- | -- |

**Resolved during research:**
- A1 (ListProjectsQuery uses AvailabilityFilter): VERIFIED -- `projects.py` line 69-71 imports and uses `AvailabilityFilter` with identical default and validator
- A2 (empty-list validator in ListProjectsQuery): VERIFIED -- `projects.py` line 97-102 has identical `_reject_empty_availability` validator that must also be removed

## Open Questions

1. **Should `LIST_PROJECTS_TOOL_DOC` also get the effective-date note?**
   - What we know: CONTEXT.md lists this as Claude's discretion. Projects also have effective dates.
   - Recommendation: Yes, add the same effective-date note. Factually accurate and keeps tool docs consistent.

## Sources

### Primary (HIGH confidence)
- Codebase direct inspection -- all code files listed in CONTEXT.md canonical references
- `tests/test_cross_path_equivalence.py` -- existing 46 cross-path tests, seed adapter patterns
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` -- bridge date filter field map (line 54-60)
- `src/omnifocus_operator/repository/hybrid/query_builder.py` -- SQL date column map (line 24-32)
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` -- ListProjectsQuery availability (line 69-102)
- `src/omnifocus_operator/service/service.py` -- _ListProjectsPipeline expand call (line 484)
- `.research/deep-dives/direct-database-access-date-filters/FINDINGS.md` -- column type map

### Secondary (MEDIUM confidence)
- 47-CONTEXT.md -- all decisions verified against codebase implementation points

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all existing patterns
- Architecture: HIGH -- all integration points verified in codebase, including projects.py
- Pitfalls: HIGH -- column type mismatch, dual validator removal, and ListProjects impact all verified

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable -- internal refactoring, no external dependencies)
