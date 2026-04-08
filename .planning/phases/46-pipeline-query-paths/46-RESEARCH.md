# Phase 46: Pipeline & Query Paths - Research

**Researched:** 2026-04-08
**Domain:** Service pipeline integration, SQL query building, bridge in-memory filtering, OmniFocus Settings table reads
**Confidence:** HIGH

## Summary

Phase 46 wires the Phase 45 date models (DateFilter, shortcut enums, resolve_date_filter) into the `list_tasks` pipeline. Three integration surfaces:

1. **Service pipeline** -- new `_resolve_date_filters()` step in `_ListTasksPipeline`, following the Method Object grain. Calls `resolve_date_filter()` per field, handles lifecycle auto-include, captures `now` once.
2. **SQL query builder** -- date predicates on effective CF epoch columns in `build_list_tasks_sql()`. Python `datetime` -> CF epoch float conversion at the query builder boundary.
3. **Bridge fallback** -- in-memory date filtering in `BridgeOnlyRepository.list_tasks()`, comparing resolved `_after`/`_before` datetimes against Task model `AwareDatetime` fields.

Plus a new `get_due_soon_setting()` method on the Repository protocol, implemented in HybridRepository (SQLite Settings table) and BridgeOnlyRepository (env var).

**Primary recommendation:** Follow the established patterns exactly -- each integration surface has a clear precedent in the codebase (resolve_project/resolve_tags for pipeline, review_due_before for CF conversion, existing list comprehensions for bridge filtering).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** `get_due_soon_setting() -> DueSoonSetting | None` on Repository protocol. HybridRepository reads from SQLite Settings table. BridgeOnlyRepository reads from `OPERATOR_DUE_SOON_THRESHOLD` env var.
- **D-02:** Pipeline calls `get_due_soon_setting()` conditionally -- only when `due: "soon"` detected.
- **D-03:** Returns `None` when neither source available; resolver fails fast with educational error (already implemented).
- **D-04:** New `_resolve_date_filters()` method in `_ListTasksPipeline`, between `_resolve_tags()` and `_build_repo_query()`.
- **D-05:** `datetime.now()` captured once at top of `_resolve_date_filters()` -- single "now" snapshot per query.
- **D-06:** Each date field resolved via `resolve_date_filter()`, stored as `self._<field>_after` / `self._<field>_before`.
- **D-07:** `completed`/`dropped` fields trigger `self._lifecycle_availability_additions`.
- **D-08:** `_build_repo_query()` merges lifecycle additions with expanded availability via set-union.
- **D-09:** Date predicates are top-level AND conditions in SQL WHERE clause.
- **D-10:** `completed: {last: "1w"}` naturally returns only completed tasks (NULL effectiveDateCompleted excluded by SQL).
- **D-11:** Combining lifecycle + other date filters = AND intersection.
- **D-12:** Column mapping (7 fields -> effective columns). See table in CONTEXT.md.
- **D-13:** Direct date columns are text format -- cannot be compared numerically. Only effective columns.
- **D-14:** Integer vs real mixing is transparent to SQLite.
- **D-15:** 174 inherited-completion tasks appear in `completed` filter results. Semantically correct.
- **D-16:** Never use `dueSoon` column. Compute `effectiveDateDue < threshold` directly.

