# Phase 35: SQL Repository - Research

**Researched:** 2026-03-30
**Domain:** SQLite repository list methods -- wiring query builder + row mappers into HybridRepository
**Confidence:** HIGH

## Summary

Phase 35 adds 5 `list_*` methods to `HybridRepository` in `repository/hybrid.py`. The building blocks are already in place: Phase 34 delivered the query builder (`build_list_tasks_sql`, `build_list_projects_sql`), the query models (`ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery`), the result container (`ListResult[T]`), and the protocol signatures. The existing `_read_all()` method establishes the pattern for connection management, lookup table building, and row mapping.

The two-plan split (D-04) is well-justified: Plan 1 (tasks + projects) involves query builder integration, full lookup tables, pagination, and `hasMore` computation. Plan 2 (tags + folders + perspectives) is simpler -- fetch-all + Python filter, no lookups, no pagination.

**Primary recommendation:** Follow the `_read_all()` pattern exactly -- fresh read-only connection, `asyncio.to_thread`, reuse existing row mappers unchanged. The only new code is the glue: executing query builder output, building lookup tables, computing `ListResult` fields.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01a:** Tags and folders use fetch-all + Python filter, NOT the query builder
- **D-01b:** Reuse existing `_TAGS_SQL` and `_FOLDERS_SQL` constants
- **D-01c:** Filter availability in Python after fetching all rows
- **D-01d:** query_builder.py stays focused on complex entities (tasks, projects)
- **D-01e:** Migrate tags/folders to query_builder only if they gain more filters
- **D-02a:** `list_tasks` and `list_projects` build full lookup tables (same as `_read_all()`)
- **D-02b:** Reuse existing lookup-building code: tag_name_lookup, task_tag_map, project_info_lookup, task_name_lookup
- **D-02c:** Row mappers called unchanged -- same signature, same behavior
- **D-02d:** Full table scans for lookups are sub-millisecond at current scale
- **D-02e:** Tags, folders, perspectives need zero lookup tables
- **D-03a:** Automated comparative test: filtered query vs full `get_all()`, assert filtered is faster
- **D-03b:** Seed test database with ~200 rows for meaningful performance gap
- **D-03c:** UAT note for real-database gap (~6ms filtered vs ~46ms full snapshot)
- **D-03d:** No hard timing thresholds (machine-dependent, CI-flaky)
- **D-04a:** Two plans split by complexity
- **D-04b:** Plan 1: `list_tasks` + `list_projects` (query builder, lookups, pagination, ~150+ tests)
- **D-04c:** Plan 2: `list_tags` + `list_folders` + `list_perspectives` (fetch-all, Python filter, ~30 tests)

### Claude's Discretion
- Internal organization of list method sync helpers (`_list_tasks_sync`, etc.)
- Exact `hasMore` computation formula (likely `offset + len(items) < total`)
- Whether lookup-building code is extracted into shared helpers or duplicated
- Test fixture design for the ~200 row performance seed
- How perspectives plist data flows through `list_perspectives`

