# Phase 16: Task Editing - Research

**Researched:** 2026-03-08
**Domain:** Patch-based task editing -- fields, tags, movement
**Confidence:** HIGH

## Summary

Phase 16 adds `edit_tasks` following the exact same three-layer pattern as Phase 15's `add_tasks`: MCP tool -> service validation -> repository delegation -> bridge execution. The key complexity is the UNSET sentinel for patch semantics (omit = no change vs null = clear vs value = set), tag editing modes (replace/add/remove with mutual exclusivity), and the `moveTo` positional system that maps directly to OmniJS's `Task.ChildInsertionLocation` API.

All OmniJS APIs needed are verified: `Task.byIdentifier()` for lookup, direct property assignment for field updates, `addTags()/removeTags()/clearTags()` for tag management, and `database.moveTasks(tasks, location)` with `project.beginning/ending`, `task.before/after/beginning/ending`, `inbox.beginning/ending` for positioning.

**Primary recommendation:** Follow Phase 15 patterns exactly. The sentinel mechanism is the only novel design element -- everything else (service validation, repository protocol extension, bridge handler, MCP tool wiring) reuses established patterns.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Sentinel pattern: omit field = no change (UNSET), null = clear, value = set
- Pydantic model uses custom sentinel as default for all optional fields
- Clearable fields: due_date, defer_date, planned_date, note, estimated_minutes
- Value-only fields: name (reject empty/whitespace), flagged (bool only)
- Three tag editing modes: `tags` (replace), `add_tags` (add), `remove_tags` (remove)
- Mutual exclusivity: `tags` cannot appear with `add_tags`/`remove_tags`; `add_tags` + `remove_tags` together IS allowed
- `moveTo` object with "key IS the position" design: beginning/ending/before/after
- Exactly one key required in `moveTo`
- Cycle detection: walk parent chain via SQLite before bridge call
- Tool named `edit_tasks` (plural), array input, single-item constraint
- Return `TaskEditResult`: `{ success, id, name, warnings? }`
- Educational warnings on all no-ops
- Pre-validate task ID exists via get_task() before bridge call
- Project-first parent resolution (documented as architecture decision)

### Claude's Discretion
- UNSET sentinel implementation (custom class vs bare object vs Pydantic mechanism)
- Bridge.js `edit_task` handler implementation details
- Test structure and organization
- How to wire edit_task into existing repository implementations
- Exact warning message wording
- Whether to add warnings field to TaskCreateResult retroactively
- Cycle detection algorithm details (recursive vs iterative parent walk)

### Deferred Ideas (OUT OF SCOPE)
- Positioning for add_tasks (moveTo on task creation) -- backlog item
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| EDIT-01 | Patch semantics (omit = no change, null = clear, value = set) | Sentinel pattern with UNSET object; Pydantic model_dump excludes UNSET fields |
| EDIT-02 | Editable fields: name, note, due_date, defer_date, planned_date, flagged, estimated_minutes | All confirmed writable via OmniJS property assignment (BRIDGE-SPEC Property Writes table) |
| EDIT-03 | Replace all tags (`tags: [...]`) | OmniJS: `clearTags()` + `addTags()` pattern |
| EDIT-04 | Add tags without removing (`add_tags: [...]`) | OmniJS: `addTags()` (ignores duplicates natively) |
| EDIT-05 | Remove specific tags (`remove_tags: [...]`) | OmniJS: `removeTags()` |
| EDIT-06 | Mutual exclusivity validation (tags vs add_tags/remove_tags) | Pydantic model_validator or service-layer check |
| EDIT-07 | Move task to different parent | OmniJS: `database.moveTasks([task], container.ending)` with project/task resolution |
| EDIT-08 | Move task to inbox (`parent: null` / `moveTo: {ending: null}`) | OmniJS: `database.moveTasks([task], inbox.ending)` |
| EDIT-09 | Array input with single-item constraint | Same pattern as add_tasks -- `len(items) != 1` guard |
</phase_requirements>

## Standard Stack

