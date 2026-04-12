# Phase 51: Task Ordering - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

Agents can see where each task sits in the hierarchy via an `order` field, and tasks are returned in correct outline order. Read-only string field using dotted notation (e.g., "2.3.1") reflecting full hierarchical position. Inbox tasks sort after projects. No new tools — enhances existing read tools.

</domain>

<decisions>
## Implementation Decisions

### Order format: dotted notation (D-01)
- `order` uses dotted string notation: `"1"`, `"1.2"`, `"2.3.1"`, etc.
- Each dot level represents position among siblings at that depth
- Example: `"2.3.1"` = 2nd root-level in project → 3rd child → 1st grandchild
- **Per-project/inbox namespace**: Every project and inbox starts numbering at "1". The `project` field identifies which namespace. Inbox is its own namespace.
- Format: dots (not dashes or slashes), no trailing dot on root items (`"1"` not `"1."`)
- Build dotted path in the recursive CTE by concatenating ordinals at each level
- Type: `str | None` (not `int`)

**Rationale (from discussion):**
- LLMs consume output as text — `"1"` vs `1` is irrelevant to processing
- Dotted notation is immediately comprehensible without traversal: `"2.3.1"` vs `order: 1` + trace parent chain
- Deep nesting becomes clearer: `"1.2.3.4.5"` vs "order 5 of what? let me find parent..."
- Agent-first design principle: optimize for LLM readability, not programmatic parsing
- Pre-sorted results mean agents don't need to compare/sort — any string sort gotchas are moot

### Scope of ordering (D-02)
- All read operations include the `order` field: `get_task`, `list_tasks`, `get_all`
- One model shape everywhere — agents don't need to know which method fetched the task
- `get_task` needs the ancestor chain to build the dotted path

### Bridge-only degradation (D-03)
- Model type: `order: str | None`
- HybridRepository always provides `str` (dotted path like "2.3.1")
- BridgeOnlyRepository always provides `None` (rank unavailable via OmniJS API)
- Honest signal of degraded mode — no misleading arbitrary values

### Outline ordering
- Recursive CTE with `sort_path` reproduces exact OmniFocus UI order
- Inbox tasks use `ZZZZZZZZZZ/` prefix to sort after projects (Strategy B from deep dive)
- Projects/folders/tags use simple `ORDER BY parent, rank` (no CTE needed)
- `order` field only on tasks for now; can extend to projects later if needed

### Tool description updates (D-04)
- Add brief note to `list_tasks`, `get_task`, `get_all` tool descriptions explaining:
  - `order` is hierarchical position within the project/inbox (dotted notation like "2.3.1")
  - Filtered results may show sparse order values (e.g., "2.1", "2.5") because non-matching siblings are omitted
- Keep it concise — one or two sentences, not verbose

### Cross-path equivalence testing (D-05)
- Existing 32 parametrized tests verify SQL and bridge paths return identical results
- `order` is an **intentional divergence**: HybridRepository returns dotted path, BridgeOnlyRepository returns `None`
- Cross-path tests must exclude `order` from comparison (or add to "known divergence fields" list)
- This is expected — per REQUIREMENTS.md: "approximate ordering acceptable for BridgeOnlyRepository fallback"

### Claude's Discretion
- Exact SQL for building dotted path (string concatenation in CTE)
- Whether to extract CTE as a shared constant or inline per query
- Test strategy for order field validation
- Count query optimization (exclude CTE if simple, include if code duplication required)
- How to exclude `order` from cross-path equivalence comparison

</decisions>

<specifics>
## Specific Ideas

No specific requirements — follow the deep dive research and established query builder patterns.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Ordering research (complete technical solution)
- `.research/deep-dives/direct-database-access-ordering/RESULTS.md` — CTE solution, performance benchmarks, edge cases, inbox handling
- `.research/updated-spec/MILESTONE-v1.3.3.md` — Phase requirements, success criteria, scope decisions

### Architecture
- `docs/architecture.md` — Three-layer architecture, repository protocol, dumb bridge principle
- `docs/model-taxonomy.md` — Model naming conventions, where new fields go

### Existing implementation
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — Current SQL builder patterns, `_TASKS_BASE` constant
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — `_map_task_row`, `_TASKS_SQL`, list/get implementations
- `src/omnifocus_operator/models/task.py` — Current Task model (add `order` field here)
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — Fallback repository, will return `order: None`

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `query_builder.py:SqlQuery` — NamedTuple for parameterized SQL, already used by list operations
- `_TASKS_BASE` constant — Base SELECT/FROM/WHERE for tasks, needs CTE prepended
- `_map_task_row()` — Row-to-dict mapper, add `order` field extraction here

### Established Patterns
- `build_list_tasks_sql()` returns `(data_query, count_query)` — CTE applies to data query
- `_read_task()` in hybrid.py — Single-entity read, needs ancestor traversal for dotted path
- `_read_all()` — Full snapshot, needs CTE for outline ordering

### Integration Points
- Task model (`models/task.py`) — Add `order: str | None` field
- `agent_messages/descriptions.py` — Add description constant for `order` field (explain dotted notation)
- BridgeOnlyRepository — Set `order=None` in list_tasks, get_task, get_all
- Bridge adapter (`adapter.py`) — May need to set `order: None` during snapshot adaptation

</code_context>

<deferred>
## Deferred Ideas

- Add `order` field to Project/Folder/Tag entities — evaluate after task ordering ships

</deferred>

---

*Phase: 51-task-ordering*
*Context gathered: 2026-04-12*
