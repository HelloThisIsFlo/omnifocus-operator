# Phase 52: Same-Container Move Fix - Context

**Gathered:** 2026-04-12
**Status:** Ready for planning

<domain>
## Phase Boundary

`moveTo beginning/ending` reliably reorders tasks even when already in the target container. The OmniFocus API silently no-ops on same-container beginning/ending moves — this phase fixes it via service-layer translation to `moveBefore`/`moveAfter`. Also improves no-op warning accuracy: checks ordinal position, not just container membership. No new tools, no bridge changes — enhances existing `edit_tasks` behavior.

</domain>

<decisions>
## Implementation Decisions

### Edge-child query — new Repository protocol method
- **D-01:** Add `get_edge_child_id(parent_id: str, edge: Literal["first", "last"]) -> str | None` to the Repository protocol
- **D-02:** `parent_id` is non-nullable. For inbox, pass `SYSTEM_LOCATIONS["inbox"].id` (the `$inbox` constant from `config.py`), never `None`. The type system prevents routing inbox through the wrong query path.
- **D-03:** Hybrid implementation: `SELECT persistentIdentifier FROM Task WHERE parent = ? ORDER BY rank ASC/DESC LIMIT 1`. For `$inbox`: `WHERE parent IS NULL AND NOT EXISTS(ProjectInfo)` — same condition as the CTE inbox anchor from phase 51.
- **D-04:** Bridge-only implementation: filter cached snapshot for direct children, return first/last from the list. OmniFocus returns tasks in display order via `flattenedTasks`, so positional first/last is correct without rank.
- **D-05:** Always use the constant `SYSTEM_LOCATIONS["inbox"].id` when referring to inbox — never the raw `"$inbox"` string literal.

### Translation strategy — always-when-children-exist
- **D-06:** Translation scope: **always when target container has children**, regardless of whether task is already in that container. One code path, no same-vs-different branching.
- **D-07:** Translation: `beginning` → `moveBefore(first_child)`, `ending` → `moveAfter(last_child)`. Empty container → no translation (direct `moveTo` works fine).
- **D-08:** Both hybrid and bridge-only paths translate. No degraded mode for this feature.

### Translation placement — domain decision per litmus test
- **D-09:** Translation lives in `domain.py`'s `_process_container_move`. Per the architecture litmus test ("Would another OmniFocus tool make this same choice?") — the choice to fix the API quirk via translation is opinionated product behavior, not universal plumbing. Another tool might accept the limitation, error out, or warn. We chose to fix it.
- **D-10:** `_process_container_move` already resolves containers, checks cycles, and returns bridge-ready dicts. Translation is a natural extension: resolve → look up edge child → translate if needed → return dict. The dict shape changes from `{position: "beginning", container_id: X}` to `{position: "before", anchor_id: Y}`, both already valid for `MoveToRepoPayload`.

### No-op detection — Option B (translation first, then detect)
- **D-11:** Translation runs unconditionally — it does NOT check whether the task being moved is the edge child. Translation is a pure transformation.
- **D-12:** No-op detection catches self-references: if translated payload has `anchor_id == task_id` → no-op. This covers all success criteria 6-9:
  - First child → beginning → translates to `before(self)` → `anchor_id == task_id` → no-op ✓
  - Last child → ending → translates to `after(self)` → `anchor_id == task_id` → no-op ✓
  - Non-edge child → beginning/ending → translates to `before/after(other)` → proceeds ✓
- **D-13:** The `anchor_id == task_id` check lives in `_all_fields_match` (where all no-op detection already lives). This check also catches direct `before`/`after` self-references if an agent sends those.

### Warning messages
- **D-14:** Remove `MOVE_SAME_CONTAINER` warning entirely (it says "will be fixed in a future release" — this IS that release).
- **D-15:** New position-specific warning for move no-ops: communicates "Task is already at the beginning/ending of this container." Exact wording is Claude's Discretion, should match existing educational style (e.g., tag no-ops, lifecycle no-ops).

### Batch freshness — already handled, no special design needed
- **D-16:** Single-item enforcement in `server.py` (lines 223-225) means batch freshness is a non-issue for phase 52.
- **D-17:** When batch support eventually arrives, existing infrastructure handles it:
  - **Hybrid path:** `@_ensures_write_through` on `edit_task` polls WAL mtime after each bridge write. Next item's `get_edge_child_id` queries SQLite which sees the fresh WAL. No application-level cache on top of SQLite.
  - **Bridge-only path:** `BridgeOnlyRepository` clears its cached snapshot after each write. Next item's `get_edge_child_id` triggers a fresh bridge dump (~1.3s per dump, acceptable for fallback mode per milestone spec).
  - Both paths guarantee sequential service calls see each other's writes. The translation can call `get_edge_child_id` normally — freshness guarantees do their job.
- **D-18:** No special batch handling code should be added in this phase. Document the freshness analysis so future batch work doesn't re-derive it.