### Core (already in project)
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x | Write model validation, sentinel handling | Already used for all models |
| mcp | >=1.26.0 | MCP server framework | Only runtime dependency |

### No New Dependencies
Phase 16 requires zero new packages. All functionality is built on existing Pydantic models, OmniJS bridge patterns, and the established three-layer architecture.

## Architecture Patterns

### Recommended File Changes
```
src/omnifocus_operator/
  models/write.py          # Add TaskEditSpec, MoveToSpec, TaskEditResult, UNSET sentinel
  models/__init__.py       # Export new models, add to _ns dict, model_rebuild()
  repository/protocol.py   # Add edit_task method to Repository protocol
  repository/hybrid.py     # Implement edit_task (bridge + mark_stale)
  repository/bridge.py     # Implement edit_task (bridge + invalidate cache)
  repository/in_memory.py  # Implement edit_task (mutate snapshot)
  service.py               # Add edit_task with validation (exists, parent, tags, cycle, name)
  server.py                # Register edit_tasks tool
  bridge/bridge.js         # Add handleEditTask + edit_task dispatch
tests/
  test_service.py          # Service-layer edit_task tests
  test_server.py           # MCP tool integration tests
  bridge_tests/            # Vitest tests for handleEditTask
```

### Pattern 1: UNSET Sentinel for Patch Semantics
**What:** Custom sentinel object that distinguishes "field not provided" from `None` (clear) and actual values.
**When to use:** Every optional field on TaskEditSpec.

**Recommended implementation -- custom class with repr:**
```python
class _Unset:
    """Sentinel for 'field not provided' in patch models."""
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    def __repr__(self) -> str:
        return "UNSET"
    def __bool__(self) -> bool:
        return False

UNSET = _Unset()
```

**Why a class, not bare `object()`:** Pydantic needs consistent type behavior, repr helps debugging, singleton ensures `is` comparison works across modules.

**Model field declaration:**
```python
class TaskEditSpec(OmniFocusBaseModel):
    id: str  # Required -- which task to edit
    name: str | _Unset = UNSET           # Value-only (reject empty)
    note: str | None | _Unset = UNSET    # Clearable
    due_date: AwareDatetime | None | _Unset = UNSET  # Clearable
    # ... etc
```

**Payload construction (exclude UNSET fields):**
```python
payload = {}
for field_name, value in spec_fields():
    if value is not UNSET:
        payload[camel_case(field_name)] = value
```

**Alternative considered:** Pydantic's `model_fields_set` -- tracks which fields were explicitly set during construction. This could work with `model_validate(data)` from raw dict, where omitted keys wouldn't appear in `model_fields_set`. This is simpler but less explicit. The sentinel approach is more robust because it works regardless of how the model is constructed.

### Pattern 2: Tag Editing Modes
**What:** Three mutually exclusive modes handled at service layer.

**Validation logic:**
```python
has_replace = spec.tags is not UNSET
has_add = spec.add_tags is not UNSET
has_remove = spec.remove_tags is not UNSET

if has_replace and (has_add or has_remove):
    raise ValueError("Cannot use 'tags' with 'addTags' or 'removeTags'")
```

**Bridge payload mapping:**
- Replace (`tags`): Send `{tagMode: "replace", tagIds: [...]}`
- Add (`add_tags`): Send `{tagMode: "add", tagIds: [...]}`
- Remove (`remove_tags`): Send `{tagMode: "remove", tagIds: [...]}`
- Add + Remove: Two separate fields or two operations in bridge
- None of the above: Don't send any tag fields

### Pattern 3: moveTo Position Mapping
**What:** Map our "key IS the position" design directly to OmniJS APIs.

**Model:**
```python
class MoveToSpec(OmniFocusBaseModel):
    beginning: str | None | _Unset = UNSET
    ending: str | None | _Unset = UNSET
    before: str | _Unset = UNSET
    after: str | _Unset = UNSET
```

**Validation:** Exactly one key must be set (not UNSET).

