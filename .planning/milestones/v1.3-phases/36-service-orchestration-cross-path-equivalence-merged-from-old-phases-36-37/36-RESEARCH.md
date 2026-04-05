# Phase 36: Service Orchestration + Cross-Path Equivalence - Research

**Researched:** 2026-03-31
**Domain:** Pydantic validation, duration parsing, cross-repository equivalence testing
**Confidence:** HIGH

## Summary

Phase 36 adds three things to the existing codebase: (1) input validation on query models (offset-requires-limit, review_due_within format), (2) a `ReviewDueFilter` value object that parses duration strings into structured data the service expands to datetimes, and (3) cross-path equivalence tests proving BridgeRepository and HybridRepository (SQLite) return identical results for the same queries.

All patterns already exist in the codebase. Validation follows the `repetition_rule.py` pattern (thin `@field_validator`/`@model_validator` wrappers calling `validate.py` helpers, raising `ValueError` with constants from `agent_messages/errors.py`). The `ReviewDueFilter` follows the `<noun>Filter` taxonomy (Scenario F in `docs/model-taxonomy.md`). Cross-path tests are new infrastructure but use existing seeding patterns from `tests/conftest.py` (bridge format) and `tests/test_hybrid_repository.py` (SQLite format).

**Primary recommendation:** Follow existing patterns exactly -- this is enrichment of established infrastructure, not new architecture.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01a-e:** Pydantic structural validation on query models via `@field_validator`/`@model_validator`. Validators call pure functions in `service/validate.py`. `@model_validator(mode="after")` for offset-requires-limit on `ListTasksQuery` and `ListProjectsQuery` only
- **D-02a-g:** `ReviewDueFilter` value object inheriting `QueryModel`, fields `amount: int | None` + `unit: DurationUnit | None`. `@field_validator(mode="before")` parses "1w" -> ReviewDueFilter. Pipeline expands to datetime. `ListProjectsRepoQuery` gets `review_due_before: datetime | None`
- **D-03a-d:** Invalid filter values -> `ToolError` (via `ValueError`). Error format: `"Invalid {thing} '{value}' -- valid values: {list}"`. New constants in `agent_messages/errors.py`
- **D-04a-c:** Status shorthands killed (Phase 34 D-03b)
- **D-05a-e:** Parametrized repo fixture, two seed adapters, all 5 entity types, sorted by ID before comparison, neutral test data format
- **D-06a-c:** Default completed/dropped exclusion already handled by model defaults

### Claude's Discretion
- Exact structure of seed adapters (helper functions, fixtures, conftest organization)
- Internal pipeline step organization for ReviewDueFilter expansion
- Test case selection for cross-path equivalence (which filter combinations to cover)
- Whether ReviewDueFilter expansion helper lives in `validate.py` or `domain.py`

### Deferred Ideas (OUT OF SCOPE)
- Ordering bug (pagination without deterministic ordering) -- captured as todo
- Status shorthands -- killed in Phase 34
- All write-path todos reviewed and excluded
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| INFRA-03 | Bridge fallback produces identical results to SQL path for same filters | Cross-path equivalence tests (D-05): parametrized repo fixture with seed adapters for both BridgeRepository and HybridRepository |
| INFRA-06 | Educational error messages for invalid filter values | Validation on query models (D-01, D-03): `@field_validator`/`@model_validator` raising `ValueError` with educational constants from `agent_messages/errors.py` |
</phase_requirements>

## Architecture Patterns

### Validation Flow (existing pattern)

The codebase has a well-established validation flow. Query model validators follow the same shape as `repetition_rule.py`:

1. `@field_validator` / `@model_validator` on the Pydantic model (thin wrapper)
2. Calls a pure function in `service/validate.py`
3. Raises `ValueError(CONSTANT.format(...))` with a constant from `agent_messages/errors.py`
4. Server's `_format_validation_errors()` (line 117 of `server.py`) catches `ValidationError` and extracts messages automatically

**Key files to modify:**
- `contracts/use_cases/list/tasks.py` -- add `@model_validator` for offset-requires-limit
- `contracts/use_cases/list/projects.py` -- add `@model_validator` for offset-requires-limit, change `review_due_within` type to `ReviewDueFilter | None`, add `@field_validator(mode="before")`
- `contracts/use_cases/list/projects.py` -- change `ListProjectsRepoQuery.review_due_within: str | None` to `review_due_before: datetime | None`
- `service/validate.py` -- add `validate_offset_requires_limit()`, `parse_review_due_within()`
- `agent_messages/errors.py` -- add new error constants

