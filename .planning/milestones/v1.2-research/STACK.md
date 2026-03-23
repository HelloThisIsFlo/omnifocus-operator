# Technology Stack

**Project:** OmniFocus Operator v1.2 -- Writes & Lookups
**Researched:** 2026-03-07

## Key Finding: Zero New Dependencies

v1.2 requires **no new runtime or dev dependencies**. The existing stack (Python 3.12 stdlib + Pydantic v2 + MCP SDK) handles everything needed for the write pipeline, get-by-ID tools, and task lifecycle changes.

The project's constraint of `mcp>=1.26.0` as the sole runtime dep remains intact.

---

## What Changes (v1.2 additions only)

### Bridge Layer (OmniJS / bridge.js)

**New bridge commands** (all within existing `bridge.js`):

| Command | Purpose | Payload Source | Response Shape |
|---------|---------|---------------|----------------|
| `get_task` | Single task by ID | Arg string (existing pattern) | Same as snapshot task object |
| `get_project` | Single project by ID | Arg string | Same as snapshot project object |
| `get_tag` | Single tag by ID | Arg string | Same as snapshot tag object |
| `add_task` | Create task | Request file params | `{ id, name }` |
| `edit_task` | Modify task fields | Request file params | `{ id, name }` |

**OmniJS write APIs** (verified in BRIDGE-SPEC.md Section 4):

| Operation | OmniJS API | Notes |
|-----------|-----------|-------|
| Create task | `new Task(name, project)` | Returns Task object with `.id.primaryKey` |
| Set fields | Direct property assignment (`t.dueDate = date`, etc.) | All writable, null clears |
| Complete | `task.markComplete()` | Sets completionDate, active stays true |
| Reactivate | `task.markIncomplete()` | Reverts completion |
| Drop | `task.drop(true)` | Permanent -- `markIncomplete()` is a no-op after drop |
| Add tag | `task.addTag(tag)` | Tag lookup via `Tag.byIdentifier(id)` |
| Remove tag | `task.removeTag(tag)` | |
| Clear tags | `task.clearTags()` | Used for `tags: []` replace mode |

**Entity lookup by ID** (documented in BRIDGE-SPEC.md Section 7):
- `Task.byIdentifier(id)` -- direct ID-based lookup
- `Project.byIdentifier(id)` -- direct ID-based lookup
- `Tag.byIdentifier(id)` -- also needed for tag resolution in write operations

### Request File Payload Format

Write commands use the existing request file mechanism with richer params. No changes to `RealBridge._write_request()` needed -- it already serializes arbitrary `params` dicts.

```json
{
  "operation": "add_task",
  "params": {
    "name": "Task name",
    "project": "projectId123",
    "tags": ["tagId1", "tagId2"],
    "dueDate": "2026-03-15T10:00:00.000Z",
    "flagged": true,
    "note": "Task notes"
  }
}
```

For edits, patch semantics via `hasOwnProperty` in bridge.js:

```json
{
  "operation": "edit_task",
  "params": {
    "id": "taskId123",
    "changes": {
      "name": "New name",
      "dueDate": null,
      "addTags": ["tagId3"],
      "removeTags": ["tagId1"]
    }
  }
}
```

### Repository Protocol Extension

Current protocol has only `get_all()`. v1.2 adds methods for single-entity lookup and writes:

```python
class Repository(Protocol):
    async def get_all(self) -> AllEntities: ...

    # New in v1.2
    async def get_task(self, task_id: str) -> Task: ...
    async def get_project(self, project_id: str) -> Project: ...
    async def get_tag(self, tag_id: str) -> Tag: ...
    async def add_task(self, params: AddTaskParams) -> AddTaskResult: ...
    async def edit_task(self, task_id: str, changes: EditTaskChanges) -> EditTaskResult: ...
```

**Implementation per repository:**

| Method | HybridRepository (SQLite) | BridgeRepository | InMemoryRepository |
|--------|--------------------------|------------------|--------------------|
| `get_task` | `SELECT ... WHERE persistentIdentifier = ?` | Dict lookup from snapshot | Dict lookup |
| `get_project` | `SELECT ... WHERE pi.task = ?` | Dict lookup | Dict lookup |
| `get_tag` | `SELECT ... WHERE persistentIdentifier = ?` | Dict lookup | Dict lookup |
| `add_task` | Delegate to bridge, mark stale | Delegate to bridge | In-memory insert |
| `edit_task` | Delegate to bridge, mark stale | Delegate to bridge | In-memory update |

**Critical:** HybridRepository writes go through the OmniJS bridge, not SQLite. SQLite is read-only -- OmniFocus owns the database. After a write, `self._stale = True` triggers WAL-based freshness detection on next read (already implemented via `_wait_for_fresh_data()`).

### HybridRepository Needs a Bridge Reference

Currently `HybridRepository` only reads SQLite. For writes, it needs a bridge to dispatch OmniJS commands.

**Recommendation:** Constructor injection -- `HybridRepository(db_path, bridge=bridge)`. Bridge is optional (None for read-only tests), required for writes. The factory (`create_repository()`) already has access to create both.

