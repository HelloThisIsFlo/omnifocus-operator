# Architecture: Date Filtering Integration

**Domain:** Date filtering for OmniFocus MCP task queries
**Researched:** 2026-04-07

## Recommended Architecture

Date filtering integrates into the existing three-layer pipeline without new layers or components. The primary new abstractions are:

1. **DateFilter model** (contracts) -- Pydantic discriminated union for the `string | object` input
2. **Date resolver** (service) -- resolves shorthand/shortcuts to absolute `DateRange(after, before)` pairs
3. **SQL date predicates** (repository/query_builder) -- adds WHERE clauses for resolved date ranges
4. **Bridge date filter** (repository/bridge_only) -- identical filtering in Python against snapshot

### Data Flow

```
Agent input (string | DateFilter)
    |
    v
[Contract Layer] -- ListTasksQuery validates, holds raw DateFilter per field
    |
    v
[Service Layer] -- _ListTasksPipeline:
    1. Capture "now" snapshot (single datetime)
    2. Resolve each DateFilter to DateRange(after: datetime|None, before: datetime|None)
    3. Auto-adjust availability when completed/dropped filters present
    4. Build ListTasksRepoQuery with resolved DateRange objects
    |
    v
[Repository Layer] -- receives DateRange objects (absolute timestamps only)
    SQL path: query_builder adds date WHERE clauses with CF-epoch params
    Bridge path: bridge_only filters in-memory using same DateRange
```

### Component Boundaries

| Component | Responsibility | Touches |
|-----------|---------------|---------|
| `contracts/use_cases/list/tasks.py` | DateFilter model, new Patch fields on ListTasksQuery, validation | New `DateFilter` union type, 7 new fields |
| `contracts/use_cases/list/_date_filter.py` (NEW) | DateFilter, DateRange, DateShorthand models | Imported by tasks.py |
| `service/date_resolve.py` (NEW) | `resolve_date_filter(filter, field_name, now) -> DateRange`, shorthand math, "soon" threshold | Imported by service.py pipeline |
| `service/service.py` | _ListTasksPipeline gains date resolution step + availability auto-adjustment | Modified: new pipeline steps |
| `repository/hybrid/query_builder.py` | Date predicate SQL generation | Modified: new clause builder |
| `repository/bridge_only/bridge_only.py` | In-memory date comparison | Modified: new filter block in list_tasks |
| `config.py` | DUE_SOON_THRESHOLD, WEEK_START config | Modified: new constants |
| `agent_messages/descriptions.py` | Per-field descriptions, tool-level date docs | Modified: new description constants |
| `agent_messages/warnings.py` | Defer-vs-availability hints | Modified: new warning constants |
| `agent_messages/errors.py` | Educational errors for invalid shortcuts | Modified: new error constants |

## New Components

### 1. DateFilter Contract Model (`contracts/use_cases/list/_date_filter.py`)

```python
# Pydantic model hierarchy for date filter input

class DateShorthand(StrictModel):
    """Exactly one of this/last/next."""
    this: str | _Unset = UNSET   # "d", "w", "m", "y"
    last: str | _Unset = UNSET   # "[N]d", "[N]w", "[N]m", "[N]y"
    next: str | _Unset = UNSET   # "[N]d", "[N]w", "[N]m", "[N]y"
    # model_validator: exactly one key set

class DateAbsolute(StrictModel):
    """One or both of before/after."""
    before: str | _Unset = UNSET  # ISO8601, date-only, or "now"
    after: str | _Unset = UNSET   # ISO8601, date-only, or "now"
    # model_validator: at least one key, after < before when both present

# The agent-facing field type:
# Patch[str | DateShorthand | DateAbsolute]
# - str for shortcuts ("today", "overdue", "soon", "any", "none")
# - DateShorthand for {this: "w"}, {last: "3d"}, {next: "1m"}
# - DateAbsolute for {before: "...", after: "..."}
```

**Design choice: discriminated-key pattern.** Follows the existing MoveAction pattern -- the key IS the discriminator (`this`/`last`/`next` or `before`/`after`). Pydantic's `model_validator` enforces mutual exclusivity, identical to MoveAction validation.

**Why two models, not one:** `DateShorthand` and `DateAbsolute` have mutually exclusive key sets. A single model with all 5 keys would need cross-validation; two models with Pydantic union discrimination is cleaner and produces better error messages.

### 2. DateRange (resolved representation)