### Claude's Discretion
- Exact warning message wording for position-specific no-ops
- Internal method naming for the edge-child lookup within `_process_container_move`
- Test organization (new test class vs extending existing)
- Whether `get_edge_child_id` in bridge-only filters from `get_all()` snapshot or uses a more targeted approach

</decisions>

<specifics>
## Specific Ideas

No specific requirements — standard service-layer patterns. The milestone spec and deep-dive results are comprehensive.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec & requirements
- `.research/updated-spec/MILESTONE-v1.3.3.md` — Full milestone spec with all three features, scope decisions, edge cases, and acceptance criteria
- `.planning/ROADMAP.md` §Phase 52 — Success criteria 1-9, requirement IDs (MOVE-01 through MOVE-06, WARN-01 through WARN-03)

### Architecture & patterns
- `docs/architecture.md` §Service Layer: Product Decisions vs Plumbing — Litmus test for domain vs plumbing placement (D-09 rationale)
- `docs/architecture.md` §Method Object Pattern — Pipeline convention for `_EditTaskPipeline`
- `docs/architecture.md` §Task movement (actions.move) — "Key IS the position" design, `MoveToRepoPayload` shape
- `docs/architecture.md` §Write Pipeline — Full sequence diagram showing service → repo → bridge flow

### Deep-dive results
- `.research/deep-dives/direct-database-access-ordering/RESULTS.md` — Rank uniqueness within parent (zero duplicates across 3062 tasks), MIN/MAX rank for edge children, CTE performance

### Existing move implementation (key files to read)
- `src/omnifocus_operator/service/domain.py` — `_process_container_move`, `_all_fields_match` (no-op detection), `_extract_move_target`
- `src/omnifocus_operator/contracts/shared/actions.py` — `MoveAction` model with exactly-one-key validation
- `src/omnifocus_operator/contracts/use_cases/edit/tasks.py` — `MoveToRepoPayload` (position + container_id/anchor_id)
- `src/omnifocus_operator/agent_messages/warnings.py` — `MOVE_SAME_CONTAINER` (to be removed)
- `src/omnifocus_operator/contracts/protocols.py` — `Repository` protocol (where `get_edge_child_id` will be added)
- `src/omnifocus_operator/config.py` — `SYSTEM_LOCATIONS["inbox"]` constant

### Phase 51 infrastructure (dependency)
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — `_TASK_ORDER_CTE` with inbox anchor SQL condition (reusable for inbox edge-child query)
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — Hybrid read paths showing how inbox vs project children are distinguished in SQL

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- **Rank-based SQL from phase 51**: The CTE inbox anchor (`WHERE parent IS NULL AND NOT EXISTS(ProjectInfo)`) is exactly the condition needed for `get_edge_child_id("$inbox", ...)`. Reuse the same WHERE clause.
- **`SYSTEM_LOCATIONS` constant** (`config.py:36-38`): Already imported by both repository implementations for inbox references. `get_edge_child_id` branches on this constant.
- **`MoveToRepoPayload`** (`contracts/use_cases/edit/tasks.py`): Already has both `container_id` (for beginning/ending) and `anchor_id` (for before/after) as optional fields. No schema changes needed — translated moves just use the anchor fields instead.
- **`BridgeWriteMixin._dump_payload()`**: Converts `MoveToRepoPayload` to bridge dict. Already handles both container and anchor shapes via `model_dump(exclude_unset=True)`.

### Established Patterns
- **Repository protocol growth**: Protocol grew from 6 methods (v1.0) to current set with `list_tasks`, `count_tasks` etc. Adding `get_edge_child_id` follows the same pattern — small, focused read method.
- **No-op detection in `_all_fields_match`**: Existing pattern compares each payload field against current task state. The `anchor_id == task_id` check extends this pattern naturally.
- **Domain litmus test**: All opinionated behavior lives in `domain.py`. Translation is opinionated → it goes there.
- **Warning constants in `agent_messages/warnings.py`**: All warnings are centralized constants with AST enforcement preventing inline strings.

### Integration Points
- **`_process_container_move` in `domain.py`**: Entry point for the translation. Currently returns `{position, container_id}` — will conditionally return `{position, anchor_id}` instead.
- **`_all_fields_match` in `domain.py`**: Entry point for improved no-op detection. Currently checks container membership — will check `anchor_id == task_id` for translated moves.
- **`Repository` protocol in `contracts/protocols.py`**: Where `get_edge_child_id` is declared.
- **`HybridRepository` in `repository/hybrid/hybrid.py`**: SQL implementation of `get_edge_child_id`.
- **`BridgeOnlyRepository` in `repository/bridge_only/bridge_only.py`**: Snapshot-filtering implementation of `get_edge_child_id`.

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope.

</deferred>

---

*Phase: 52-same-container-move-fix*
*Context gathered: 2026-04-12*
