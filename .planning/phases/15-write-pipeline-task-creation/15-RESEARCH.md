# Phase 15: Write Pipeline & Task Creation - Research

**Researched:** 2026-03-08
**Domain:** OmniJS write APIs, MCP write pipeline architecture, Pydantic write models
**Confidence:** HIGH

## Summary

Phase 15 implements the first write path through the full stack: MCP tool -> Service (validate) -> Repository -> Bridge (OmniJS) -> invalidate snapshot. The OmniJS API for task creation is well-documented from prior research (`new Task(name)` / `new Task(name, container)`), and the existing IPC mechanism (request files + response files) already supports arbitrary payloads. The main complexity is in the service-layer validation (parent resolution, tag resolution) and wiring the bridge into HybridRepository.

All building blocks exist: `send_command(operation, params)` dispatches arbitrary operations, `_stale` + `_wait_for_fresh_data()` handles post-write freshness, and the test infrastructure (InMemoryRepository, InMemoryBridge, in-process MCP client) covers every layer.

**Primary recommendation:** Build bottom-up: bridge.js `add_task` handler -> repository `add_task` method -> service validation + delegation -> MCP tool registration. Test each layer independently.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- Single `parent` ID field on write model (not separate `project` + `parent_task_id`)
- Server resolves parent type: try `get_project` first, then `get_task`, error if neither found
- Tags specified as names (case-insensitive matching), tag IDs accepted as fallback
- Non-existent tag = validation error (no auto-create)
- Ambiguous tag name error includes matching tag IDs for retry
- Tool named `add_tasks` (plural), array input, single-item constraint enforced
- Returns per-item result array: `[{ success: true, id: "...", name: "..." }]`
- Fields: name (required), parent, tags, due_date, defer_date, planned_date, flagged, estimated_minutes, note
- HybridRepository gains a bridge reference (always required)
- Reads stay SQLite, writes go through bridge
- `TEMPORARY_simulate_write` replaced with real bridge calls + `_stale = True`
- InMemoryRepository gains in-memory write methods
- Bridge operation renamed: `snapshot` -> `get_all` in bridge.js
- Bridge returns minimal `{ success, id, name }` for add_task command
- 2s WAL mtime timeout for freshness after writes

### Claude's Discretion
- Write model Pydantic class design (TaskCreateSpec or similar)
- Bridge.js `add_task` command implementation details
- Test structure and organization for write pipeline
- How to wire bridge into HybridRepository constructor in factory
- Validation error message formatting

### Deferred Ideas (OUT OF SCOPE)
None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|-----------------|
| CREA-01 | Create task with name (minimum required field) | OmniJS `new Task(name)` -> inbox. Bridge `add_task` handler |
| CREA-02 | Assign task to parent (project or task ID); server resolves type | Service validates via `get_project`/`get_task`. Bridge uses `Project.byIdentifier`/`Task.byIdentifier` |
| CREA-03 | Set tags, dates, flagged, estimated_minutes, note on creation | OmniJS direct property assignment after `new Task()`. Bridge sets each field |
| CREA-04 | No parent = inbox | `new Task(name)` with no second arg -> inbox automatically |
| CREA-05 | Service validates before bridge (name required, parent exists, tags exist) | Service layer resolves parent + tags using existing repository get-by-ID methods |
| CREA-06 | Returns per-item result with success, id, name | Bridge returns `{ success: true, id: task.id.primaryKey, name: task.name }` |
| CREA-07 | API accepts arrays with single-item constraint | MCP tool validates `len(items) == 1`, raises if not |
| CREA-08 | Snapshot invalidated after write; next read returns fresh data | HybridRepository sets `_stale = True` + captures WAL mtime. Existing `_wait_for_fresh_data` handles the rest |

</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| pydantic | 2.x (existing) | Write model (TaskCreateSpec) | Already used for all models, camelCase alias generation |
| mcp | >=1.26.0 (existing) | FastMCP tool registration | Already used, `ToolAnnotations(readOnlyHint=False)` for write tools |

### Supporting
No new libraries needed. Everything builds on existing infrastructure.

## Architecture Patterns

### Write Pipeline Flow
```
MCP tool (add_tasks)
  -> Validate array length (exactly 1)
  -> Service.add_task(spec)
     -> Validate name present
     -> Resolve parent (if provided): get_project(id) || get_task(id)
     -> Resolve tags (if provided): match by name (case-insensitive) or ID
     -> Repository.add_task(validated_spec)
        -> Bridge.send_command("add_task", payload)
        -> Mark stale (_stale = True, capture WAL mtime)
        -> Return {success, id, name}
```

