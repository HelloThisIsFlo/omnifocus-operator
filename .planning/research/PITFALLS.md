# Domain Pitfalls

**Domain:** SQL filtering, pagination, entity listing, and count tools on an MCP server with dual read paths (SQLite + in-memory fallback)
**Researched:** 2026-03-29
**System context:** OmniFocus Operator v1.3 milestone

## Critical Pitfalls

Mistakes that cause result divergence between read paths, data loss via silent omission, or incorrect agent behavior.

---

### Pitfall 1: SQL/In-Memory Result Divergence from Separate Filter Implementations

**What goes wrong:** SQL WHERE clauses and Python in-memory filtering silently produce different results for the same filter parameters. The contract "bridge fallback produces identical results to SQL path" is violated without any error.

**Why it happens:** Two independent implementations of the same filter logic. Every filter is written twice -- once in SQL, once in Python. Subtle semantic differences accumulate: LIKE vs `in` operator, NULL handling, type coercion, collation, boundary conditions.

**Consequences:** Agent gets different task counts depending on which read path is active. Tests pass against InMemoryBridge, but real SQLite path returns different data. Bugs are invisible until someone compares outputs side-by-side.

**Prevention:**
- **Single filter specification, two backends.** Define each filter as a declarative spec (e.g., `FilterSpec(field="name", op="contains", value="...")`) that both SQL builder and Python filter interpret. Don't write SQL strings in one place and Python `if` chains in another.
- **Property-based cross-path tests.** For every filter combination, assert `sql_result == in_memory_result` using the same seed data. The golden master pattern already exists (43 scenarios) -- extend it to cover filtered queries.
- **Shared filter resolution.** Filter parameter parsing (e.g., status shorthands, `review_due_within` duration parsing) MUST happen in the service layer before reaching either repository. Repositories receive resolved, unambiguous filter values.

**Detection:** Add a CI test that runs every filter against both paths with a known dataset and diffs results. Any difference is a test failure.

---

### Pitfall 2: Pagination Without Deterministic ORDER BY

**What goes wrong:** `LIMIT 5 OFFSET 5` returns overlapping or missing rows across pages. Agent paginating through results sees duplicate tasks or silently skips tasks.

**Why it happens:** SQL does not guarantee row order without `ORDER BY`. The existing `_TASKS_SQL` query has no ORDER BY clause. SQLite's internal storage order can change between reads (especially with WAL mode). The same query with `LIMIT 10 OFFSET 0` and `LIMIT 10 OFFSET 10` may return overlapping rows because the engine picks a different execution plan.

**Consequences:** Agent paging through "all flagged tasks" misses some, sees others twice. `count_tasks()` says 47, but iterating with `limit=10` only yields 43 unique tasks. Agent makes decisions on incomplete data.

**Prevention:**
- **Always ORDER BY a unique column.** Add `ORDER BY t.persistentIdentifier` (or another unique, stable column) to every filtered query. This is cheap (indexed primary key) and guarantees deterministic pagination.
- **Apply the same sort to in-memory filtering.** Python fallback must `sorted(results, key=lambda t: t.id)` before applying offset/limit slicing.
- **Test pagination determinism.** Assert that `list_tasks(limit=5, offset=0)` + `list_tasks(limit=5, offset=5)` produces the same set as `list_tasks(limit=10)`.

**Detection:** Pagination integration test that verifies no overlap and no gaps when iterating through the full result set.

---

### Pitfall 3: LIKE Case Sensitivity for Non-ASCII Characters

**What goes wrong:** `search` filter using SQL `LIKE` is case-insensitive for ASCII (`a` matches `A`) but case-sensitive for Unicode (`e` does NOT match `E` with accent). A user searching "resume" won't find a task named "Resume" (fine), but searching for accented characters like "cafe" won't find "Cafe" with accented e.

**Why it happens:** SQLite's built-in LIKE operator only does ASCII case folding. The `PRAGMA case_sensitive_like` is deprecated. COLLATE NOCASE doesn't affect LIKE behavior. Full Unicode case folding requires the ICU extension or a custom collation.