### ReviewDueFilter Value Object (D-02)

Follows `<noun>Filter` taxonomy (Scenario F in model-taxonomy.md):
- Lives in `contracts/use_cases/list/` (alongside the query models it nests in)
- Inherits `QueryModel`
- Fields: `amount: int | None`, `unit: DurationUnit | None` (both None for "now")
- `DurationUnit` is a small `StrEnum` with values `d`, `w`, `m`, `y`

**Parse-don't-validate:** `@field_validator(mode="before")` on `ListProjectsQuery.review_due_within` parses the raw string into `ReviewDueFilter`. If it constructs, the duration is valid.

**Expansion in pipeline:** `_ListProjectsPipeline` expands `ReviewDueFilter` to `datetime` before building the repo query. This is domain computation (amount + unit + now -> threshold), which means the helper should live in `domain.py` (context-dependent: needs `now`).

### RepoQuery Field Change

`ListProjectsRepoQuery.review_due_within: str | None` changes to `review_due_before: datetime | None`. This ripples to:
- `repository/query_builder.py` line 199-201: currently compares raw string to CF epoch float. Must change to compare CF epoch float (converted from datetime)
- `repository/bridge.py` `list_projects`: currently doesn't filter on `review_due_within` at all -- must add `review_due_before` filtering against `project.next_review_date`
- The SQL query builder already has the column reference (`pi.nextReviewDate`), just needs the parameter to be a CF epoch float instead of a raw string

### Cross-Path Equivalence Test Architecture (D-05)

```
Neutral test data (model instances or dicts)
         /                          \
seed_bridge(data)              seed_sqlite(data)
  -> InMemoryBridge              -> create_test_db()
  -> BridgeRepository            -> HybridRepository
         |                              |
   list_X(query)                 list_X(query)
         |                              |
         +------- sort by ID -----------+
         |                              |
         assert items == items
```

**Seed adapters translate neutral format to each repo's input:**
- Bridge adapter: camelCase keys, ISO dates, inline tags -- uses `make_task_dict()`, `make_project_dict()` etc. from `tests/conftest.py`
- SQLite adapter: CF epoch floats, int booleans, join tables -- uses `create_test_db()` from `tests/test_hybrid_repository.py`

**Entity coverage:** All 5 types (tasks, projects, tags, folders, perspectives)

**Sort before compare:** Both paths may return items in different order. Sort by `id` before assertion (D-05d).

### Pipeline Enrichment Points

`_ListProjectsPipeline._build_repo_query()` currently passes `review_due_within` straight through. After this phase:

1. If `query.review_due_within` is not None (now a `ReviewDueFilter`), expand to `datetime`
2. Pass `review_due_before: datetime` to `ListProjectsRepoQuery`

No changes needed to `_ListTasksPipeline` beyond the offset-requires-limit validator on the query model (which fires at construction time, before the pipeline).

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Duration parsing | Custom regex/split on "1w", "2m" | Pydantic `@field_validator(mode="before")` that constructs `ReviewDueFilter` | Parse-don't-validate: if it constructs, it's valid |
| CF epoch conversion | Manual arithmetic | `(dt - CF_EPOCH).total_seconds()` | Already established in `test_hybrid_repository.py` line 46 and query builder |
| Error message formatting | Inline strings | Constants in `agent_messages/errors.py` with `.format()` | Centralized, auditable, consistent tone |
| Validation error surfacing | Custom error handling | `_format_validation_errors()` in `server.py` | Already catches Pydantic `ValidationError` and extracts clean messages |

## Common Pitfalls

### Pitfall 1: CF Epoch vs ISO Datetime in SQL comparison
**What goes wrong:** The SQLite database stores `nextReviewDate` as CF epoch floats (seconds since 2001-01-01). If you pass an ISO string or Python datetime, the comparison silently returns wrong results.
**How to avoid:** Convert `review_due_before: datetime` to CF epoch float in the query builder: `(dt - CF_EPOCH).total_seconds()`. The `_cf_epoch()` helper in `test_hybrid_repository.py` shows the pattern.