### Claude's Discretion
- CF epoch conversion strategy (where Python datetime -> CF epoch float happens)
- `OPERATOR_DUE_SOON_THRESHOLD` env var format for BridgeOnlyRepository
- InMemoryBridge `get_due_soon_setting()` implementation for tests
- Exact signature of `_resolve_date_filters()`
- Bridge path filtering order/optimization

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| RESOLVE-11 | `"overdue"` resolves to `effectiveDateDue < now` -- both paths use identical timestamp logic | `resolve_date_filter()` already returns `(None, now)` for overdue. Pipeline captures `now` once (D-05). SQL converts to CF epoch. Bridge compares against `effective_due_date`. |
| RESOLVE-12 | `"soon"` resolves using DueSoonInterval + DueSoonGranularity from Settings table | `resolve_date_filter()` already implements two-mode threshold. `get_due_soon_setting()` is the new retrieval method. DueSoonSetting enum maps all 7 UI options. |
| EXEC-01 | SQL path adds date predicates on effective CF epoch columns | Query builder adds `t.effectiveDateDue >= ?` / `t.effectiveDateDue < ?` with CF epoch float params. Pattern matches existing `review_due_before`. |
| EXEC-02 | Bridge fallback applies identical date filtering in-memory | Sequential list comprehensions comparing `task.effective_due_date` (AwareDatetime) against resolved datetime bounds. |
| EXEC-03 | Using `completed` date filter auto-includes completed tasks | Pipeline's `_resolve_date_filters()` adds `Availability.COMPLETED` to lifecycle additions when completed field is set. |
| EXEC-04 | Using `dropped` date filter auto-includes dropped tasks | Same mechanism -- adds `Availability.DROPPED` to lifecycle additions when dropped field is set. |
| EXEC-05 | `completed: "any"` includes all completed tasks regardless of date | `"any"` triggers availability addition but bypasses date resolver (raises ValueError in resolver, handled in pipeline). No _after/_before set. |
| EXEC-06 | `dropped: "any"` includes all dropped tasks regardless of date | Same mechanism as EXEC-05 for dropped. |
| EXEC-07 | Tasks with no value for filtered date field are excluded (NULL) | SQL natural behavior: `NULL >= ?` evaluates to false. Bridge: `None` fields fail comparison. |
| EXEC-09 | Date filters combine with AND with each other and existing base filters | SQL conditions list is AND-joined. Bridge list comprehensions applied sequentially (logical AND). |

</phase_requirements>

## Standard Stack

No new dependencies. Phase 46 uses only existing project infrastructure.

### Core (already installed)
| Library | Version | Purpose |
|---------|---------|---------|
| pydantic | 2.x (project version) | Model validation for query/repo contracts |
| pydantic-settings | 2.x (project version) | `Settings(BaseSettings)` for env var reading |
| pytest | 9.0.2 | Test framework |

### Key Internal Modules (Phase 45 outputs)
| Module | Purpose |
|--------|---------|
| `service/resolve_dates.py` | Pure `resolve_date_filter()` -- already tested (49 tests) |
| `contracts/use_cases/list/_enums.py` | `DueDateShortcut`, `LifecycleDateShortcut`, `DueSoonSetting` |
| `contracts/use_cases/list/_date_filter.py` | `DateFilter` contract model |
| `contracts/use_cases/list/tasks.py` | `ListTasksQuery` (7 date fields), `ListTasksRepoQuery` (14 _after/_before fields) |
| `config.py` | `Settings`, `get_settings()`, `get_week_start()` |

## Architecture Patterns

### Integration Surface Map
```
Agent request
  |
  v
ListTasksQuery (7 date fields: due, defer, planned, completed, dropped, added, modified)
  |
  v
_ListTasksPipeline.execute()
  |-- _resolve_inbox()
  |-- _check_inbox_project_warning()
  |-- _resolve_project()
  |-- _resolve_tags()
  |-- _resolve_date_filters()    <-- NEW
  |-- _build_repo_query()        <-- MODIFIED (date fields + lifecycle merge)
  |-- _delegate()
  |
  v
ListTasksRepoQuery (14 _after/_before datetime fields + merged availability)
  |
  +--- SQL path (HybridRepository)
  |    query_builder.py: datetime -> CF epoch conversion, WHERE predicates
  |
  +--- Bridge path (BridgeOnlyRepository)
       list_tasks(): sequential list comprehensions against Task model fields
```

### Pattern 1: Pipeline Date Resolution Step
**What:** `_resolve_date_filters()` follows the `_resolve_project()` / `_resolve_tags()` grain.
**When to use:** This phase only -- it's the date-specific pipeline step.

```python
# [VERIFIED: codebase pattern from _resolve_project() / _resolve_tags()]
def _resolve_date_filters(self) -> None:
    self._now = datetime.now()  # single timestamp per D-05
    self._lifecycle_availability_additions: list[Availability] = []

    # For each of the 7 date fields:
    # 1. Check if set (is_set)
    # 2. Handle "any" shortcut -> lifecycle addition only, no date bounds
    # 3. Call resolve_date_filter() -> (after, before) tuple
    # 4. Store as self._<field>_after / self._<field>_before
    # 5. For completed/dropped: add lifecycle availability
```