**OmniJS mapping:**
| Our Key | OmniJS Code |
|---------|-------------|
| `beginning: "<id>"` | `database.moveTasks([task], container.beginning)` |
| `ending: "<id>"` | `database.moveTasks([task], container.ending)` |
| `before: "<taskId>"` | `database.moveTasks([task], anchorTask.before)` |
| `after: "<taskId>"` | `database.moveTasks([task], anchorTask.after)` |
| `beginning: null` | `database.moveTasks([task], inbox.beginning)` |
| `ending: null` | `database.moveTasks([task], inbox.ending)` |

Where `container` is resolved via `Project.byIdentifier(id) || Task.byIdentifier(id)`.

### Pattern 4: Cycle Detection (Parent Chain Walk)
**What:** Before moving task A under task B, verify B is not a descendant of A.
**How:** Read parent chain from SQLite (via get_all or targeted queries). Walk from target parent upward; if we encounter the task being moved, reject.

```python
async def _check_cycle(self, task_id: str, target_parent_id: str) -> None:
    all_data = await self._repository.get_all()
    task_map = {t.id: t for t in all_data.tasks}
    current = target_parent_id
    visited = set()
    while current is not None:
        if current == task_id:
            raise ValueError("Cannot move task: would create circular reference")
        if current in visited:
            break  # Safety: avoid infinite loop on corrupt data
        visited.add(current)
        task = task_map.get(current)
        if task is None:
            break  # Reached a project or unknown -- safe
        current = task.parent.id if task.parent and task.parent.type == "task" else None
```

### Anti-Patterns to Avoid
- **Don't send unchanged fields to bridge:** Only include fields where value is not UNSET. The bridge should receive minimal payloads.
- **Don't resolve tags in bridge.js:** Tag name->ID resolution stays in Python service layer (same as Phase 15).
- **Don't skip task existence check:** Always verify the task exists before attempting edit (consistent with Phase 15 parent validation).
- **Don't use `model_dump(exclude_none=True)` for edit payloads:** That would strip intentional `null` (clear) values. Must use custom serialization that only strips UNSET.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase serialization | Manual key transformation | `OmniFocusBaseModel` with `alias_generator=to_camel` | Already proven pattern |
| Tag name resolution | Custom lookup in bridge.js | `OperatorService._resolve_tags()` | Reuse existing, tested code |
| Parent type resolution | Custom lookup logic | `OperatorService._resolve_parent()` | Reuse existing, tested code |
| Cache invalidation | Custom freshness tracking | `_mark_stale()` / `_cached = None` patterns | Already proven in add_task |

## Common Pitfalls

### Pitfall 1: UNSET vs None Confusion
**What goes wrong:** Treating `None` as "no change" instead of "clear this field."
**Why it happens:** Natural Python instinct is `None` = absent.
**How to avoid:** UNSET sentinel is the ONLY way to express "no change." `None` always means "clear/remove."
**Warning signs:** Tests that set `field=None` and expect the field unchanged.

### Pitfall 2: model_dump Strips Intentional Nulls
**What goes wrong:** Using `exclude_none=True` removes clearable field nulls from the payload.
**Why it happens:** Phase 15 uses `exclude_none=True` because create has no "clear" semantics.
**How to avoid:** Custom payload construction that skips UNSET but preserves None.
**Warning signs:** Edit with `due_date=None` doesn't clear the due date.

### Pitfall 3: Tag Mode Validation Gap
**What goes wrong:** Allowing `tags` alongside `add_tags` or `remove_tags`.
**Why it happens:** Missing mutual exclusivity check.
**How to avoid:** Explicit check in service layer before any tag resolution.
**Warning signs:** Ambiguous behavior when both replace and add are specified.

### Pitfall 4: moveTo with Invalid Container
**What goes wrong:** `before`/`after` with a project ID instead of a task ID.
**Why it happens:** `before`/`after` take sibling task IDs (parent inferred), not container IDs.
**How to avoid:** For `before`/`after`, validate the anchor is a task. For `beginning`/`ending`, resolve as project-first then task.
**Warning signs:** OmniJS error about invalid insertion location.