### Pitfall 2: Bridge path missing review_due filter
**What goes wrong:** `BridgeRepository.list_projects()` currently has no `review_due_within` filtering. If the repo query field changes to `review_due_before: datetime`, the bridge path must also filter on `project.next_review_date <= threshold`.
**How to avoid:** Add the filter to `bridge.py` `list_projects()` alongside the existing availability/folder/flagged filters.

### Pitfall 3: Timezone-naive datetime comparisons
**What goes wrong:** `ReviewDueFilter` expansion computes `now + duration`. If `now` is naive and `next_review_date` is timezone-aware, comparisons fail or produce wrong results.
**How to avoid:** Use `datetime.now(UTC)` consistently. The project model has `next_review_date: AwareDatetime` (line 29 of `models/project.py`).

### Pitfall 4: Model validator on inherited QueryModel not firing
**What goes wrong:** Pydantic `@model_validator(mode="after")` must be on the concrete class, not the base. If accidentally placed on `QueryModel`, it won't fire for specific query classes.
**How to avoid:** Place `@model_validator` directly on `ListTasksQuery` and `ListProjectsQuery`. Follow `FrequencyAddSpec._check_cross_type_fields` pattern.

### Pitfall 5: Cross-path test data divergence
**What goes wrong:** Seed adapters produce subtly different data (e.g., different tag assignment, missing fields) causing false test failures.
**How to avoid:** Define test data once in neutral format (model-level dicts), then each seed adapter translates mechanically. Minimize manual data construction per adapter.

## Code Examples

### Offset-requires-limit validator (follows FrequencyAddSpec pattern)

```python
# In service/validate.py
OFFSET_REQUIRES_LIMIT = "offset requires limit -- set limit before using offset"

def validate_offset_requires_limit(limit: int | None, offset: int | None) -> None:
    if offset is not None and limit is None:
        raise ValueError(OFFSET_REQUIRES_LIMIT)

# In contracts/use_cases/list/tasks.py
from pydantic import model_validator

class ListTasksQuery(QueryModel):
    # ... existing fields ...

    @model_validator(mode="after")
    def _check_offset_requires_limit(self) -> ListTasksQuery:
        validate_offset_requires_limit(self.limit, self.offset)
        return self
```
Source: Pattern from `FrequencyAddSpec._check_cross_type_fields` in `contracts/shared/repetition_rule.py` line 83-86

### ReviewDueFilter parsing

```python
# In contracts/use_cases/list/projects.py (or a new file in same package)
class DurationUnit(StrEnum):
    DAYS = "d"
    WEEKS = "w"
    MONTHS = "m"
    YEARS = "y"

class ReviewDueFilter(QueryModel):
    amount: int | None = None  # None for "now"
    unit: DurationUnit | None = None  # None for "now"

# field_validator on ListProjectsQuery
@field_validator("review_due_within", mode="before")
@classmethod
def _parse_review_due_within(cls, v: object) -> object:
    if v is None or isinstance(v, ReviewDueFilter):
        return v
    return parse_review_due_within(str(v))  # calls validate.py helper
```
Source: Pattern from `_validate_frequency_type` in `contracts/shared/repetition_rule.py` line 39-43

### Educational error constant

```python
# In agent_messages/errors.py
REVIEW_DUE_WITHIN_INVALID = (
    "Invalid review_due_within '{value}' -- "
    "valid formats: 'now', or a number followed by d/w/m/y (e.g. '1w', '2m', '30d')"
)
```
Source: Pattern from `REPETITION_INVALID_FREQUENCY_TYPE` in `agent_messages/errors.py` line 95-98

### Cross-path equivalence test structure