### Write Model Design (TaskCreateSpec)
```python
class TaskCreateSpec(OmniFocusBaseModel):
    """Input model for task creation. Minimal required fields."""
    name: str                              # Required
    parent: str | None = None              # Project or task ID
    tags: list[str] | None = None          # Tag names (case-insensitive) or IDs
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    flagged: bool | None = None            # None = use OmniFocus default (false)
    estimated_minutes: float | None = None
    note: str | None = None
```

- Inherits `OmniFocusBaseModel` for camelCase alias generation
- All optional fields default to `None` (omitted in bridge payload)
- `parent` is a single string ID, not a structured object -- server resolves type

### Bridge.js add_task Handler
```javascript
function handleAddTask(params) {
    // params comes from request file payload
    var task;
    if (params.parent) {
        // Try project first, then task
        var container = Project.byIdentifier(params.parent)
            || Task.byIdentifier(params.parent);
        if (!container) {
            throw new Error("Parent not found: " + params.parent);
        }
        task = new Task(params.name, container);
    } else {
        task = new Task(params.name);  // -> inbox
    }

    // Set optional fields
    if (params.dueDate) task.dueDate = new Date(params.dueDate);
    if (params.deferDate) task.deferDate = new Date(params.deferDate);
    if (params.plannedDate) task.plannedDate = new Date(params.plannedDate);
    if (params.hasOwnProperty("flagged")) task.flagged = params.flagged;
    if (params.hasOwnProperty("estimatedMinutes"))
        task.estimatedMinutes = params.estimatedMinutes;
    if (params.hasOwnProperty("note")) task.note = params.note;

    // Tags -- resolved by ID (service already validated and resolved names to IDs)
    if (params.tagIds && params.tagIds.length > 0) {
        var tags = params.tagIds.map(function(id) {
            var tag = Tag.byIdentifier(id);
            if (!tag) throw new Error("Tag not found: " + id);
            return tag;
        });
        task.addTags(tags);
    }

    return { id: task.id.primaryKey, name: task.name };
}
```

Key insight: **Tag resolution happens in the service layer (Python), but tag objects are looked up by ID in the bridge (OmniJS).** The bridge receives tag IDs, not names. This keeps the bridge dumb and testable logic in Python.

### Parent Resolution in Service Layer
```python
async def _resolve_parent(self, parent_id: str) -> str:
    """Validate parent exists. Returns the ID (pass-through).
    Raises ValueError if neither project nor task found."""
    project = await self._repository.get_project(parent_id)
    if project is not None:
        return parent_id
    task = await self._repository.get_task(parent_id)
    if task is not None:
        return parent_id
    raise ValueError(f"Parent not found: {parent_id}")
```

### Tag Resolution in Service Layer
```python
async def _resolve_tags(self, tag_names: list[str]) -> list[str]:
    """Resolve tag names to IDs. Case-insensitive match.
    Falls back to treating input as ID if no name match.
    Raises ValueError on not-found or ambiguous."""
    all_data = await self._repository.get_all()
    tag_ids = []
    for name in tag_names:
        # Try case-insensitive name match
        matches = [t for t in all_data.tags if t.name.lower() == name.lower()]
        if len(matches) == 1:
            tag_ids.append(matches[0].id)
        elif len(matches) > 1:
            ids_str = ", ".join(f"{t.id} ({t.name})" for t in matches)
            raise ValueError(
                f"Ambiguous tag name '{name}' matches {len(matches)} tags: {ids_str}. "
                f"Use a tag ID instead."
            )
        else:
            # Try as ID fallback
            tag = await self._repository.get_tag(name)
            if tag is not None:
                tag_ids.append(tag.id)
            else:
                raise ValueError(f"Tag not found: '{name}'")
    return tag_ids
```

### HybridRepository Changes
- Constructor gains `bridge` parameter (always required for writes)
- `add_task()` method: calls `bridge.send_command("add_task", payload)`, then sets `_stale = True` + captures WAL mtime
- `TEMPORARY_simulate_write()` removed
- Factory wires bridge into HybridRepository

### InMemoryRepository Changes
- `add_task()` appends to internal `_snapshot.tasks` list (creates a Task model from spec)
- Enables testing without bridge

### Bridge Dispatch Rename
- `snapshot` operation -> `get_all` in bridge.js dispatch table
- `BridgeRepository._refresh()` updates: `send_command("get_all")` instead of `send_command("snapshot")`
- Add `add_task` to dispatch table

### MCP Tool Result Shape
```python
class TaskCreateResult(OmniFocusBaseModel):
    success: bool
    id: str
    name: str
```

Tool returns `list[TaskCreateResult]` (array of 1 for now).