**Consequences:** For this system, the practical impact is moderate -- OmniFocus task names are overwhelmingly ASCII. But the `search` filter documentation must not promise "case-insensitive" without the ASCII caveat.

**Prevention:**
- **Document the limitation explicitly.** Tool description says "case-insensitive ASCII substring match" not just "case-insensitive."
- **Use `LOWER()` for both sides** as a pragmatic middle ground: `WHERE LOWER(name) LIKE LOWER(?)`. This handles ASCII correctly and is explicit about what's happening. Still won't handle full Unicode, but matches the Python `str.lower()` behavior, preventing SQL/in-memory divergence.
- **In-memory path must use the same semantics.** Python `str.lower()` also doesn't do full Unicode case folding (though it's better than SQLite's). Use `casefold()` on neither or both paths -- consistency matters more than completeness.
- **Punt full Unicode search to v1.4.1 fuzzy search.** Don't solve Unicode case folding now; it's a future milestone's problem.

**Detection:** Test with mixed-case ASCII task names and verify both paths return the same results.

---

### Pitfall 4: NULL Handling Asymmetry Between SQL and Python Filters

**What goes wrong:** SQL `WHERE estimated_minutes <= 30` silently excludes rows where `estimated_minutes IS NULL`. Python `task.estimated_minutes <= 30` raises `TypeError` (comparing `None <= 30`) or returns `False` depending on implementation.

**Why it happens:** SQL's three-valued logic: `NULL <= 30` evaluates to NULL (falsy), so the row is excluded. Python's None comparison raises TypeError in strict mode. If guarded with `if task.field is not None and task.field <= 30`, the semantics match SQL. But if someone writes `task.field <= 30` and catches the TypeError, they might return True or False inconsistently.

**Consequences:** Filter results diverge. Worse: the divergence is data-dependent. If all test data has estimated_minutes populated, the bug is invisible. First user with NULL estimated_minutes gets different results from SQL vs in-memory.

**Prevention:**
- **Explicit NULL exclusion in both paths.** SQL: `WHERE estimated_minutes IS NOT NULL AND estimated_minutes <= ?`. Python: `if task.estimated_minutes is not None and task.estimated_minutes <= max_val`. Make the NULL check explicit rather than relying on SQL's implicit behavior.
- **Test with NULL values in seed data.** Every filterable field that can be NULL must have at least one NULL value in test fixtures. This is non-negotiable.
- **Document NULL semantics per filter.** The spec says "tasks with no value for a date field are excluded from that filter" -- extend this principle to all nullable fields (estimated_minutes, note content, etc.).

**Detection:** Test fixture with a task where every optional field is NULL. Verify every filter that touches optional fields handles it correctly on both paths.

---

### Pitfall 5: Count/List Result Divergence

**What goes wrong:** `count_tasks(flagged=True)` returns 12, but `len(list_tasks(flagged=True))` returns 10. Agent calculates "2 pages of 5" but only gets 10 tasks total.

**Why it happens:** Count and list use separate code paths. Count uses `SELECT COUNT(*)`, list uses `SELECT *`. If the WHERE clauses drift (e.g., count forgets to exclude completed tasks, or list adds an extra join that filters differently), results diverge.

**Consequences:** Agent's pagination math is wrong. "Page 3 of 5" might be empty. Agent reports incorrect totals to the user.

**Prevention:**
- **The spec already calls this out:** "Implemented as `len(filtered_results)` or `SELECT COUNT(*)` -- one code path to prevent count/list divergence." Follow this literally.
- **Concrete implementation:** Have `count_tasks()` call `list_tasks()` and return `len(result)`. Or: have both call a shared `_build_query()` that returns the WHERE clause + params, and count wraps it in `SELECT COUNT(*) FROM (...)`.
- **The spec also says count ignores limit/offset.** This is correct -- count returns total matching, not total in current page. But implement it by sharing the filter-building logic, not by duplicating it minus the LIMIT clause.
- **Cross-assert in tests.** Every test that calls `count_*` should also call `list_*` with the same filters and assert equality. Make this a test helper, not a per-test burden.