```python
@dataclass(frozen=True)
class DateRange:
    """Resolved date filter -- absolute timestamps, ready for SQL/bridge."""
    after: datetime | None = None   # >= comparison (inclusive)
    before: datetime | None = None  # < comparison (exclusive internally)
    is_null_check: bool = False     # True for "none" shortcut
    is_any: bool = False            # True for "any" shortcut (no date restriction)
```

Lives in contracts alongside DateFilter. The repo layer receives only DateRange -- never raw strings or shorthand objects.

### 3. Date Resolver (`service/date_resolve.py`)

Pure functions, no class needed (unlike Resolver which needs repo access for name lookups).

```python
def resolve_date_filter(
    raw: str | DateShorthand | DateAbsolute,
    field_name: str,
    now: datetime,
    due_soon_threshold: timedelta | None = None,
    week_start: int = 0,  # 0=Monday (ISO), 6=Sunday
) -> DateRange:
    """Resolve any date filter form to absolute DateRange."""
```

**Key behaviors:**
- String shortcuts: dispatch table `{"today": ..., "overdue": ..., "soon": ..., "any": ..., "none": ...}`
- `"soon"` requires `due_soon_threshold` (only valid on `due` field -- validated at contract level)
- Shorthand: parse `[N]unit` format (reuse pattern from `ReviewDueFilter`), apply calendar math
- Absolute: parse ISO8601/date-only/`"now"`, apply date-only resolution rules
- All math uses `now` parameter -- never calls `datetime.now()` internally

### 4. "Now" Snapshot

Created in `_ListTasksPipeline.execute()` before any filter resolution:

```python
async def execute(self, query: ListTasksQuery) -> ListResult[Task]:
    self._now = datetime.now()  # naive local time per spec
    # ... resolve date filters using self._now ...
```

This is a service-layer concern. The repository never sees "now" -- only resolved DateRange objects.

## Modified Components

### ListTasksQuery (contracts)

7 new `Patch[str | DateShorthand | DateAbsolute]` fields:

```python
due: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
defer: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
planned: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
completed: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
dropped: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
added: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
modified: Patch[str | DateShorthand | DateAbsolute] = Field(default=UNSET, ...)
```

Field-specific validators ensure shortcut validity (e.g., `"overdue"` only on `due`).

### ListTasksRepoQuery (contracts)

7 new `DateRange | None` fields:

```python
due: DateRange | None = None
defer: DateRange | None = None
planned: DateRange | None = None
completed: DateRange | None = None
dropped: DateRange | None = None
added: DateRange | None = None
modified: DateRange | None = None
```

### _ListTasksPipeline (service)

New steps inserted between existing steps:

```
execute():
    1. self._now = datetime.now()          # NEW: "now" snapshot
    2. ... existing: gather tags/projects ...
    3. ... existing: resolve_inbox ...
    4. ... existing: resolve_project, resolve_tags ...
    5. self._resolve_date_filters()        # NEW: resolve all 7 date fields
    6. self._adjust_availability()         # NEW: auto-include completed/dropped
    7. self._check_defer_warning()         # NEW: defer-vs-availability hints
    8. self._build_repo_query()            # MODIFIED: include resolved DateRanges
    9. return await self._delegate()
```

### Availability Auto-Adjustment

When `completed` or `dropped` date filter is set, the pipeline automatically adds those availability values:

```python
def _adjust_availability(self) -> None:
    """Auto-include completed/dropped when date filters target those states."""
    if self._completed_range is not None:
        # Ensure COMPLETED is in availability list
        ...
    if self._dropped_range is not None:
        # Ensure DROPPED is in availability list
        ...
```

This is service logic -- the agent shouldn't need to manually set `availability: ["available", "completed"]` when using `completed: "today"`.

### Availability Trimming (breaking change)

The `availability` field on ListTasksQuery drops `COMPLETED` and `DROPPED` enum values. Only `AVAILABLE`, `BLOCKED`, and `ALL` remain. The service layer handles completed/dropped inclusion based on date filters.

This means `AvailabilityFilter` enum changes from 5 values to 3.

### query_builder.py (repository)

New helper function for date predicates:

```python
# Date field -> SQLite column mapping
_DATE_COLUMN_MAP = {
    "due": "t.effectiveDateDue",
    "defer": "t.effectiveDateToStart",
    "planned": "t.effectiveDatePlanned",
    "completed": "t.effectiveDateCompleted",
    "dropped": "t.effectiveDateHidden",
    "added": "t.dateAdded",
    "modified": "t.dateModified",
}

def _add_date_predicate(
    conditions: list[str],
    params: list[Any],
    field: str,
    date_range: DateRange,
) -> None:
    """Add date filter WHERE clause. Values stored as CF-epoch seconds."""
```