### Anti-Patterns to Avoid
- **Tag resolution in bridge.js**: Keep it in Python where it's testable. Bridge only receives tag IDs.
- **Parent resolution in bridge.js**: Validate in service layer, but bridge also does `Project.byIdentifier || Task.byIdentifier` as a safety net.
- **Validating after bridge call**: All validation MUST happen before `send_command`. OmniJS has no transactions.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| camelCase serialization | Manual dict key conversion | `OmniFocusBaseModel` with `alias_generator=to_camel` | Already working for all models |
| IPC file atomicity | Manual temp+rename | Existing `_write_request` in RealBridge | Already handles `.tmp` -> `os.replace()` |
| Post-write freshness | Custom polling loop | Existing `_stale` + `_wait_for_fresh_data()` | WAL mtime detection already implemented |
| MCP tool registration | Manual JSON schema | FastMCP `@mcp.tool()` with type hints | Framework handles schema generation |

## Common Pitfalls

### Pitfall 1: Bridge operation rename breaks BridgeRepository
**What goes wrong:** Renaming `snapshot` -> `get_all` in bridge.js but forgetting to update `BridgeRepository._refresh()` which sends `send_command("snapshot")`.
**How to avoid:** Update both bridge.js dispatch AND Python `_refresh()` in the same task. Test via existing BridgeRepository tests.
**Warning signs:** BridgeRepository tests fail with "Unknown operation: snapshot".

### Pitfall 2: Case sensitivity in tag matching
**What goes wrong:** Agent sends "work" but tag is "Work" -- exact match fails.
**How to avoid:** Case-insensitive comparison (`t.name.lower() == name.lower()`).
**Warning signs:** Tags that exist but aren't found during validation.

### Pitfall 3: HybridRepository constructor change breaks factory
**What goes wrong:** HybridRepository now requires `bridge` parameter but factory doesn't provide it.
**How to avoid:** Update `_create_hybrid_repository()` in factory.py to create a bridge and pass it.
**Warning signs:** Server startup crashes with TypeError about missing `bridge` argument.

### Pitfall 4: InMemoryRepository write model mismatch
**What goes wrong:** `add_task()` in InMemoryRepository creates a Task model that doesn't match the full read model shape (missing computed fields like urgency, availability, added, modified, url).
**How to avoid:** In InMemoryRepository, generate synthetic values for computed fields (e.g., urgency="none", availability="available", added/modified=now).
**Warning signs:** Tests that read back a created task fail on missing fields.

### Pitfall 5: Date serialization mismatch between Python and OmniJS
**What goes wrong:** Python sends ISO 8601 dates but OmniJS needs `new Date(string)`.
**How to avoid:** OmniJS `new Date(iso_string)` parses ISO 8601 correctly. Just pass the ISO string.
**Warning signs:** Dates appear wrong or null after creation.

### Pitfall 6: Bridge params vs argument string confusion
**What goes wrong:** Write payloads are in the request file `params` field, but existing code only uses `operation` from request. The `params` field is already supported by `_write_request()` but `handleSnapshot()` ignores params.
**How to avoid:** `handleAddTask` reads from the `params` object passed by `dispatch()`. Already structured correctly -- `request.params` is available.
**Warning signs:** Bridge receives empty params object.

## Code Examples

### OmniJS Task Creation (verified from research)
```javascript
// Source: .research/deep-dives/omni-automation-api/FINDINGS.md
// Basic inbox task
var task = new Task("Buy groceries");

// In a project (by reference)
var project = Project.byIdentifier("proj-123");
var task = new Task("Buy groceries", project);

// Under a parent task (action group)
var parentTask = Task.byIdentifier("task-456");
var task = new Task("Subtask", parentTask);

// Set properties after creation
task.dueDate = new Date("2026-03-15T17:00:00.000Z");
task.deferDate = new Date("2026-03-10T09:00:00.000Z");
task.flagged = true;
task.estimatedMinutes = 30;
task.note = "Remember to check the list";

// Add tags (by reference)
var tag = Tag.byIdentifier("tag-789");
task.addTag(tag);
task.addTags([tag1, tag2]);

// Get the created task's ID
task.id.primaryKey  // -> "abc123"
```

### Existing IPC Pattern (already in codebase)
```python
# Source: src/omnifocus_operator/bridge/real.py
# Request file contains: {"operation": "add_task", "params": {...}}
# Response file contains: {"success": true, "data": {"id": "...", "name": "..."}}
await self._write_request(request_id, operation="add_task", params={
    "name": "Buy groceries",
    "tagIds": ["tag-789"],
    "dueDate": "2026-03-15T17:00:00.000Z",
})
```