### Deferred Ideas (OUT OF SCOPE)
- None -- discussion stayed within phase scope
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TASK-01 | List tasks filtered by inbox status | `in_inbox` filter handled by query builder `t.inInbox = ?` clause |
| TASK-02 | List tasks filtered by flagged status | `flagged` filter handled by query builder `t.flagged = ?` clause |
| TASK-03 | List tasks filtered by project name (case-insensitive partial match) | `project` filter uses subquery on ProjectInfo + LIKE COLLATE NOCASE |
| TASK-04 | List tasks filtered by tags (OR logic) | `tags` filter uses IN subquery on TaskToTag; service resolves names to IDs |
| TASK-05 | List tasks filtered by has_children | **DROPPED** per Phase 34 D-11 -- deferred, no agent use case |
| TASK-06 | List tasks filtered by estimated_minutes_max | `estimated_minutes_max` filter uses `t.estimatedMinutes <= ?` |
| TASK-07 | List tasks filtered by availability | Availability clause uses static lookup dict, no user params |
| TASK-08 | Search tasks by substring in name/notes | `search` filter uses LIKE on `t.name` and `t.plainTextNote` |
| TASK-09 | Paginate task results with limit/offset | Query builder appends `LIMIT ?` / `OFFSET ?` params |
| TASK-10 | Combine multiple task filters with AND logic | Query builder ANDs all conditions in WHERE clause |
| TASK-11 | Completed/dropped excluded by default | Default availability `[available, blocked]` on ListTasksQuery |
| PROJ-01 | List projects filtered by status | Availability clause covers active/blocked/completed/dropped |
| PROJ-02 | Status shorthands (remaining, available, all) | **REPLACED** by concrete availability enum values per Phase 34 D-03 |
| PROJ-03 | Default returns remaining (active + on_hold) | Default availability `[available, blocked]` on ListProjectsQuery |
| PROJ-04 | List projects filtered by folder name | `folder` filter uses subquery on Folder + LIKE COLLATE NOCASE |
| PROJ-05 | List projects with reviews due within duration | `review_due_within` uses `pi.nextReviewDate <= ?` (service resolves duration to timestamp) |
| PROJ-06 | List projects filtered by flagged status | `flagged` filter uses `t.flagged = ?` |
| PROJ-07 | Paginate project results with limit/offset | Same LIMIT/OFFSET pattern as tasks |
| BROWSE-01 | List tags filtered by availability | Fetch all + Python filter on TagAvailability enum |
| BROWSE-02 | List folders filtered by availability | Fetch all + Python filter on FolderAvailability enum |
| BROWSE-03 | List perspectives (all, with builtin flag) | Fetch all via _PERSPECTIVES_SQL, map with _map_perspective_row, builtin is computed field |
| INFRA-02 | Filtered queries measurably faster than full snapshot | Comparative pytest: filtered vs get_all(), assert filtered faster, ~200 row seed |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: No automated tests touch the real Bridge. All testing uses InMemoryBridge or SimulatorBridge. Repository tests use in-memory SQLite via `create_test_db()`.
- **Method Object pattern**: Not applicable to this phase (list methods are read delegations, not use case pipelines).
- **Model conventions**: Read `docs/architecture.md` naming taxonomy before creating any new model. Models in `models/` use no suffix or `Read` suffix.
- **Output schema test**: Run `uv run pytest tests/test_output_schema.py -x -q` after modifying any model that appears in tool output.

## Architecture Patterns

### Where the New Code Lives

```
src/omnifocus_operator/
    repository/
        hybrid.py              # ADD: 5 async list_* methods + sync helpers
        query_builder.py       # EXISTING: build_list_tasks_sql, build_list_projects_sql
    contracts/
        use_cases/
            list_entities.py   # EXISTING: query models, ListResult[T]
        protocols.py           # EXISTING: list_* signatures already declared
```

### Pattern: Sync Helper + Async Wrapper

Every existing read method follows this pattern. New list methods MUST follow it:

```python
# Async public method
async def list_tasks(self, query: ListTasksQuery) -> ListResult[Task]:
    return await asyncio.to_thread(self._list_tasks_sync, query)

# Sync helper (all SQLite work)
def _list_tasks_sync(self, query: ListTasksQuery) -> ListResult[Task]:
    conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Build lookup tables (same as _read_all)
        # 2. Execute query builder SQL
        # 3. Map rows -> models
        # 4. Compute ListResult
    finally:
        conn.close()
```

### Pattern: Lookup Table Building (tasks and projects only)

Reuse from `_read_all()` lines 534-567. Four lookups needed:

1. **tag_name_lookup**: `dict[str, str]` -- tag ID -> tag name. From `SELECT * FROM Context`.
2. **task_tag_map**: `dict[str, list[dict[str, str]]]` -- task ID -> list of `{id, name}`. From `SELECT task, tag FROM TaskToTag`.
3. **project_info_lookup**: `dict[str, dict[str, str]]` -- ProjectInfo PK -> `{id, name}`. From `SELECT pi.pk, pi.task, t.name FROM ProjectInfo pi JOIN Task t ON pi.task = t.persistentIdentifier`.
4. **task_name_lookup**: `dict[str, str]` -- task ID -> name. From `SELECT persistentIdentifier, name FROM Task`. Only needed for `list_tasks` (parent task name resolution).

Decision D-02a: build ALL lookups (full table scans), not filtered subsets. At ~64 tags, ~363 projects, ~2,400 tasks this is sub-millisecond.

### Pattern: Fetch-All + Python Filter (tags, folders)

```python
def _list_tags_sync(self, query: ListTagsQuery) -> ListResult[Tag]:
    conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_TAGS_SQL).fetchall()
        all_tags = [Tag.model_validate(_map_tag_row(row)) for row in rows]
        # Python filter on availability
        avail_set = set(query.availability)
        filtered = [t for t in all_tags if t.availability in avail_set]
        return ListResult(items=filtered, total=len(filtered), has_more=False)
    finally:
        conn.close()
```