Date values in SQLite are Core Foundation epoch seconds (seconds since 2001-01-01). The existing `_CF_EPOCH` constant handles conversion. Date predicates use `>=` and `<` with parameterized values.

For `is_null_check=True`: generates `column IS NULL`.
For `is_any=True`: no date predicate (but triggers availability adjustment).

### bridge_only.py (repository)

Parallel Python filtering using model attribute access:

```python
# Date field -> Task attribute mapping
_DATE_ATTR_MAP = {
    "due": "effective_due_date",
    "defer": "effective_defer_date",
    "planned": "effective_planned_date",
    "completed": "effective_completion_date",
    "dropped": "effective_drop_date",
    "added": "added",
    "modified": "modified",
}
```

Both paths use the same DateRange dataclass -- the only difference is how the comparison is executed (SQL vs Python).

### config.py

```python
# -- Due-soon threshold --------------------------------------------------------
# How far ahead "due soon" extends. Matches OmniFocus "Due Soon" preference.
# Configurable via OPERATOR_DUE_SOON env var. Default: 2 days.
DUE_SOON_THRESHOLD: timedelta = ...  # parsed from env

# -- Week start ----------------------------------------------------------------
# 0=Monday (ISO 8601), 6=Sunday. Affects {this: "w"} calendar alignment.
WEEK_START: int = ...  # parsed from OPERATOR_WEEK_START env var
```

## Patterns to Follow

### Pattern 1: Discriminated-Key Union (existing)

MoveAction already uses this: `{"beginning": "parentId"}` / `{"ending": "parentId"}`. DateShorthand uses the same pattern: `{"this": "w"}` / `{"last": "3d"}` / `{"next": "1m"}`.

### Pattern 2: Resolution at Service Boundary (existing)

Name-to-ID resolution happens in the service layer before repo delegation. Date filter resolution follows the same pattern: raw `string | DateFilter` enters the service, resolved `DateRange` exits to the repo.

### Pattern 3: Shared Resolution, Divergent Execution (existing)

Cross-path equivalence tests prove SQL and bridge produce identical results. Date filtering adds 7 new axes to test but follows the same structure -- shared DateRange, divergent execution (SQL vs Python).

### Pattern 4: Pure Functions for Resolution (new but fits)

`date_resolve.py` is pure functions taking `now` as a parameter. This makes testing trivial -- inject any timestamp. Follows the existing `_expand_review_due` static method pattern but extracted to its own module because it serves 7 fields, not 1.

## Anti-Patterns to Avoid

### Anti-Pattern 1: "now" evaluated per-filter

Each date filter calling `datetime.now()` independently creates subtle inconsistencies when a query has multiple date fields. The spec requires a single snapshot.

### Anti-Pattern 2: Date resolution in the repository

The repo should receive only absolute timestamps. Putting shorthand resolution in the query builder or bridge filter would duplicate logic and violate the "service resolves, repo executes" boundary.

### Anti-Pattern 3: Raw string shortcuts reaching the repo

Shortcuts like `"today"` or `"soon"` are agent-facing sugar. The repo should never see them -- only `DateRange` with absolute timestamps or null-check/any flags.

### Anti-Pattern 4: Calendar math with dateutil

The spec explicitly calls for naive approximation (1 month = 30 days, 1 year = 365 days) matching the existing `review_due_within` convention. Adding python-dateutil would be inconsistent and adds a runtime dependency.

## SQLite Column Reference

Confirmed mapping from hybrid.py row parsing:

| Date filter field | SQLite column | Effective? | Type |
|---|---|---|---|
| `due` | `effectiveDateDue` | Yes (inherited) | CF epoch float, nullable |
| `defer` | `effectiveDateToStart` | Yes (inherited) | CF epoch float, nullable |
| `planned` | `effectiveDatePlanned` | Yes (inherited) | CF epoch float, nullable |
| `completed` | `effectiveDateCompleted` | Yes (inherited) | CF epoch float, nullable |
| `dropped` | `effectiveDateHidden` | Yes (inherited) | CF epoch float, nullable |
| `added` | `dateAdded` | No (direct) | CF epoch float, NOT NULL |
| `modified` | `dateModified` | No (direct) | CF epoch float, NOT NULL |

All stored as Core Foundation epoch seconds (seconds since 2001-01-01 00:00:00 UTC). Conversion: `(py_datetime - _CF_EPOCH).total_seconds()`.