### Pattern 2: CF Epoch Conversion in Query Builder
**What:** Convert Python `datetime` to CF epoch float for SQL parameters.
**Precedent:** Already done for `review_due_before` in `build_list_projects_sql()`.

```python
# [VERIFIED: query_builder.py line 220]
# Existing pattern:
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)
cf_seconds = (query.review_due_before - _CF_EPOCH).total_seconds()
params.append(cf_seconds)

# Date filter pattern (same conversion):
if query.due_after is not None:
    conditions.append("t.effectiveDateDue >= ?")
    params.append((query.due_after - _CF_EPOCH).total_seconds())
if query.due_before is not None:
    conditions.append("t.effectiveDateDue < ?")
    params.append((query.due_before - _CF_EPOCH).total_seconds())
```

### Pattern 3: Bridge In-Memory Filtering
**What:** Sequential list comprehensions matching SQL semantics.
**Precedent:** All existing filters in `BridgeOnlyRepository.list_tasks()`.

```python
# [VERIFIED: bridge_only.py lines 157-188]
# Existing pattern:
if query.flagged is not None:
    items = [t for t in items if t.flagged == query.flagged]

# Date filter pattern (same shape):
if query.due_after is not None:
    items = [t for t in items if t.effective_due_date is not None
             and t.effective_due_date >= query.due_after]
if query.due_before is not None:
    items = [t for t in items if t.effective_due_date is not None
             and t.effective_due_date < query.due_before]
```

### Pattern 4: Repository Protocol Extension
**What:** Add `get_due_soon_setting()` to Repository protocol.
**Precedent:** Protocol is structural typing -- add the method, implement in both repos.

```python
# [VERIFIED: contracts/protocols.py]
# Protocol method (no default):
class Repository(Protocol):
    async def get_due_soon_setting(self) -> DueSoonSetting | None: ...

# HybridRepository: read from SQLite Settings table
# BridgeOnlyRepository: read from OPERATOR_DUE_SOON_THRESHOLD env var
```

### Pattern 5: SQLite Settings Table Read
**What:** `HybridRepository.get_due_soon_setting()` reads DueSoonInterval + DueSoonGranularity.

```python
# [VERIFIED: .research/deep-dives/direct-database-access-date-filters/6-due-soon-spike/FINDINGS.md]
# Settings table structure: key-value pairs
# SQL:
SELECT value FROM Setting WHERE key = 'DueSoonInterval'
SELECT value FROM Setting WHERE key = 'DueSoonGranularity'

# Mapping (interval_seconds -> DueSoonSetting member):
# (86400, 0) -> TWENTY_FOUR_HOURS
# (86400, 1) -> TODAY
# (172800, 1) -> TWO_DAYS
# ... etc
```

### Anti-Patterns to Avoid
- **Never use `dueSoon` column for filtering** -- excludes overdue tasks, opposite of spec. [VERIFIED: FINDINGS.md section 1]
- **Never use direct date columns** (`dateDue`, `dateToStart`, `datePlanned`) -- they're text format, `text < number` always false in SQLite. [VERIFIED: FINDINGS.md section 3]
- **Never compute "soon" as `now + interval` uniformly** -- calendar-aligned settings (6 of 7 options) anchor to midnight, not now. [VERIFIED: due-soon-spike FINDINGS.md section 4]
- **Don't touch `datetime.now(UTC)` for date resolution** -- the resolver uses naive datetimes (OmniFocus stores naive local time). The `now` captured in the pipeline should be `datetime.now()` (naive local), not UTC-aware. CF epoch conversion handles the UTC offset at the query builder layer. [ASSUMED -- needs verification against how HybridRepository stores timestamps]

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Date shortcut resolution | Custom if/elif chains | `resolve_date_filter()` | Already tested (49 tests), handles all 4 shortcuts + DateFilter objects |
| CF epoch conversion | Manual timestamp arithmetic | `(dt - _CF_EPOCH).total_seconds()` | Already established pattern in query_builder.py |
| DueSoonSetting mapping | Switch statement on interval/granularity | `DueSoonSetting` enum constructor matching | Enum already has `.days` and `.calendar_aligned` properties |

