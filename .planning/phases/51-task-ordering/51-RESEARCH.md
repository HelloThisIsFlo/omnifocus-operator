# Phase 51: Task Ordering - Research

**Researched:** 2026-04-12
**Domain:** SQLite CTE-based ordering, Pydantic model extension, query builder modification
**Confidence:** HIGH

## Summary

This phase adds a read-only `order` field (dotted string notation like `"2.3.1"`) to Task responses and ensures all read operations return tasks in correct OmniFocus outline order. The technical solution is fully validated -- a recursive CTE building a `sort_path` from rank values at each depth level reproduces exact OmniFocus UI order, verified against real data in the deep dive (3062 tasks, 4 nesting levels, ~5ms performance).

The implementation touches four layers: Task model (add field), query builder (prepend CTE, change ORDER BY), hybrid repository (pass `order` through row mapper), and bridge-only repository (set `order=None` for degraded mode). The `order` field is inherently read-only because `EditTaskCommand` uses `extra="forbid"` -- any field not explicitly declared is rejected.

**Primary recommendation:** Follow the CTE solution from the deep dive verbatim. The hard problem (correct ordering from SQLite) is solved. This phase is pure integration work.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01: Dotted notation** -- `order` is `str | None`, not `int`. Format: `"1"`, `"1.2"`, `"2.3.1"`. Per-project/inbox namespace (each starts at "1"). Build dotted path in recursive CTE.
- **D-02: All read operations** -- `get_task`, `list_tasks`, `get_all` all include `order`. One model shape everywhere.
- **D-03: Bridge-only degradation** -- HybridRepository returns `str`, BridgeOnlyRepository returns `None`. Honest signal of degraded mode.
- **D-04: Tool description updates** -- Brief note on `list_tasks`, `get_task`, `get_all` explaining dotted notation and sparse values in filtered results.
- **D-05: Cross-path equivalence** -- `order` is a known divergence (str vs None). Cross-path tests must exclude `order` from comparison.

### Claude's Discretion
- Exact SQL for building dotted path (string concatenation in CTE)
- Whether to extract CTE as a shared constant or inline per query
- Test strategy for order field validation
- Count query optimization (exclude CTE if simple, include if code duplication required)
- How to exclude `order` from cross-path equivalence comparison

### Deferred Ideas (OUT OF SCOPE)
- Add `order` field to Project/Folder/Tag entities -- evaluate after task ordering ships
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| ORDER-01 | Task responses include an `order` field reflecting position within parent | Add `order: str \| None` to Task model; CTE computes dotted path; `_map_task_row` extracts it |
| ORDER-02 | Siblings under same parent have sequential, gap-free order values (1, 2, 3...) | Dotted notation uses `ROW_NUMBER() OVER (PARTITION BY parent ORDER BY rank)` per level, producing 1-based ordinals |
| ORDER-03 | `order` field is read-only -- not settable via edit_tasks | `EditTaskCommand` inherits `CommandModel` (`extra="forbid"`) -- `order` not declared, so it's automatically rejected |
| ORDER-04 | Tasks returned in outline order -- siblings grouped, depth respected | Recursive CTE with `sort_path` produces depth-first traversal matching OmniFocus UI; replaces current `ORDER BY t.persistentIdentifier` |
| ORDER-05 | Inbox tasks sort after projects in get_all/list_tasks | Inbox CTE anchor uses `ZZZZZZZZZZ/` prefix in sort_path (Strategy B from deep dive, validated at 6ms) |
</phase_requirements>

## Project Constraints (from CLAUDE.md)

- **SAFE-01/02**: All tests use `InMemoryBridge` or `SimulatorBridge`. No `RealBridge` in tests/CI.
- **Model conventions**: Read `docs/model-taxonomy.md` before creating models. `order` goes on `Task` in `models/task.py` (core model, no suffix).
- **Output schema test**: After modifying Task model, run `uv run pytest tests/test_output_schema.py -x -q` to verify serialized output validates against MCP outputSchema.
- **Agent-facing descriptions**: All field descriptions go in `agent_messages/descriptions.py` as constants. Use `Field(description=CONSTANT)` pattern.
- **Service layer**: Read delegations stay inline (one-liner pass-throughs). No pipeline needed for this read-only field.