```python
@pytest.fixture(params=["bridge", "sqlite"])
async def repo(request, tmp_path):
    """Parametrized fixture: same test runs against both repository implementations."""
    data = build_neutral_test_data()
    if request.param == "bridge":
        return seed_bridge_repo(data)
    else:
        return seed_sqlite_repo(data, tmp_path)

async def test_list_tasks_default(repo):
    query = ListTasksRepoQuery()
    result = await repo.list_tasks(query)
    items = sorted(result.items, key=lambda t: t.id)
    # Assert against expected items (sorted by ID)
```
Source: Standard pytest parametrization pattern

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_list_contracts.py tests/test_list_pipelines.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| INFRA-03 | Cross-path equivalence: SQL and bridge return identical results | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | Wave 0 |
| INFRA-06-a | offset-requires-limit validation on ListTasksQuery | unit | `uv run pytest tests/test_list_contracts.py -x -q -k offset` | Wave 0 |
| INFRA-06-b | offset-requires-limit validation on ListProjectsQuery | unit | `uv run pytest tests/test_list_contracts.py -x -q -k offset` | Wave 0 |
| INFRA-06-c | ReviewDueFilter parsing valid inputs | unit | `uv run pytest tests/test_list_contracts.py -x -q -k review_due` | Wave 0 |
| INFRA-06-d | ReviewDueFilter rejects invalid inputs with educational error | unit | `uv run pytest tests/test_list_contracts.py -x -q -k review_due` | Wave 0 |
| INFRA-06-e | Pipeline expands ReviewDueFilter to datetime in repo query | integration | `uv run pytest tests/test_list_pipelines.py -x -q -k review_due` | Wave 0 |
| INFRA-06-f | SQL query builder uses review_due_before datetime | unit | `uv run pytest tests/test_query_builder.py -x -q -k review_due` | Existing (needs update) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_list_contracts.py tests/test_list_pipelines.py tests/test_query_builder.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_cross_path_equivalence.py` -- new file, covers INFRA-03 (cross-path equivalence for all 5 entity types)
- [ ] Add offset-requires-limit tests to `tests/test_list_contracts.py`
- [ ] Add ReviewDueFilter parsing tests to `tests/test_list_contracts.py`
- [ ] Add ReviewDueFilter pipeline expansion tests to `tests/test_list_pipelines.py`
- [ ] Update `tests/test_query_builder.py` for `review_due_before: datetime` (existing test passes raw string, needs datetime)

## Key Observations from Codebase Audit

### Current review_due_within flow is incomplete
- `ListProjectsRepoQuery.review_due_within: str | None` passes raw strings
- Query builder (line 199-201) does `pi.nextReviewDate <= ?` with the raw string value
- `BridgeRepository.list_projects()` completely ignores `review_due_within` -- no filter at all
- Existing test in `test_hybrid_repository.py:2224` passes an ISO datetime string directly
- This phase fixes all three issues: model parses, pipeline expands to datetime, both repos filter correctly

### Seed infrastructure already exists but is split
- Bridge seeding: `make_task_dict()`, `make_project_dict()`, `make_snapshot_dict()` in `tests/conftest.py`
- SQLite seeding: `create_test_db()` in `tests/test_hybrid_repository.py` (not extracted to conftest)
- Cross-path tests will need both -- may want to extract `create_test_db` to a shared location or import it

### Pipeline doesn't need new steps
- `_ListProjectsPipeline` already has `_build_repo_query()` where the ReviewDueFilter expansion happens
- `_ListTasksPipeline` needs no pipeline changes -- offset-requires-limit fires at model construction
- No new pipeline steps needed, just enrichment of existing `_build_repo_query()`

## Sources

### Primary (HIGH confidence)
- `src/omnifocus_operator/contracts/shared/repetition_rule.py` -- validator pattern (field_validator + model_validator calling validate.py helpers)
- `src/omnifocus_operator/agent_messages/errors.py` -- educational error constant pattern
- `src/omnifocus_operator/service/service.py` -- pipeline architecture, _ReadPipeline, _ListProjectsPipeline
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` -- current ListProjectsQuery and ListProjectsRepoQuery
- `src/omnifocus_operator/repository/query_builder.py` -- current review_due_within SQL handling
- `src/omnifocus_operator/repository/bridge.py` -- current BridgeRepository list methods (missing review_due filter)
- `docs/model-taxonomy.md` -- `<noun>Filter` taxonomy, Scenario F
- `tests/test_hybrid_repository.py` -- create_test_db(), CF epoch helpers, existing list tests
- `tests/conftest.py` -- make_task_dict(), make_project_dict(), bridge-format factories

### Secondary (MEDIUM confidence)
- `docs/architecture.md` -- three-layer validation principle (referenced in CONTEXT.md)
- `docs/structure-over-discipline.md` -- validate.py vs domain.py boundary

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all within existing Pydantic + pytest
- Architecture: HIGH -- all patterns exist in codebase, this is enrichment
- Pitfalls: HIGH -- identified from direct code audit (CF epoch comparison, missing bridge filter, timezone)

**Research date:** 2026-03-31
**Valid until:** 2026-04-30 (stable codebase, no external dependencies)