## Common Pitfalls

### Pitfall 1: Naive vs Aware Datetime Mismatch
**What goes wrong:** `resolve_date_filter()` works with naive datetimes (`datetime.now()` without tz). The Task model stores `AwareDatetime` fields. The query builder needs UTC-based CF epoch conversion. Mixing these causes comparison failures or wrong results.
**Why it happens:** Three different datetime conventions in the codebase.
**How to avoid:**
- Pipeline captures `datetime.now()` (naive local) for the resolver [ASSUMED]
- Query builder receives resolved datetimes and converts to CF epoch using `_CF_EPOCH` (UTC-based)
- Bridge path compares resolved datetimes against Task model fields (AwareDatetime)
- Key insight: the query builder's `.total_seconds()` conversion must handle timezone-aware datetimes if the resolver produces them. The existing `review_due_before` pattern uses `datetime.now(UTC)` -- need to verify the resolver's convention.
**Warning signs:** Tests pass with timezone-naive fixtures but fail against real OmniFocus data.

### Pitfall 2: "any" Shortcut Bypasses Date Resolver
**What goes wrong:** `completed: "any"` and `dropped: "any"` mean "include all tasks in that state, no date bounds." But the resolver raises `ValueError` for `"any"` -- it's not a date filter, it's a lifecycle expansion.
**Why it happens:** `"any"` is semantically different from all other shortcuts. It doesn't produce date bounds.
**How to avoid:** Pipeline must check for `"any"` before calling `resolve_date_filter()`. If `"any"`, add lifecycle availability addition only, skip date resolution.
**Warning signs:** `ValueError: 'any' on field 'completed' is not a date filter` in production.

### Pitfall 3: Lifecycle Availability Duplicates
**What goes wrong:** If agent passes both `completed: "today"` and `availability: ["completed"]`, the set-union (D-08) correctly deduplicates. But if the implementation uses list concatenation instead of set-union, duplicates cause double-counting or SQL errors.
**Why it happens:** Easy to forget set-union when appending to a list.
**How to avoid:** Use `set()` for the union: `availability_set = set(expanded) | set(lifecycle_additions)`, then convert back to list.
**Warning signs:** Duplicate availability values in the SQL WHERE clause.

### Pitfall 4: DueSoonInterval Stored as Seconds, Not Days
**What goes wrong:** OmniFocus stores `DueSoonInterval` as seconds (86400 for 1 day). If interpreted as days, the threshold would be 86400 days (~237 years).
**Why it happens:** The column name doesn't indicate the unit.
**How to avoid:** The `DueSoonSetting` enum already abstracts this -- map `(interval, granularity)` to enum members, then use `.days` property.
**Warning signs:** All tasks matching as "due soon."

### Pitfall 5: Settings Table Name
**What goes wrong:** Wrong table or column names in the SQLite query.
**Why it happens:** The table is `Setting` (singular), not `Settings`. Keys are `DueSoonInterval` and `DueSoonGranularity`.
**How to avoid:** Use exact names from the spike findings. [VERIFIED: 6-due-soon-spike/FINDINGS.md]
**Warning signs:** `no such table: Settings` error.

## Code Examples

### CF Epoch Conversion (already established)
```python
# Source: query_builder.py line 14, 220
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

# For each date dimension, same pattern:
def _add_date_conditions(
    conditions: list[str],
    params: list[Any],
    column: str,
    after: datetime | None,
    before: datetime | None,
) -> None:
    if after is not None:
        conditions.append(f"t.{column} >= ?")
        params.append((after - _CF_EPOCH).total_seconds())
    if before is not None:
        conditions.append(f"t.{column} < ?")
        params.append((before - _CF_EPOCH).total_seconds())
```