## Architecture Patterns

### Where Each Change Lives

```
models/task.py                          # Add order: str | None field
agent_messages/descriptions.py          # Add ORDER_FIELD description constant
                                        # Update tool descriptions (get_task, list_tasks, get_all)
repository/hybrid/query_builder.py      # CTE constant, modify build_list_tasks_sql()
repository/hybrid/hybrid.py             # Modify _map_task_row(), _read_all(), _read_task(),
                                        #   _list_tasks_sync()
repository/bridge_only/bridge_only.py   # No changes needed (order=None comes from adapter)
repository/bridge_only/adapter.py       # Set order=None on adapted tasks
tests/conftest.py                       # Add order to make_model_task_dict() and make_task_dict()
tests/test_cross_path_equivalence.py    # Exclude order from assert_equivalent()
tests/test_output_schema.py             # Will auto-validate (uses Task model)
```

### CTE Integration Pattern

The CTE must be prepended to the existing query structure. Current `build_list_tasks_sql()` returns `(data_query, count_query)`. The CTE applies to `data_query` only -- `count_query` does not need ordering.

```
Current data query:        SELECT t.* FROM Task t LEFT JOIN ... WHERE ... ORDER BY t.persistentIdentifier
After CTE:                 WITH RECURSIVE task_order(...) AS (...) SELECT t.*, <order_expr> FROM Task t LEFT JOIN ... JOIN task_order o ON ... WHERE ... ORDER BY o.sort_path
```

### Dotted Path Computation

Two approaches for computing the dotted path from `sort_path`:

**Option A: Compute in SQL** -- Use a window function `ROW_NUMBER() OVER (PARTITION BY t.parent ORDER BY t.rank)` at each CTE level, concatenate ordinals with dots. This produces the final `"2.3.1"` string directly in SQL.

**Option B: Compute in Python** -- CTE provides `sort_path` for ordering only; Python computes dotted ordinals from the parent/rank relationships in the result set. Simpler SQL, but requires post-processing.

**Recommendation: Option A** -- compute in SQL. The CTE already traverses the hierarchy; adding `ROW_NUMBER()` at each level is natural. Avoids a second pass in Python. The CTE can carry both `sort_path` (for ORDER BY) and `dotted_order` (for the `order` field).

### CTE Design (Dotted Path + Sort Path)

```sql
WITH RECURSIVE task_order(id, sort_path, dotted_order, depth) AS (
    -- Anchor: project-root tasks
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + 2147483648),
           CAST(ROW_NUMBER() OVER (ORDER BY t.rank) AS TEXT),
           0
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    -- Anchor: inbox root tasks (sorted after projects)
    SELECT t.persistentIdentifier,
           'ZZZZZZZZZZ/' || printf('%010d', t.rank + 2147483648),
           CAST(ROW_NUMBER() OVER (ORDER BY t.rank) AS TEXT),
           0
    FROM Task t
    WHERE t.parent IS NULL
      AND t.containingProjectInfo IS NULL
      AND t.persistentIdentifier NOT IN (SELECT pi2.task FROM ProjectInfo pi2)

    UNION ALL

    -- Recursive: children
    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + 2147483648),
           o.dotted_order || '.' || CAST(
               ROW_NUMBER() OVER (PARTITION BY t.parent ORDER BY t.rank) AS TEXT
           ),
           o.depth + 1
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
```

**Important caveat**: SQLite's recursive CTE has limitations with window functions. `ROW_NUMBER()` inside `UNION ALL` branches may not work as expected in all SQLite versions. The deep dive CTE uses `sort_path` only. If window functions in recursive CTEs cause issues, fall back to computing ordinals in Python from the sorted result set (Option B).

[ASSUMED] -- SQLite window functions inside recursive CTE branches work correctly. If not, compute dotted ordinals in Python post-sort.