### Test Pattern (existing style)
```python
# Source: tests/test_service.py
# Service tests use InMemoryRepository
snapshot = make_snapshot(tags=[make_tag_dict(id="tag-1", name="Work")])
repo = InMemoryRepository(snapshot=snapshot)
service = OperatorService(repository=repo)
result = await service.add_task(TaskCreateSpec(name="New task", tags=["Work"]))
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| `TEMPORARY_simulate_write()` | Real bridge `add_task` + `_stale = True` | This phase | Writes actually persist to OmniFocus |
| Bridge only reads (`snapshot`) | Bridge reads + writes (`get_all`, `add_task`) | This phase | Bridge dispatch table grows |
| HybridRepository read-only | HybridRepository reads SQLite + writes via bridge | This phase | Constructor gains `bridge` param |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + anyio (Python), vitest (JS bridge) |
| Config file | `pyproject.toml` [tool.pytest.ini_options], `vitest.config.js` |
| Quick run command | `uv run pytest tests/ -x --no-cov -q` |
| Full suite command | `uv run pytest tests/ --cov` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| CREA-01 | Create task with name only -> inbox | unit + integration | `uv run pytest tests/test_service.py::TestAddTask::test_create_minimal -x` | Wave 0 |
| CREA-02 | Assign to parent (project or task), server resolves | unit | `uv run pytest tests/test_service.py::TestAddTask::test_parent_resolution -x` | Wave 0 |
| CREA-03 | Set all optional fields on creation | unit | `uv run pytest tests/test_service.py::TestAddTask::test_all_fields -x` | Wave 0 |
| CREA-04 | No parent = inbox | unit | `uv run pytest tests/test_service.py::TestAddTask::test_no_parent_inbox -x` | Wave 0 |
| CREA-05 | Validation errors (no name, bad parent, bad tag) | unit | `uv run pytest tests/test_service.py::TestAddTask::test_validation -x` | Wave 0 |
| CREA-06 | Returns {success, id, name} | unit + integration | `uv run pytest tests/test_server.py::TestAddTasks -x` | Wave 0 |
| CREA-07 | Array input with single-item constraint | unit | `uv run pytest tests/test_server.py::TestAddTasks::test_single_item_constraint -x` | Wave 0 |
| CREA-08 | Snapshot invalidated after write | unit | `uv run pytest tests/test_hybrid_repository.py::TestAddTask -x` | Wave 0 |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x --no-cov -q`
- **Per wave merge:** `uv run pytest tests/ --cov`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] `tests/test_service.py::TestAddTask` -- service-level add_task tests (validation, parent/tag resolution)
- [ ] `tests/test_server.py::TestAddTasks` -- MCP tool integration tests
- [ ] `tests/test_hybrid_repository.py::TestAddTask` -- repository write + staleness tests
- [ ] `tests/test_bridge.py` -- bridge.js `handleAddTask` vitest tests
- [ ] Write model classes (TaskCreateSpec, TaskCreateResult) -- needed before tests

## Open Questions

1. **Tag name matching with parent paths in ambiguity errors**
   - What we know: CONTEXT.md says "show parent path in ambiguity errors (e.g., 'Work > Personal' vs 'Work > Office')"
   - What's clear: Tag model has `parent` field (tag ID). Service can resolve tag hierarchy.
   - Recommendation: Build tag path string from parent chain in the error message. Nice to have, implement in validation.

2. **Bridge.js params already supported?**
   - What we know: `_write_request` writes `{"operation": ..., "params": {...}}`. Bridge `readRequest` parses the full object. But `dispatch` only passes `request.operation` to handlers, not params.
   - What's clear: `dispatch` needs to pass `request.params` to operation handlers.
   - Recommendation: Update `dispatch()` to pass params. Simple change.

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/omni-automation-api/FINDINGS.md` -- OmniJS task creation API (`new Task()`, property assignment, tag operations)
- `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md` -- Bridge specification, write caveats, `byIdentifier()` lookups
- `.research/deep-dives/omnifocus-api-ground-truth/scripts/05-write-create-test-data.js` -- Verified working OmniJS write code patterns
- Source code: `server.py`, `service.py`, `repository/hybrid.py`, `repository/in_memory.py`, `bridge/real.py`, `bridge/bridge.js` -- existing patterns

### Secondary (MEDIUM confidence)
- `.research/updated-spec/MILESTONE-v1.2.md` -- Spec for write pipeline architecture

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- no new libraries, all existing infrastructure
- Architecture: HIGH -- write pipeline design is well-specified in CONTEXT.md and MILESTONE spec
- Pitfalls: HIGH -- derived from actual code review of existing patterns
- OmniJS write API: HIGH -- verified via empirical audit scripts run against live OmniFocus

**Research date:** 2026-03-08
**Valid until:** 2026-04-08 (stable domain, no external dependencies changing)