### Pattern: ListResult Construction

```python
# Paginated (tasks, projects)
items = [Task.model_validate(_map_task_row(row, ...)) for row in data_rows]
total = count_row[0]
offset = query.offset or 0
has_more = (offset + len(items)) < total
return ListResult(items=items, total=total, has_more=has_more)

# Non-paginated (tags, folders, perspectives)
return ListResult(items=filtered, total=len(filtered), has_more=False)
```

### Anti-Patterns to Avoid

- **Do NOT filter lookups to match data query results.** Always build full lookups. A task's parent might be a project not in the filtered result set -- the lookup must still have it.
- **Do NOT create new row mappers.** Reuse `_map_task_row`, `_map_project_row`, `_map_tag_row`, `_map_folder_row`, `_map_perspective_row` unchanged.
- **Do NOT add `_ensures_write_through` decorator.** List methods are read-only -- no write staleness concern.
- **Do NOT modify `_read_all()`.** It continues to serve `get_all()`. The new list methods are parallel, not replacement.

### Critical Code Discrepancy

The CONTEXT.md states `_map_project_row(row, tag_map, project_lookup)` but the **actual** signature is:

```python
def _map_project_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
```

Only 2 parameters, not 3. The executor MUST use the actual 2-param signature. Project rows already contain all needed columns via the JOIN.

### Shared Helper Extraction (discretion area)

The 4 lookup-building queries are duplicated between `_read_all()` and the new list methods. Options:
- **Extract**: Create `_build_tag_name_lookup(conn)`, `_build_task_tag_map(conn, tag_name_lookup)`, etc. Reduces duplication, ~4 small functions.
- **Duplicate**: Copy the 4 query blocks. Simpler, fewer indirections.

Recommendation: **Extract** into private module-level or class-level helpers. The `_list_tasks_sync` and `_list_projects_sync` both need 3-4 of the same lookups, so extraction pays for itself immediately.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| SQL generation with filters | String concatenation with filter conditions | `build_list_tasks_sql()` / `build_list_projects_sql()` | Phase 34 already built this -- parameterized, tested, injection-safe |
| Row-to-model mapping | New mapping functions | Existing `_map_*_row()` functions | Proven, tested, handle all edge cases (timestamps, plist, parent refs) |
| Availability filtering for tags/folders | SQL WHERE clauses | Python `in` check against enum set | D-01a: ~64 tags / ~79 folders -- SQL filtering adds complexity for zero gain |
| Test database creation | Manual SQLite setup | `create_test_db()` from test_hybrid_repository.py | Schema already defined, insert helpers for all entity types |

## Common Pitfalls

### Pitfall 1: Forgetting tag_name_lookup When Building task_tag_map
**What goes wrong:** task_tag_map entries have empty tag names because tag_name_lookup wasn't built first.
**Why it happens:** The lookup order matters: Context table -> TaskToTag join -> task_tag_map.
**How to avoid:** Always build tag_name_lookup BEFORE task_tag_map, exactly as `_read_all()` does.
**Warning signs:** Task tags appear as `[{id: "abc", name: ""}]` instead of `[{id: "abc", name: "Work"}]`.

### Pitfall 2: Count Query Including LIMIT/OFFSET
**What goes wrong:** `total` reflects the page size, not the total matching count.
**Why it happens:** Using the data query for COUNT instead of the separate count query.
**How to avoid:** The query builder returns `(data_query, count_query)` as a tuple. The count query never has LIMIT/OFFSET. Use `count_query` for the total.
**Warning signs:** `total` equals `len(items)` for every response.

### Pitfall 3: Availability Filter on Tags Using Wrong Enum
**What goes wrong:** Tags accept `Availability.COMPLETED` which doesn't exist for tags.
**Why it happens:** Using `Availability` enum instead of `TagAvailability` for comparison.
**How to avoid:** The query model already uses the correct enum type (`ListTagsQuery.availability: list[TagAvailability]`). The Python filter should compare against the `Tag.availability` string value, which is already typed as `TagAvailability`.
**Warning signs:** Pydantic validation error or incorrect filtering.