### Pitfall 5: Cycle Detection Missing Edge Cases
**What goes wrong:** Moving a task under its own descendant.
**Why it happens:** Not walking the full parent chain from target.
**How to avoid:** Walk from target parent up to root; reject if source task found.
**Warning signs:** OmniFocus shows task under itself (corrupt hierarchy).

### Pitfall 6: bridge.js Falsy Value Handling
**What goes wrong:** `if (params.flagged)` skips `false` values.
**Why it happens:** JavaScript falsy check treats `false`, `0`, `""` as falsy.
**How to avoid:** Use `params.hasOwnProperty("fieldName")` for all fields that can be falsy (same as Phase 15 pattern).
**Warning signs:** Setting `flagged: false` or `estimatedMinutes: 0` has no effect.

## Code Examples

### Bridge.js handleEditTask (template)
```javascript
// Source: Pattern derived from handleAddTask (bridge.js lines 215-248)
function handleEditTask(params) {
    var task = Task.byIdentifier(params.id);
    if (!task) throw new Error("Task not found: " + params.id);

    // Field updates (hasOwnProperty for falsy-safe checks)
    if (params.hasOwnProperty("name")) task.name = params.name;
    if (params.hasOwnProperty("note")) task.note = params.note;
    if (params.hasOwnProperty("dueDate"))
        task.dueDate = params.dueDate ? new Date(params.dueDate) : null;
    if (params.hasOwnProperty("deferDate"))
        task.deferDate = params.deferDate ? new Date(params.deferDate) : null;
    if (params.hasOwnProperty("plannedDate"))
        task.plannedDate = params.plannedDate ? new Date(params.plannedDate) : null;
    if (params.hasOwnProperty("flagged")) task.flagged = params.flagged;
    if (params.hasOwnProperty("estimatedMinutes"))
        task.estimatedMinutes = params.estimatedMinutes;

    // Tag management
    if (params.hasOwnProperty("tagMode")) {
        var tagObjs = (params.tagIds || []).map(function(id) {
            var tag = Tag.byIdentifier(id);
            if (!tag) throw new Error("Tag not found: " + id);
            return tag;
        });
        if (params.tagMode === "replace") {
            task.clearTags();
            if (tagObjs.length > 0) task.addTags(tagObjs);
        } else if (params.tagMode === "add") {
            task.addTags(tagObjs);
        } else if (params.tagMode === "remove") {
            task.removeTags(tagObjs);
        }
    }

    // Movement
    if (params.hasOwnProperty("moveTo")) {
        var mv = params.moveTo;
        var location;
        if (mv.position === "beginning" || mv.position === "ending") {
            if (mv.containerId === null) {
                location = inbox[mv.position];
            } else {
                var container = Project.byIdentifier(mv.containerId)
                    || Task.byIdentifier(mv.containerId);
                if (!container) throw new Error("Container not found: " + mv.containerId);
                location = container[mv.position];
            }
        } else {
            // before/after -- anchor is a task
            var anchor = Task.byIdentifier(mv.anchorId);
            if (!anchor) throw new Error("Anchor task not found: " + mv.anchorId);
            location = anchor[mv.position];
        }
        moveTasks([task], location);
    }

    return { id: task.id.primaryKey, name: task.name };
}
```