### Pydantic Input Models

New models for write requests (no new deps, standard Pydantic v2):

| Model | Purpose | Key Fields |
|-------|---------|------------|
| `AddTaskParams` | Task creation input | `name` (required), `project`, `parent_task_id`, `tags`, dates, `flagged`, `note` |
| `EditTaskChanges` | Patch semantics | All fields optional, null = clear, omit = no change |
| `AddTaskResult` | Creation response | `id`, `name`, `success` |
| `EditTaskResult` | Edit response | `id`, `name`, `success` |
| `TaskLifecycleAction` | Enum for lifecycle | `complete`, `drop`, `reactivate` |

**Validation approach** -- Pydantic v2 built-in validators handle everything:
- `model_validator(mode="before")` for mutual exclusivity (project vs parent_task_id, tags vs add_tags)
- `field_validator` for ISO8601 date parsing
- Standard type validation for required vs optional fields
- No need for jsonschema or external validation libraries

### Snapshot Invalidation

The mechanism already exists:
- `HybridRepository.TEMPORARY_simulate_write()` captures WAL mtime and sets `_stale = True`
- Replace with real `_mark_stale()` doing the same thing
- Next `get_all()` calls `_wait_for_fresh_data()` (50ms poll, 2s timeout) -- already implemented and tested

---

## Existing Stack (Unchanged)

### Runtime

| Technology | Version | Purpose | Status |
|------------|---------|---------|--------|
| Python | 3.12+ | Runtime | Unchanged |
| `mcp` | >=1.26.0 | MCP SDK (FastMCP) | Unchanged, sole runtime dep |
| Pydantic | v2 (via mcp) | Models, validation | Unchanged, used for new input models |
| sqlite3 | stdlib | Read path | Unchanged, read-only |
| asyncio | stdlib | Async runtime | Unchanged |
| json | stdlib | IPC serialization | Unchanged |

### Dev Dependencies (Unchanged)

| Library | Version | Purpose |
|---------|---------|---------|
| ruff | >=0.15.0 | Linting/formatting |
| mypy | >=1.19.1 | Type checking |
| pytest | >=9.0.2 | Testing |
| pytest-asyncio | >=1.3.0 | Async test support |
| pytest-cov | >=7.0.0 | Coverage |
| pytest-timeout | >=2.4.0 | Test timeouts |
| pre-commit | >=4.0.0 | Pre-commit hooks |

---

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Validation | Pydantic v2 (existing) | marshmallow, attrs | Already in stack via MCP SDK |
| Date parsing | Pydantic `AwareDatetime` | python-dateutil | Handles ISO8601; no RRULE parsing in v1.2 |
| Schema for edits | Pydantic `model_validator` | jsonschema, json-patch | Pydantic handles patch semantics with optional fields + None sentinels |
| Bridge IPC | Existing request file format | New protocol | Works as-is -- just add new operation names and richer params |
| Write path | OmniJS bridge only | Direct SQLite writes | OmniFocus owns the database; direct writes corrupt state |
| Retry/resilience | None (v1.2) | tenacity, backoff | Deferred to v1.5 Production Hardening |

## What NOT to Add

- **No new runtime dependencies.** Stdlib + Pydantic covers everything.
- **No jsonschema/json-patch.** Pydantic optional fields + None sentinel = patch semantics.
- **No python-dateutil.** ISO8601 handled by Pydantic. RRULE parsing not needed in v1.2.
- **No retry/resilience libraries.** Deferred to v1.5.
- **No transaction/rollback mechanism.** OmniJS has no transactions -- best-effort with per-item results.

---

## Integration Flow

### Write pipeline through existing layers

```
MCP Tool (server.py)
  -> OperatorService (service.py)       # Validate against snapshot
    -> Repository.add_task()            # Dispatch to implementation
      -> HybridRepository               # Delegates write to bridge
        -> Bridge.send_command()        # Existing IPC mechanism
          -> bridge.js dispatch()       # New operation handlers
            -> OmniJS API              # new Task(), t.field = value, markComplete()
        -> self._stale = True          # Trigger WAL freshness on next read
```

### Get-by-ID through existing layers

```
MCP Tool (server.py)
  -> OperatorService (service.py)
    -> Repository.get_task(id)
      -> HybridRepository              # SELECT ... WHERE id = ?
      or BridgeRepository              # Dict lookup from snapshot
```

---

## Installation

```bash
# Nothing to install. Zero new dependencies.
# Existing `uv sync` is sufficient.
```

---

## Sources

- BRIDGE-SPEC.md Section 4 (Write Operations) -- HIGH confidence, empirically verified against OmniFocus 4.8.8
- BRIDGE-SPEC.md Section 7 (`Task.byIdentifier`, `Project.byIdentifier`) -- HIGH confidence
- Existing codebase direct inspection: `bridge.js`, `real.py`, `hybrid.py`, `protocol.py`, `service.py`
- MILESTONE-v1.2.md -- project spec for v1.2 scope

---
*Stack research for: OmniFocus Operator v1.2 Writes & Lookups*
*Researched: 2026-03-07*