### Column Mapping Reference
```python
# [VERIFIED: 46-CONTEXT.md D-12, FINDINGS.md section 3]
DATE_COLUMN_MAP = {
    "due": "effectiveDateDue",
    "defer": "effectiveDateToStart",
    "planned": "effectiveDatePlanned",
    "completed": "effectiveDateCompleted",
    "dropped": "effectiveDateHidden",
    "added": "dateAdded",
    "modified": "dateModified",
}
```

### Bridge Field Mapping Reference
```python
# [VERIFIED: models/common.py ActionableEntity fields]
BRIDGE_FIELD_MAP = {
    "due": "effective_due_date",
    "defer": "effective_defer_date",
    "planned": "effective_planned_date",
    "completed": "effective_completion_date",  # Task-only (not on ActionableEntity)
    "dropped": "effective_drop_date",
    "added": "added",
    "modified": "modified",
}
```

### DueSoonSetting Mapping from SQLite
```python
# [VERIFIED: _enums.py DueSoonSetting values + 6-due-soon-spike/FINDINGS.md]
_SETTING_MAP: dict[tuple[int, int], DueSoonSetting] = {
    (86400, 1): DueSoonSetting.TODAY,
    (86400, 0): DueSoonSetting.TWENTY_FOUR_HOURS,
    (172800, 1): DueSoonSetting.TWO_DAYS,
    (259200, 1): DueSoonSetting.THREE_DAYS,
    (345600, 1): DueSoonSetting.FOUR_DAYS,
    (432000, 1): DueSoonSetting.FIVE_DAYS,
    (604800, 1): DueSoonSetting.ONE_WEEK,
}
```