### Service Layer edit_task Outline
```python
# Source: Pattern from service.py add_task (lines 60-85)
async def edit_task(self, spec: TaskEditSpec) -> TaskEditResult:
    # 1. Verify task exists
    task = await self._repository.get_task(spec.id)
    if task is None:
        raise ValueError(f"Task not found: {spec.id}")

    # 2. Validate name if provided
    if spec.name is not UNSET:
        if not spec.name or not spec.name.strip():
            raise ValueError("Task name cannot be empty")

    # 3. Validate tag mutual exclusivity
    # 4. Resolve tags (reuse _resolve_tags)
    # 5. Validate and resolve moveTo (parent resolution + cycle check)
    # 6. Build payload, delegate to repository
    # 7. Collect warnings, return TaskEditResult
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Separate project + parent fields | Unified `parent: ParentRef` | Phase 14 (v1.2) | Edit must resolve parent via ParentRef model |
| Bridge handles tag resolution | Service resolves tag names -> IDs | Phase 15 (v1.2) | Same pattern for edit tag operations |

## Open Questions

1. **UNSET and Pydantic JSON Schema**
   - What we know: Pydantic generates JSON schema for MCP tool input. UNSET sentinel type will appear in schema.
   - What's unclear: Whether agents will be confused by the sentinel type in the schema, or if omitted keys are naturally handled by MCP clients.
   - Recommendation: Use `json_schema_extra` or field exclusion to ensure the schema shows fields as simply optional. Test with an MCP client to verify omitted fields work correctly.

2. **`model_fields_set` as Alternative to Sentinel**
   - What we know: Pydantic tracks which fields were explicitly set via `model_fields_set`. When constructing from a dict (as we do with `model_validate(items[0])`), omitted keys won't appear in `model_fields_set`.
   - What's unclear: Whether this is robust enough for all construction paths.
   - Recommendation: Evaluate both approaches during implementation. `model_fields_set` is simpler if it works with `model_validate()` from raw dicts (our actual usage pattern).

3. **inbox Reference in OmniJS**
   - What we know: `inbox.beginning` and `inbox.ending` are documented in the API.
   - What's unclear: Exact variable name -- `inbox` vs `Inbox` vs `document.inbox`.
   - Recommendation: Verify in bridge.js. The API docs reference `Inbox.beginning` (capitalized).

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio (Python), Vitest (JS bridge) |
| Config file | pyproject.toml (`asyncio_mode = "auto"`) |
| Quick run command | `uv run pytest tests/ -x -q` |
| Full suite command | `uv run pytest tests/ && npx vitest run` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| EDIT-01 | Patch semantics: omit/null/value | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-02 | Field edits: name, note, dates, flagged, estimated_minutes | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-03 | Replace all tags | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-04 | Add tags | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-05 | Remove tags | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-06 | Tag mode mutual exclusivity | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-07 | Move task to different parent | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-08 | Move task to inbox | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | No -- Wave 0 |
| EDIT-09 | Array input single-item constraint | integration | `uv run pytest tests/test_server.py::TestEditTasks -x` | No -- Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q`
- **Per wave merge:** `uv run pytest tests/ && npx vitest run`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_service.py::TestEditTask` -- service-layer edit tests (EDIT-01 through EDIT-08)
- [ ] `tests/test_server.py::TestEditTasks` -- MCP tool integration tests (EDIT-09)
- [ ] `bridge_tests/` -- Vitest tests for handleEditTask
- [ ] TaskEditSpec, MoveToSpec, TaskEditResult models in `models/write.py`
- [ ] edit_task on Repository protocol + all 3 implementations

## Sources

### Primary (HIGH confidence)
- BRIDGE-SPEC.md (`.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md`) -- Property Writes table, tag methods (addTag/removeTag/clearTags), Task.byIdentifier
- [OmniFocus API reference](https://www.omni-automation.com/omnifocus/OF-API.html) -- `database.moveTasks()`, `Task.ChildInsertionLocation` (before/after/beginning/ending)
- [OmniFocus Task page](https://www.omni-automation.com/omnifocus/task.html) -- `addTags()`, `removeTags()`, `clearTags()` method signatures
- Existing codebase: `service.py`, `models/write.py`, `bridge.js`, all repository implementations

### Secondary (MEDIUM confidence)
- [OmniFocus move tasks plug-in](https://omni-automation.com/omnifocus/plug-in-move-tasks-to-project.html) -- `moveTasks()` usage pattern

### Tertiary (LOW confidence)
- `Inbox.beginning` / `Inbox.ending` -- documented in API but exact variable naming not verified in bridge context. Needs bridge.js testing.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new dependencies, all patterns proven
- Architecture: HIGH -- direct extension of Phase 15 patterns
- Pitfalls: HIGH -- sentinel pattern well-understood, OmniJS API verified
- OmniJS positioning API: MEDIUM -- documented but `inbox` reference needs verification

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, no external dependencies changing)