### Pitfall 4: Perspectives With No valueData
**What goes wrong:** `_map_perspective_row` returns `name: ""` for perspectives with null `valueData`.
**Why it happens:** Built-in perspectives may have null valueData in the Perspective table.
**How to avoid:** This is correct behavior -- builtin perspectives have `id=None` and may have empty names. The `Perspective.builtin` computed field handles the distinction.
**Warning signs:** None -- this is expected.

### Pitfall 5: Performance Test Flakiness
**What goes wrong:** Comparative timing test fails on CI or slow machines.
**Why it happens:** Absolute timing thresholds are machine-dependent.
**How to avoid:** D-03d says no hard timing thresholds. Compare filtered vs full-snapshot timing **relatively**: `assert filtered_time < full_time`. Seed with ~200 rows (D-03b) to create a meaningful gap even on in-memory SQLite.
**Warning signs:** Test passes locally but fails in CI.

### Pitfall 6: offset Without limit
**What goes wrong:** Query builder silently ignores offset when limit is None.
**Why it happens:** SQL requires LIMIT before OFFSET. The query builder correctly ignores offset-without-limit.
**How to avoid:** This is correct behavior -- the query model allows it, but the SQL builder handles it safely. No special repository handling needed.
**Warning signs:** None -- this is by design.

## Code Examples

### list_tasks Sync Helper (sketch)

```python
def _list_tasks_sync(self, query: ListTasksQuery) -> ListResult[Task]:
    """Synchronous list_tasks implementation."""
    conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        # 1. Build lookup tables (full scans)
        tag_name_lookup = _build_tag_name_lookup(conn)
        task_tag_map = _build_task_tag_map(conn, tag_name_lookup)
        project_info_lookup = _build_project_info_lookup(conn)
        task_name_lookup = _build_task_name_lookup(conn)

        # 2. Execute query builder SQL
        data_q, count_q = build_list_tasks_sql(query)
        data_rows = conn.execute(data_q.sql, data_q.params).fetchall()
        count_row = conn.execute(count_q.sql, count_q.params).fetchone()

        # 3. Map rows -> validated models
        tasks = [
            Task.model_validate(
                _map_task_row(row, task_tag_map, project_info_lookup, task_name_lookup)
            )
            for row in data_rows
        ]

        # 4. Compute ListResult
        total = count_row[0]
        offset = query.offset or 0
        has_more = (offset + len(tasks)) < total

        return ListResult(items=tasks, total=total, has_more=has_more)
    finally:
        conn.close()
```

### list_perspectives (sketch)

```python
def _list_perspectives_sync(self) -> ListResult[Perspective]:
    """Synchronous list_perspectives implementation."""
    conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
    conn.row_factory = sqlite3.Row
    try:
        rows = conn.execute(_PERSPECTIVES_SQL).fetchall()
        perspectives = [
            Perspective.model_validate(_map_perspective_row(row))
            for row in rows
        ]
        return ListResult(
            items=perspectives,
            total=len(perspectives),
            has_more=False,
        )
    finally:
        conn.close()
```

### Performance Comparison Test (sketch)