### `OPERATOR_DUE_SOON_THRESHOLD` Env Var (Recommendation)
```python
# [ASSUMED -- Claude's discretion per CONTEXT.md]
# Recommendation: use DueSoonSetting member names (matches enum, self-documenting)
# Valid values: TODAY, TWENTY_FOUR_HOURS, TWO_DAYS, THREE_DAYS, FOUR_DAYS, FIVE_DAYS, ONE_WEEK
# Example: OPERATOR_DUE_SOON_THRESHOLD=TWO_DAYS
# If not set: get_due_soon_setting() returns None -> resolver fails fast on "soon"
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 |
| Config file | `pyproject.toml` (pytest section) |
| Quick run command | `uv run pytest tests/ -x -q --no-header` |
| Full suite command | `uv run pytest tests/ -q --no-header` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| RESOLVE-11 | `"overdue"` resolves to `effectiveDateDue < now` | unit (resolver already tested) + integration (pipeline) | `uv run pytest tests/test_resolve_dates.py::TestOverdueShortcut -x` | Resolver: yes, Pipeline: Wave 0 |
| RESOLVE-12 | `"soon"` resolves using DueSoonSetting from Settings/env | unit (resolver) + integration (pipeline + repo) | `uv run pytest tests/test_resolve_dates.py::TestSoonShortcut -x` | Resolver: yes, Pipeline+Repo: Wave 0 |
| EXEC-01 | SQL path adds date predicates on effective CF epoch columns | unit (query_builder) | `uv run pytest tests/test_query_builder.py -x` | Wave 0 |
| EXEC-02 | Bridge fallback applies identical date filtering in-memory | integration (list pipeline with bridge repo) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-03 | `completed` date filter auto-includes completed tasks | integration (pipeline lifecycle merge) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-04 | `dropped` date filter auto-includes dropped tasks | integration (pipeline lifecycle merge) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-05 | `completed: "any"` includes all completed tasks | integration (pipeline "any" handling) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-06 | `dropped: "any"` includes all dropped tasks | integration (pipeline "any" handling) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-07 | NULL dates excluded from filter results | unit (query_builder) + integration | `uv run pytest tests/test_query_builder.py tests/test_list_pipelines.py -x` | Wave 0 |
| EXEC-09 | Date filters AND with each other and base filters | integration (combined filters) | `uv run pytest tests/test_list_pipelines.py -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q --no-header`
- **Per wave merge:** `uv run pytest tests/ -q --no-header`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- [ ] Date predicate tests in `tests/test_query_builder.py` -- covers EXEC-01, EXEC-07
- [ ] Pipeline date resolution tests in `tests/test_list_pipelines.py` -- covers EXEC-02 through EXEC-06, EXEC-09
- [ ] `get_due_soon_setting()` tests for HybridRepository -- covers RESOLVE-12
- [ ] `get_due_soon_setting()` tests for BridgeOnlyRepository -- covers RESOLVE-12 env var path
- [ ] Test fixture updates: `make_task_dict()` may need `effectiveCompletionDate` and `effectiveDropDate` fields exercised in test data

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Pipeline should capture `datetime.now()` (naive local) rather than `datetime.now(UTC)` | Pitfall 1, Pattern 1 | Wrong timezone produces off-by-hours date boundaries. Medium risk -- resolver tests use naive datetimes, but CF epoch conversion at query builder uses UTC. Need to verify the full datetime flow. |
| A2 | `OPERATOR_DUE_SOON_THRESHOLD` env var should use DueSoonSetting member names (e.g., `TWO_DAYS`) | Code Examples | Low risk -- format is Claude's discretion per CONTEXT.md. Alternative: duration string like `2d`. |
| A3 | Settings table name is `Setting` (singular) | Pitfall 5 | Medium risk -- if wrong, SQLite query fails. Verified in spike findings but should be confirmed in implementation. |

## Open Questions

1. **Naive vs aware datetime flow through the pipeline**
   - What we know: `resolve_date_filter()` accepts naive datetimes (tests use `datetime(2026, 4, 7, 14, 0, 0)` without tz). Task model uses `AwareDatetime`. Query builder uses `_CF_EPOCH` (UTC-aware). The existing `review_due_before` path uses `datetime.now(UTC)`.
   - What's unclear: Should the pipeline capture `datetime.now()` or `datetime.now(UTC)`? How does the CF epoch conversion handle naive vs aware input?
   - Recommendation: Look at how `_CF_EPOCH` subtraction works with both -- `(naive_dt - aware_dt)` raises TypeError in Python 3.12. The pipeline likely needs to be timezone-aware, with the resolver operating on aware datetimes. The resolver tests may need updating. Resolve during implementation by tracing the full datetime path.

2. **InMemoryBridge `get_due_soon_setting()` wiring**
   - What we know: InMemoryBridge is the test double. It doesn't implement Repository protocol methods directly -- BridgeOnlyRepository wraps it.
   - What's unclear: How to inject configurable DueSoonSetting into tests. The conftest chain is `bridge -> BridgeOnlyRepository -> OperatorService`.
   - Recommendation: BridgeOnlyRepository reads from env var. Tests monkeypatch `OPERATOR_DUE_SOON_THRESHOLD` via `monkeypatch.setenv()`. HybridRepository reads from SQLite -- tested separately with a test database fixture.

## Sources

### Primary (HIGH confidence)
- Codebase: `service/service.py` -- full _ListTasksPipeline implementation and Method Object pattern
- Codebase: `repository/hybrid/query_builder.py` -- existing SQL builder with CF epoch conversion
- Codebase: `repository/bridge_only/bridge_only.py` -- existing bridge filtering pattern
- Codebase: `service/resolve_dates.py` -- full resolver implementation (49 passing tests)
- Codebase: `contracts/use_cases/list/tasks.py` -- ListTasksQuery and ListTasksRepoQuery definitions
- Codebase: `contracts/use_cases/list/_enums.py` -- DueSoonSetting enum with all 7 members
- Research: `.research/deep-dives/direct-database-access-date-filters/FINDINGS.md` -- column types, inheritance rates, null distributions
- Research: `.research/deep-dives/direct-database-access-date-filters/6-due-soon-spike/FINDINGS.md` -- DueSoonInterval/Granularity mapping, two-mode threshold formula

### Secondary (MEDIUM confidence)
- Phase context: `46-CONTEXT.md` -- locked decisions from discuss phase

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, pure internal wiring
- Architecture: HIGH -- all patterns have clear codebase precedents
- Pitfalls: HIGH -- database research validates all assumptions, resolver already tested
- Datetime handling: MEDIUM -- naive vs aware flow needs verification during implementation

**Research date:** 2026-04-08
**Valid until:** 2026-05-08 (stable internal codebase)