**Detection:** Parametrized test: for N filter combinations, assert `count_tasks(**filters) == len(list_tasks(**filters))`.

---

### Pitfall 6: Status Shorthand Expansion Inconsistency

**What goes wrong:** `list_projects(status=["remaining"])` returns different results on SQL vs in-memory because "remaining" is expanded to `["active", "on_hold"]` in one path but not the other. Or "available" shorthand maps to `active` in one path but `available` in another.

**Why it happens:** The spec defines shorthands: `remaining` = active + on_hold, `available` = active only, `all` = no filter. These must be expanded before reaching the repository. If expansion happens inside the SQL builder, the in-memory path doesn't get it. If expansion happens differently in each path, results diverge.

**Consequences:** "Show me remaining projects" returns 47 on SQL, 52 on in-memory. The 5 extra are on_hold projects included in one path but not the other.

**Prevention:**
- **Expand shorthands in the service layer, before the repository.** Repository receives only concrete status values: `["active", "on_hold"]`, never `"remaining"`. Both paths see the same resolved values.
- **Validate shorthand values at the service layer.** Unknown values get educational errors before reaching repository.
- **Map to the correct axis.** Project "status" in the spec maps to the `availability` field on the model. `active` = `available`, `on_hold` = `blocked`, `done` = `completed`, `dropped` = `dropped`. The SQL must filter on the correct column (`effectiveStatus` from ProjectInfo for SQL, `availability` field for in-memory). This mapping must be consistent.

**Detection:** Test each shorthand individually and verify expansion produces the same concrete values. Test that SQL and in-memory paths receive identical resolved filter values.

---

## Moderate Pitfalls

---

### Pitfall 7: `review_due_within` Date Arithmetic Edge Cases

**What goes wrong:** `review_due_within: "1m"` means "projects where nextReviewDate <= now + 1 month." But "1 month" is defined as ~30 days (naive). A project with nextReviewDate 31 days from now is excluded, even though a human would say "it's due within a month."

**Prevention:**
- **The spec already decided naive arithmetic** (30d/month, 365d/year). Document this in the tool description: "Month = ~30 days, year = ~365 days."
- **The real risk is the timestamp format.** `nextReviewDate` in SQLite is stored as Core Foundation epoch float (seconds since 2001-01-01). The service must convert `now + duration` to the same format for comparison. If the SQL compares an ISO string to a CF epoch float, every row fails the comparison silently.
- **NULL nextReviewDate.** Projects with no review schedule have NULL nextReviewDate. These must be excluded (the spec says "projects with no review schedule are excluded"). SQL handles this naturally (`NULL <= x` is falsy), but the in-memory path needs an explicit `if project.next_review_date is not None` guard.
- **`review_due_within: "now"` means overdue for review** -- `nextReviewDate <= now`. Test with a project whose review is overdue and one that's upcoming.

**Detection:** Test with CF epoch timestamps, not ISO strings. Test with projects that have no review schedule (NULL nextReviewDate).

---

### Pitfall 8: Tag Filter OR Logic vs AND Logic for Other Filters

**What goes wrong:** `tags: ["Work", "Urgent"]` should return tasks with Work OR Urgent (any of the specified tags). But if combined with `flagged: true`, the overall combination is AND: `(tag IN ("Work", "Urgent")) AND flagged`. Implementing this incorrectly as all-AND or all-OR silently changes result sets.