```python
@pytest.mark.asyncio
async def test_filtered_query_faster_than_full_snapshot(hybrid_repo):
    """INFRA-02: Filtered SQL measurably faster than full snapshot."""
    import time

    # Filtered query (single filter)
    query = ListTasksQuery(flagged=True)
    start = time.perf_counter()
    filtered_result = await hybrid_repo.list_tasks(query)
    filtered_time = time.perf_counter() - start

    # Full snapshot
    start = time.perf_counter()
    full_result = await hybrid_repo.get_all()
    full_time = time.perf_counter() - start

    assert filtered_time < full_time
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_hybrid_repository.py -x -q` |
| Full suite command | `uv run pytest -x -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TASK-01 | Inbox filter returns only inbox/non-inbox tasks | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and inbox" -x` | Wave 0 |
| TASK-02 | Flagged filter returns only flagged/unflagged tasks | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and flagged" -x` | Wave 0 |
| TASK-03 | Project filter partial match, case-insensitive | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and project" -x` | Wave 0 |
| TASK-04 | Tags filter OR logic | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and tags" -x` | Wave 0 |
| TASK-05 | has_children filter | n/a | n/a | DROPPED (D-11) |
| TASK-06 | Estimated minutes max filter | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and estimated" -x` | Wave 0 |
| TASK-07 | Availability filter | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and availability" -x` | Wave 0 |
| TASK-08 | Search substring in name+notes | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and search" -x` | Wave 0 |
| TASK-09 | Pagination with limit/offset | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and limit" -x` | Wave 0 |
| TASK-10 | Combined filters AND logic | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and combined" -x` | Wave 0 |
| TASK-11 | Default excludes completed/dropped | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tasks and default" -x` | Wave 0 |
| PROJ-01 | Availability filter on projects | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and availability" -x` | Wave 0 |
| PROJ-02 | (replaced by availability enum values) | n/a | n/a | Covered by PROJ-01 |
| PROJ-03 | Default returns remaining projects | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and default" -x` | Wave 0 |
| PROJ-04 | Folder filter partial match | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and folder" -x` | Wave 0 |
| PROJ-05 | Review due within filter | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and review" -x` | Wave 0 |
| PROJ-06 | Flagged filter on projects | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and flagged" -x` | Wave 0 |
| PROJ-07 | Pagination on projects | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_projects and limit" -x` | Wave 0 |
| BROWSE-01 | Tags filtered by availability | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_tags" -x` | Wave 0 |
| BROWSE-02 | Folders filtered by availability | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_folders" -x` | Wave 0 |
| BROWSE-03 | List all perspectives | unit | `uv run pytest tests/test_hybrid_repository.py -k "list_perspectives" -x` | Wave 0 |
| INFRA-02 | Filtered faster than full snapshot | unit | `uv run pytest tests/test_hybrid_repository.py -k "performance" -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_hybrid_repository.py -x -q`
- **Per wave merge:** `uv run pytest -x -q`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- All tests are new -- no existing test infrastructure gaps. The `create_test_db()` helper and `hybrid_db`/`hybrid_repo` fixtures already exist and support the `@pytest.mark.hybrid_db(...)` marker pattern.
- No new framework installs needed.
- The ~200-row performance seed is new fixture data needed for INFRA-02.

## Test Architecture Notes

### Fixture Pattern
All tests use `@pytest.mark.hybrid_db(...)` marker -> `hybrid_db` fixture -> `hybrid_repo` fixture chain:

```python
@pytest.mark.asyncio
@pytest.mark.hybrid_db(
    tasks=[_minimal_task({"flagged": 1}), _minimal_task({"persistentIdentifier": "t2"})],
    tags=[_minimal_tag()],
)
async def test_list_tasks_flagged(self, hybrid_repo: HybridRepository) -> None:
    result = await hybrid_repo.list_tasks(ListTasksQuery(flagged=True))
    assert len(result.items) == 1
    assert result.items[0].flagged is True
```

### Test Organization Per Plan
- **Plan 1** tests go in `tests/test_hybrid_repository.py` (extending existing file) -- classes like `TestListTasks*`, `TestListProjects*`, `TestListPerformance`
- **Plan 2** tests also go in `tests/test_hybrid_repository.py` -- classes like `TestListTags`, `TestListFolders`, `TestListPerspectives`

### Performance Test Seeding
The ~200 row seed for INFRA-02 needs:
- ~150 tasks with varied attributes (flagged, projects, tags, availability states)
- ~30 projects with varied folders and availability
- ~15 tags
- ~5 folders
- A handful of perspectives
- TaskToTag join rows connecting tasks to tags

Use a helper function that generates these programmatically rather than listing 200 dict literals.

## Sources

### Primary (HIGH confidence)
- `src/omnifocus_operator/repository/hybrid.py` -- existing patterns for connection management, lookup building, row mapping
- `src/omnifocus_operator/repository/query_builder.py` -- Phase 34 SQL generation (verified, 47 tests passing)
- `src/omnifocus_operator/contracts/use_cases/list_entities.py` -- query models and ListResult[T]
- `src/omnifocus_operator/contracts/protocols.py` -- list method signatures on Repository protocol
- `tests/test_hybrid_repository.py` -- existing test patterns (79 tests passing)
- `tests/test_query_builder.py` -- query builder test patterns (47 tests passing)
- `.planning/phases/34-contracts-and-query-foundation/34-CONTEXT.md` -- all contract decisions

### Secondary (MEDIUM confidence)
- `.planning/phases/35-sql-repository/35-CONTEXT.md` -- implementation decisions (user-approved)

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing code
- Architecture: HIGH -- pattern is established by `_read_all()`, proven by 79 existing tests
- Pitfalls: HIGH -- identified from actual code inspection, not speculation

**Research date:** 2026-03-30
**Valid until:** 2026-04-30 (stable -- no external dependencies to go stale)