## Suggested Build Order

Build order follows dependency chain -- each phase produces a testable artifact.

### Phase 1: DateFilter Contract Models + Validation

**New:** `contracts/use_cases/list/_date_filter.py` (DateFilter, DateShorthand, DateAbsolute, DateRange)
**Modified:** None yet -- standalone models with unit tests

- DateShorthand with exactly-one-key validator
- DateAbsolute with at-least-one-key and after<before validators
- Duration string parser (`[N]unit` format)
- DateRange dataclass
- Field-specific shortcut validation rules
- Tests: model validation, rejection of invalid combos, error messages

**Why first:** Everything else depends on these types being correct.

### Phase 2: Date Resolver (pure function)

**New:** `service/date_resolve.py`
**Modified:** None yet -- standalone resolver with unit tests

- `resolve_date_filter()` with all resolution paths
- `"today"` / `"overdue"` / `"soon"` / `"any"` / `"none"` shortcuts
- `this` calendar-aligned resolution (needs week_start config)
- `last`/`next` day-snapped rolling resolution
- Absolute date parsing (ISO8601, date-only, `"now"`)
- Date-only boundary expansion (`before` → next-day midnight)
- Month/year approximation (30d/365d)
- Tests: extensive parametrized tests with fixed `now` timestamps, covering all the spec's concrete examples

**Why second:** Pure functions, no integration needed. Can verify all the spec's example cases.

### Phase 3: Config + Descriptions

**Modified:** `config.py`, `agent_messages/descriptions.py`, `agent_messages/warnings.py`, `agent_messages/errors.py`

- DUE_SOON_THRESHOLD from env var (with parsing, default)
- WEEK_START from env var
- All 7 field descriptions
- Tool-level date filter description text
- Defer-vs-availability warning strings
- Educational error strings for invalid shortcuts

**Why third:** Config is needed by resolver tests for threshold. Descriptions needed before wiring into ListTasksQuery.

### Phase 4: Contract Integration (ListTasksQuery + ListTasksRepoQuery)

**Modified:** `contracts/use_cases/list/tasks.py`

- 7 new Patch fields on ListTasksQuery with field descriptions
- 7 new DateRange fields on ListTasksRepoQuery
- Field-specific validators (shortcut validity per field)
- AvailabilityFilter enum trimmed (remove COMPLETED, DROPPED)
- Tests: query model validation, schema shape verification

**Why fourth:** Models must exist before pipeline and repo can use them.

### Phase 5: Service Pipeline Integration

**Modified:** `service/service.py` (_ListTasksPipeline)

- "Now" snapshot at pipeline start
- Date filter resolution step (calls resolve_date_filter for each set field)
- Availability auto-adjustment for completed/dropped
- Defer-vs-availability warning detection
- Build repo query with resolved DateRange fields
- Tests: pipeline integration tests with InMemoryBridge

**Why fifth:** Wires resolver into the existing pipeline flow.

### Phase 6: SQL Path

**Modified:** `repository/hybrid/query_builder.py`

- `_add_date_predicate()` helper
- `_DATE_COLUMN_MAP` constant
- CF-epoch conversion for date params
- IS NULL generation for `"none"`
- Integration into `build_list_tasks_sql()`
- Tests: SQL generation unit tests (verify SQL string + params)

**Why sixth:** Repository is the last layer to touch.

### Phase 7: Bridge Path

**Modified:** `repository/bridge_only/bridge_only.py`

- `_DATE_ATTR_MAP` constant
- Date comparison filter block in `list_tasks()`
- IS None check for `"none"`
- Tests: bridge path unit tests

**Why seventh:** Parallel to SQL path, same DateRange input.

### Phase 8: Cross-Path Equivalence + Existing Filter Changes

- Cross-path equivalence tests for all date filter variants
- Remove `urgency` filter parameter from ListTasksQuery
- Replace `completed` boolean with date filter
- Availability enum trimming (if not done in Phase 4)
- End-to-end integration tests

**Why last:** Cross-path tests validate the full stack. Breaking changes are safest after new functionality is proven.

## Sources

- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.2.md`
- Existing query builder: `src/omnifocus_operator/repository/hybrid/query_builder.py`
- Existing bridge filter: `src/omnifocus_operator/repository/bridge_only/bridge_only.py`
- Service pipeline: `src/omnifocus_operator/service/service.py`
- Task model: `src/omnifocus_operator/models/common.py` (date fields)
- SQLite column mapping: `src/omnifocus_operator/repository/hybrid/hybrid.py` (lines 340-381)