**Prevention:**
- **Be explicit about the algebra.** The spec says: "Filters combine with AND logic" and "tags: list (OR) -- tasks with at least one of the specified tags." This means tags are OR within the tag list, but AND with every other filter.
- **SQL implementation:** Join to TaskToTag, filter `WHERE tag IN (?, ?)`, but this creates duplicate rows if a task has multiple matching tags. Must use `SELECT DISTINCT` or `EXISTS (SELECT 1 FROM TaskToTag WHERE ...)` subquery.
- **In-memory equivalent:** `any(tag.name in filter_tags for tag in task.tags)` -- straightforward, but must match SQL behavior exactly including case sensitivity of tag matching.
- **Case sensitivity of tag names.** The spec says "case-insensitive partial match on project name" for the project filter, but doesn't explicitly state case sensitivity for tags. Tags in OmniFocus are case-sensitive (you can have "work" and "Work" as separate tags). The filter should match by tag name exactly (case-sensitive), or document otherwise.

**Detection:** Test with a task that has both "Work" and "Urgent" tags -- verify it appears once (not twice from the JOIN). Test with a task that has only "Work" -- verify it still appears.

---

### Pitfall 9: `project` Filter Requires a JOIN That Doesn't Exist Yet

**What goes wrong:** `list_tasks(project="Renovations")` needs to match tasks by their containing project's name at any nesting depth (not just direct children). The current `_TASKS_SQL` query doesn't join to project names. The task row has `containingProjectInfo` (a ProjectInfo FK) but not the project name directly.

**Prevention:**
- **The SQL query needs a LEFT JOIN to ProjectInfo and then to Task** (since projects are stored as Task rows with a ProjectInfo entry). Something like: `LEFT JOIN ProjectInfo pi2 ON t.containingProjectInfo = pi2.pk LEFT JOIN Task pt ON pi2.task = pt.persistentIdentifier WHERE pt.name LIKE ?`.
- **For in-memory:** The Task model doesn't currently have a `project_name` field. The spec notes "project_name as a derived field on Task (resolved from snapshot/join)." This needs to be either: (a) added as a field populated during snapshot loading, or (b) resolved at filter time by looking up the parent chain.
- **Inbox tasks have no project.** `containingProjectInfo IS NULL` for inbox tasks. A `project` filter with an INNER JOIN would exclude all inbox tasks. Must use LEFT JOIN and handle NULL.

**Detection:** Test filtering by project name on inbox tasks (should not match). Test partial match ("Renov" matches "Renovations"). Test case insensitivity. Test deeply nested tasks (task inside action group inside project must still match).

---

### Pitfall 10: `completed`/`dropped` Default Exclusion Interacts with Other Filters

**What goes wrong:** `list_tasks(flagged=True)` excludes completed/dropped tasks by default. But the SQL query must explicitly add `WHERE dateCompleted IS NULL AND dateHidden IS NULL` (or equivalent availability filter). If the default exclusion is implemented via `availability NOT IN ('completed', 'dropped')`, it works. But if it's implemented by checking date columns, it must match the availability derivation logic exactly.