### get_task: Ancestor Chain for Dotted Path

`_read_task()` fetches a single task by ID. To produce the dotted path, it needs the full ancestor chain. Two approaches:

**Approach 1: Run the full CTE** for the task's project, then look up the single task's `dotted_order`. The CTE is ~5ms for the full DB, and scoped to one project it would be faster.

**Approach 2: Walk ancestors in Python** -- query parent chain (`parent -> parent -> ... -> project root`), compute ordinal at each level via `ROW_NUMBER()` equivalent (`SELECT COUNT(*) FROM Task WHERE parent = ? AND rank <= ?`).

**Recommendation: Approach 1** -- run the CTE scoped to the task's project/inbox namespace. Simpler, consistent with list path, ~1-2ms for a single project tree.

### Anti-Patterns to Avoid
- **Do not add `order` to `EditTaskCommand`** -- it's read-only by design. The `extra="forbid"` base class handles rejection.
- **Do not compute `order` in BridgeOnlyRepository** -- it lacks rank data. Return `None` honestly.
- **Do not use flat `ORDER BY rank`** -- verified in deep dive that this interleaves tasks from different depths nonsensically.
- **Do not modify the count query with CTE** -- count doesn't need ordering. Unnecessary overhead.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Outline ordering from SQLite | Custom sort algorithm | Recursive CTE with sort_path | Verified solution from deep dive, handles edge cases (negatives, gaps, action groups) |
| Gap-free ordinals | Manual counting in Python | ROW_NUMBER() OVER (PARTITION BY parent ORDER BY rank) | SQL window function is exact and handles edge cases |
| Rank-to-unsigned conversion | Custom math | `printf('%010d', rank + 2147483648)` | Proven formula from deep dive, handles full 32-bit range |

## Common Pitfalls

### Pitfall 1: Window Functions in Recursive CTE
**What goes wrong:** SQLite may not support `ROW_NUMBER()` inside `UNION ALL` branches of a recursive CTE.
**Why it happens:** Recursive CTEs process rows incrementally; window functions need the full partition.
**How to avoid:** Test early. If it fails, compute dotted ordinals in Python from the sorted result set. The sort_path CTE works regardless.
**Warning signs:** SQL error or incorrect ordinal values in recursive step output.

### Pitfall 2: Cross-Path Equivalence Test Breakage
**What goes wrong:** 32 parametrized tests fail because HybridRepository now returns `order="2.3.1"` while BridgeOnlyRepository returns `order=None`.
**Why it happens:** `assert_equivalent()` compares full model instances.
**How to avoid:** Modify `assert_equivalent()` to exclude `order` from comparison. Use `model_dump(exclude={"order"})` or sort items by ID and compare field-by-field excluding `order`.
**Warning signs:** Test failures in `test_cross_path_equivalence.py` immediately after adding the field.

### Pitfall 3: Output Schema Drift
**What goes wrong:** Adding `order` to Task changes the MCP outputSchema. If the field isn't properly typed/described, schema validation tests fail.
**Why it happens:** FastMCP auto-generates JSON Schema from Pydantic models. New fields appear automatically.
**How to avoid:** Run `uv run pytest tests/test_output_schema.py -x -q` after adding the field. Ensure `order: str | None` with proper `Field(description=...)`.
**Warning signs:** `test_output_schema.py` failures.

