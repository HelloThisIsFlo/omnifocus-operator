# Phase 16: Task Editing - Context

**Gathered:** 2026-03-08
**Status:** Ready for planning

<domain>
## Phase Boundary

Patch-based task editing via `edit_tasks` tool. Agents can modify fields, manage tags (replace/add/remove), and move tasks between parents. No lifecycle changes (complete/drop/reactivate -- Phase 17), no project/tag writes, no batch execution (single-item constraint).

</domain>

<decisions>
## Implementation Decisions

### Patch semantics
- Sentinel pattern: omit field = no change (UNSET), null = clear, value = set
- Pydantic model uses custom sentinel (e.g., `_UNSET = object()`) as default for all optional fields
- Agent JSON: omitted keys map to UNSET; explicit `null` maps to None; values map to values
- Bridge payload only includes fields that are not UNSET -- bridge.js uses `hasOwnProperty()` (same Phase 15 pattern)

### Clearable vs value-only fields
- **Clearable (null = remove):** due_date, defer_date, planned_date, note, estimated_minutes
- **Value-only (no null):** name (string, reject empty/whitespace), flagged (bool, true/false only)
- Tags and parent handled by their own dedicated fields/modes

### Tag editing modes
- Three separate fields: `tags` (replace all), `add_tags` (add without removing), `remove_tags` (remove specific)
- Mutual exclusivity: `tags` cannot appear alongside `add_tags` or `remove_tags` -- validation error if mixed
- `add_tags` + `remove_tags` together IS allowed (add some, remove others in one call)
- `tags: []` (empty list) clears all tags on the task
- Tag resolution: same as Phase 15 -- case-insensitive name match, ID fallback, ambiguity error with IDs listed
- Removing a tag the task doesn't have: silently ignored (no-op), but included in response warnings

### Task movement
- `parent` field on edit model uses same sentinel pattern: UNSET = don't move, null = move to inbox, value = move to parent
- Parent resolution: same Phase 15 pattern -- try project first, then task, error if neither found
- **Document project-first resolution as an architecture decision** (project takes precedence when ID matches both)
- Moving to current parent: silently accepted (no-op), with educational warning in response
- **Full cycle validation:** walk parent chain via SQLite before bridge call; reject if moving task under itself or any of its descendants. Clear error: "Cannot move task: would create circular reference"

### Validation
- Pre-validate task ID exists via `get_task()` in service layer before bridge call (consistent with Phase 15 parent validation)
- Name validation: reject empty/whitespace when name is provided (same as add_tasks)
- All tag and parent validation happens in service layer before bridge execution

### Edit result shape
- Return `TaskEditResult`: `{ success, id, name, warnings? }`
- `name` reflects the updated name (post-edit state from bridge)
- `warnings` is an optional list of strings for no-op situations
- **Educational warnings on all no-ops** with hints about omitting fields:
  - Tag not present: "Tag 'X' was not on this task -- to skip tag changes, omit remove_tags"
  - Same parent: "Task is already under this parent -- omit parent to skip movement"
  - Field set to current value: similar pattern
- Consistent with add_tasks minimal result shape (plus warnings extension)

### Tool API shape
- Tool named `edit_tasks` (plural) -- array input, single-item constraint (same as add_tasks)
- Returns per-item result array: `[{ success, id, name, warnings? }]`
- `id` is required in each item (which task to edit)

### Claude's Discretion
- UNSET sentinel implementation (custom class vs bare object vs Pydantic's own mechanism)
- Bridge.js `edit_task` handler implementation details
- Test structure and organization
- How to wire edit_task into existing repository implementations
- Exact warning message wording
- Whether to add warnings field to TaskCreateResult retroactively for consistency
- Cycle detection algorithm details (recursive vs iterative parent walk)

</decisions>

<specifics>
## Specific Ideas

- Educational warnings that teach the agent patch semantics: "Parent unchanged -- omit the parent field to skip this." The idea is that LLMs learn in-context from tool responses, so warnings serve as runtime documentation
- Project-first parent resolution should be documented as an architecture decision, not just an implementation detail
- Cycle validation is cheap since we read from SQLite cache (~46ms full snapshot, single-row queries faster)

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `TaskCreateSpec` / `TaskCreateResult` (`models/write.py`): edit models follow same patterns, TaskEditResult extends with warnings
- `OperatorService._resolve_parent()` (`service.py`): reusable for edit parent validation
- `OperatorService._resolve_tags()` (`service.py`): reusable for all three tag modes
- `bridge.js handleAddTask()` (lines 215-248): template for handleEditTask -- same `hasOwnProperty()` pattern for optional fields
- `HybridRepository.add_task()` / `BridgeRepository.add_task()`: template for edit_task -- same payload construction and cache invalidation
- `InMemoryRepository.add_task()`: template for in-memory edit (mutate existing task in snapshot)
- `OmniFocusBaseModel` with camelCase aliases: edit models inherit this

### Established Patterns
- Service validates before bridge executes (parent exists, tags exist, name non-empty)
- Repository protocol with structural typing: add `edit_task` method
- `model_dump(by_alias=True, exclude_none=True)` for camelCase bridge payloads
- `hasOwnProperty()` in bridge.js for falsy values (false, 0)
- `_mark_stale()` / `_cached = None` after writes for freshness
- `items: list[dict]` input with `model_validate()` for camelCase handling at MCP layer

### Integration Points
- `repository/protocol.py`: extend with `edit_task` method
- `repository/hybrid.py`: implement edit_task via bridge + mark stale
- `repository/bridge.py`: implement edit_task via bridge + invalidate cache
- `repository/in_memory.py`: implement edit_task as in-memory mutation
- `service.py`: add `edit_task` with validation (task exists, parent resolution, tag resolution, cycle check, name validation)
- `server.py`: register `edit_tasks` tool with `readOnlyHint=False`
- `bridge/bridge.js`: add `edit_task` command handler (OmniJS: `Task.byIdentifier()` + field assignment)
- `models/write.py`: add `TaskEditSpec` + `TaskEditResult`

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 16-task-editing*
*Context gathered: 2026-03-08*