**Prevention:**
- **Use the availability column, not date columns, for default exclusion.** The `_map_task_availability` function derives availability from `dateCompleted` and `dateHidden`. In SQL, replicate this: tasks where `dateHidden IS NOT NULL` are dropped, `dateCompleted IS NOT NULL` are completed. Filter as: `WHERE t.dateHidden IS NULL AND t.dateCompleted IS NULL AND NOT t.blocked` would be wrong (that's `available` only, not "not completed/dropped").
- **Correct default exclusion in SQL:** `WHERE t.dateHidden IS NULL AND t.dateCompleted IS NULL`. This excludes completed and dropped while keeping both available and blocked tasks.
- **In-memory:** `task.availability not in ("completed", "dropped")`. These must be semantically identical.
- **The v1.3.1 date filters will override this.** Using `completed: "any"` or `completed: {last: "1w"}` must disable the default exclusion for completed tasks. Design the exclusion as an addable/removable clause from the start.

**Detection:** Seed data must include completed and dropped tasks. Verify they're excluded by default. Verify `availability: "blocked"` still returns blocked-but-not-completed tasks.

---

### Pitfall 11: `offset` Without `limit` Is Silently Meaningless

**What goes wrong:** Agent calls `list_tasks(offset=10)` without `limit`. SQL `OFFSET` without `LIMIT` is implementation-defined (SQLite ignores it). The agent thinks they're skipping 10 tasks, but gets all tasks.

**Prevention:**
- **The spec already requires `limit` when `offset` is used.** Validate at the service layer: if offset > 0 and limit is None, return an educational error.
- **Don't just silently ignore offset.** The error message should say: "offset requires limit. Use limit to set page size, then offset to skip pages."

**Detection:** Test that `offset` without `limit` raises a validation error, not silent behavior.

---

### Pitfall 12: Tool Description Quality for LLMs -- Enum Values and Filter Syntax

**What goes wrong:** LLM calls `list_tasks(availability="Available")` (PascalCase from training data) instead of `availability="available"` (snake_case). Or calls `list_projects(status="active")` when the parameter expects a list, not a string. Or uses `status="remaining"` which is a shorthand, not a concrete value.

**Prevention:**
- **List all valid values in the tool description.** Not "see enum" -- literally spell them out: `availability: "available" or "blocked"`.
- **Show the type explicitly.** `status: list of strings. Values: "active", "on_hold", "done", "dropped". Shorthands: "remaining" (= active + on_hold, default), "available" (= active only), "all" (= no filter).`
- **Include one example per non-obvious filter** in the description. LLMs are few-shot learners -- a single example in the tool description dramatically reduces calling errors.
- **Validate with Pydantic at entry.** Fail fast with educational messages: "Got 'Available', did you mean 'available'? Valid values are: ..."
- **Test tool descriptions with multiple LLM models.** The v1.3.1 spec mentions testing with Sonnet and Opus. Do this for v1.3 too -- have each model call every filter combination and verify they construct valid calls from the description alone.

**Detection:** UAT: have an LLM read only the tool description and generate 10 example calls. Check if they're all valid.

---

## Minor Pitfalls

---

### Pitfall 13: SQL LIKE Escaping for `%` and `_` in Search Terms

**What goes wrong:** User searches for a task containing literal "50%" or "file_name". SQL LIKE interprets `%` as wildcard and `_` as single-character wildcard. `WHERE name LIKE '%50%%'` matches "50 things" not just "50%".

**Prevention:**
- **Escape LIKE wildcards in user input.** Before building the LIKE pattern, escape `%` to `\%` and `_` to `\_`, then set `ESCAPE '\'` in the SQL.
- **In-memory path uses `in` operator** (`search_term in task.name`), which doesn't have this problem. If SQL escapes but Python doesn't, they'll agree on most inputs but diverge on inputs containing `%` or `_`.

**Detection:** Test with a task named "50% complete" and search for "50%".

---

### Pitfall 14: `estimated_minutes_max` Boundary -- Inclusive or Exclusive?

**What goes wrong:** `estimated_minutes_max: 30` -- does this include a 30-minute task? SQL `<=` includes it, `<` excludes it. If SQL uses `<=` but Python uses `<` (or vice versa), results diverge for tasks at exactly the boundary.

**Prevention:**
- **The spec says "Tasks with estimated duration <= this value."** Use `<=` in both paths. Document as inclusive.
- **Type consideration:** `estimated_minutes` is `float | None` in the model. SQL comparison with float works. Python comparison works. Just be consistent.

**Detection:** Test with a task at exactly the boundary value.

---

### Pitfall 15: `has_children` Filter on Stale Data

**What goes wrong:** `has_children` in SQLite is derived from `childrenCount > 0`. In the in-memory bridge, it's computed from the snapshot. If a task just had its children moved elsewhere (via `edit_tasks` with `moveTo`), the SQLite cache might reflect the new state but the in-memory snapshot might not (or vice versa, depending on cache freshness).

**Prevention:**
- **This is a read-after-write consistency issue**, not a filter logic issue. The existing `_ensures_write_through` decorator handles this for HybridRepository. For BridgeRepository, cache invalidation on writes already exists.
- **In tests, verify that after a move operation, the has_children value updates.** This is more of a v1.2 concern, but filters surface it more visibly.

**Detection:** Integration test: create parent with children, move children away, verify `has_children: false` in subsequent list query.

---

### Pitfall 16: `inbox` Filter and the `inInbox` Column

**What goes wrong:** A task that was just added (still in processing) might not have `inInbox` set correctly in SQLite. Or the SQLite `inInbox` column semantics might differ from the bridge's `inInbox` field.

**Prevention:**
- **Verify `inInbox` column behavior.** In SQLite, `inInbox` is a boolean column on the Task table. The existing `_map_task_row` already reads it: `"in_inbox": bool(row["inInbox"])`. The filter just adds `WHERE t.inInbox = 1` (or `= 0`).
- **In-memory:** `task.in_inbox == filter_value`. Straightforward.
- **Edge case:** Tasks in the inbox have no project assignment. `inbox: true` and `project: "something"` should return empty results (AND logic). This is a natural consequence but worth a test.

**Detection:** Test that `inbox: true, project: "X"` returns empty. Test that `inbox: false` excludes inbox tasks.

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| SQL WHERE clause builder | Pitfall 1 (divergence), 4 (NULL) | Declarative filter specs, shared resolution in service layer |
| Pagination | Pitfall 2 (ORDER BY), 11 (offset validation) | Deterministic sort on ID, service-layer validation |
| Substring search | Pitfall 3 (LIKE case), 13 (LIKE escaping) | `LOWER()` on both sides, escape wildcards |
| Status shorthands | Pitfall 6 (expansion inconsistency) | Expand in service layer before repository |
| Count tools | Pitfall 5 (count/list divergence) | Share filter-building code, cross-assert in tests |
| Tag filter | Pitfall 8 (OR vs AND, duplicates) | EXISTS subquery or DISTINCT, explicit algebra |
| Project name filter | Pitfall 9 (missing JOIN) | LEFT JOIN through ProjectInfo to Task name |
| Default exclusion | Pitfall 10 (completed/dropped) | Use date columns for exclusion, design as removable clause |
| Tool descriptions | Pitfall 12 (LLM calling errors) | Spell out all values, include examples, test with LLMs |
| review_due_within | Pitfall 7 (date arithmetic, timestamp format) | CF epoch comparison, NULL handling, document naive months |
| Date filters (v1.3.1) | Pitfall 4 (NULL dates), 7 (arithmetic) | Explicit NULL exclusion, shared resolution |

## Architectural Recommendation: Filter Resolution Pipeline

The single most impactful prevention strategy across all critical pitfalls is a **shared filter resolution pipeline** in the service layer:

```
Agent input  -->  Service: parse + validate + expand shorthands + resolve dates
             -->  Repository receives: concrete, unambiguous filter values
             -->  SQL builder OR Python filter applies identical resolved filters
```

This eliminates pitfalls 1, 4, 5, 6, 7, and 10 at the architectural level. The repository never interprets shorthands, never expands durations, never decides NULL semantics. All that complexity lives in one place, tested once.

## Sources

- [SQLite NULL handling documentation](https://sqlite.org/nulls.html)
- [SQLite LIKE case sensitivity and expression docs](https://www.sqlite.org/lang_expr.html)
- [5 ways to implement case-insensitive search in SQLite](https://shallowdepth.online/posts/2022/01/5-ways-to-implement-case-insensitive-search-in-sqlite-with-full-unicode-support/)
- [Non-deterministic pagination without ORDER BY](https://use-the-index-luke.com/sql/partial-results/fetch-next-page)
- [Deterministic sort order required for pagination](https://blog.kalvad.com/sql-paging-requires-a-deterministic-sort-order-a-classic-example-of-s-e-p-somebody-elses-problem/)
- [MCP Tools specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools)
- [How LLMs choose MCP tools](https://gyliu513.medium.com/how-llm-choose-the-right-mcp-tools-9f88dbcf11a2)
- [LLM tool calling with MCP best practices](https://towardsdatascience.com/tools-for-your-llm-a-deep-dive-into-mcp/)