### Pitfall 4: get_task Missing Ancestor Context
**What goes wrong:** `_read_task()` returns `order=None` because it doesn't have the ancestor chain to compute the dotted path.
**Why it happens:** Current `_read_task()` fetches only the single task row + immediate parent lookup. Dotted path requires the full hierarchy.
**How to avoid:** Run a scoped CTE (anchored at the task's project) when reading a single task, or walk the ancestor chain with separate queries.
**Warning signs:** `get_task` returning `None` for `order` on HybridRepository when `list_tasks` returns a valid string.

### Pitfall 5: Inbox Namespace Collision
**What goes wrong:** Inbox tasks get order values that collide with project tasks (e.g., both have `"1"` as order).
**Why it happens:** Without per-namespace numbering, inbox and project root ordinals overlap.
**How to avoid:** Per-project/inbox namespace is the design (D-01). Each project and inbox starts at "1". The `project` field on the task disambiguates.
**Warning signs:** Duplicate order values across different projects (which is actually correct -- namespaced).

### Pitfall 6: Test Factory Defaults
**What goes wrong:** Existing tests break because Task model now requires `order` but test factories don't provide it.
**Why it happens:** `make_model_task_dict()` and `make_task_dict()` don't include `order`.
**How to avoid:** Add `order: None` to both factory defaults. This is the safe default (bridge-compatible). Tests that need specific order values override explicitly.
**Warning signs:** `ValidationError: field required` across many test files.

## Code Examples

### Task Model Addition

```python
# Source: models/task.py -- add order field
# Per CONTEXT.md D-01: dotted string notation, str | None
from omnifocus_operator.agent_messages.descriptions import ORDER_FIELD

class Task(ActionableEntity):
    __doc__ = TASK_DOC

    order: str | None = Field(default=None, description=ORDER_FIELD)
    # ... existing fields ...
```

[VERIFIED: codebase] -- Task model location and pattern confirmed from `models/task.py`.

### CTE Constant in query_builder.py

```python
# Source: deep dive RESULTS.md -- validated CTE solution
_TASK_ORDER_CTE = (
    "WITH RECURSIVE task_order(id, sort_path) AS ("
    "  SELECT t.persistentIdentifier,"
    "         printf('%010d', t.rank + 2147483648)"
    "  FROM Task t"
    "  JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task"
    "  UNION ALL"
    "  SELECT t.persistentIdentifier,"
    "         'ZZZZZZZZZZ/' || printf('%010d', t.rank + 2147483648)"
    "  FROM Task t"
    "  WHERE t.parent IS NULL"
    "    AND t.containingProjectInfo IS NULL"
    "    AND t.persistentIdentifier NOT IN (SELECT pi2.task FROM ProjectInfo pi2)"
    "  UNION ALL"
    "  SELECT t.persistentIdentifier,"
    "         o.sort_path || '/' || printf('%010d', t.rank + 2147483648)"
    "  FROM Task t"
    "  JOIN task_order o ON t.parent = o.id"
    ") "
)
```

[VERIFIED: deep dive RESULTS.md] -- CTE structure and inbox strategy validated against real data.

### _map_task_row Update

```python
# Source: hybrid.py -- add order to task dict
def _map_task_row(
    row: sqlite3.Row,
    tag_lookup: ...,
    project_info_lookup: ...,
    task_name_lookup: ...,
    order: str | None = None,  # NEW: dotted order from CTE
) -> dict[str, Any]:
    # ... existing mapping ...
    result = {
        "id": task_id,
        "name": row["name"],
        "order": order,  # NEW
        # ... rest of fields ...
    }
    return result
```

[VERIFIED: codebase] -- `_map_task_row` signature and pattern confirmed from `hybrid.py`.

### Cross-Path Equivalence Fix

```python
# Source: test_cross_path_equivalence.py -- exclude order from comparison
def assert_equivalent(result_a: ListRepoResult, result_b: ListRepoResult) -> None:
    items_a = sorted(result_a.items, key=lambda x: x.id or "")
    items_b = sorted(result_b.items, key=lambda x: x.id or "")
    # Exclude order from comparison -- intentional divergence (D-05)
    for a, b in zip(items_a, items_b):
        assert a.model_dump(exclude={"order"}) == b.model_dump(exclude={"order"})
    assert result_a.total == result_b.total
```

[VERIFIED: codebase] -- `assert_equivalent` location and current pattern confirmed from cross-path tests.

### BridgeOnly Adapter: Set order=None

```python
# Source: adapter.py -- set order=None for bridge-adapted tasks
def _adapt_task(raw: dict[str, Any]) -> None:
    # ... existing adaptation ...
    raw["order"] = None  # D-03: bridge path cannot compute order
```

[VERIFIED: codebase] -- `_adapt_task` location confirmed from `adapter.py`.

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `ORDER BY t.persistentIdentifier` | `ORDER BY o.sort_path` (CTE) | This phase | Tasks return in OmniFocus outline order instead of alphabetical ID order |
| No order field on Task | `order: str \| None` (dotted notation) | This phase | Agents can see sibling positioning without parent-chain traversal |

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | SQLite window functions (`ROW_NUMBER()`) work inside recursive CTE branches | CTE Design | Dotted path must be computed in Python instead of SQL. Sort path still works -- only the ordinal computation changes. |

## Open Questions

1. **ROW_NUMBER() in recursive CTE**
   - What we know: SQLite supports window functions (added 3.25.0, 2018). Recursive CTEs are supported.
   - What's unclear: Whether `ROW_NUMBER()` works correctly inside `UNION ALL` branches of a recursive CTE. The deep dive CTE doesn't use window functions -- it only builds `sort_path`.
   - Recommendation: Try SQL-based dotted path first. If it fails, compute ordinals in Python from sorted results (trivial: iterate sorted list, track parent, count siblings).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ORDER-01 | Task includes `order` field (dotted string) | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k order` | Wave 0 |
| ORDER-01 | Task `order` is None on bridge path | unit | `uv run pytest tests/test_bridge_only_repository.py -x -q -k order` | Wave 0 |
| ORDER-02 | Siblings have sequential 1-based order values | unit | `uv run pytest tests/test_query_builder.py -x -q -k order` | Wave 0 |
| ORDER-03 | `order` rejected on edit_tasks input | unit | `uv run pytest tests/test_output_schema.py -x -q` | Existing (extra="forbid" handles this -- no new test needed) |
| ORDER-04 | Tasks returned in outline order | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k outline_order` | Wave 0 |
| ORDER-05 | Inbox tasks after projects | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k inbox_after` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- New test cases needed in `test_hybrid_repository.py` for:
  - [ ] Order field present and correct (dotted notation)
  - [ ] Outline ordering (siblings grouped under parent)
  - [ ] Inbox tasks after projects
  - [ ] get_task returns correct order
- New test cases in `test_bridge_only_repository.py` for:
  - [ ] Order field is None
- Modifications to `test_cross_path_equivalence.py`:
  - [ ] Exclude `order` from `assert_equivalent()`
- Modifications to `tests/conftest.py`:
  - [ ] Add `order` default to factory functions
- Output schema validation:
  - [ ] Run `test_output_schema.py` (existing, auto-validates)

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/direct-database-access-ordering/RESULTS.md` -- CTE solution, performance benchmarks, edge cases, inbox handling [VERIFIED: codebase]
- `.research/updated-spec/MILESTONE-v1.3.3.md` -- Phase requirements, scope decisions [VERIFIED: codebase]
- `src/omnifocus_operator/repository/hybrid/query_builder.py` -- Current SQL builder patterns [VERIFIED: codebase]
- `src/omnifocus_operator/repository/hybrid/hybrid.py` -- Current row mapper, read implementations [VERIFIED: codebase]
- `src/omnifocus_operator/models/task.py` -- Current Task model [VERIFIED: codebase]
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` -- EditTaskCommand (extra="forbid") [VERIFIED: codebase]
- `tests/test_cross_path_equivalence.py` -- Current cross-path comparison mechanism [VERIFIED: codebase]
- `docs/model-taxonomy.md` -- Model naming conventions [VERIFIED: codebase]

### Secondary (MEDIUM confidence)
- None

### Tertiary (LOW confidence)
- None

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, pure SQLite + Pydantic
- Architecture: HIGH -- all integration points verified in codebase, CTE validated in deep dive
- Pitfalls: HIGH -- identified from actual code patterns and cross-path test structure

**Research date:** 2026-04-12
**Valid until:** 2026-05-12 (stable -- no external dependencies changing)
