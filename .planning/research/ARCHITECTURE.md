# Architecture Patterns

**Domain:** v1.3.1 integration — system locations, name resolution for writes, rich references, model changes
**Researched:** 2026-04-05
**Confidence:** HIGH (analysis of existing codebase, not external research)

---

## How New Features Map to Existing Layers

### Layer Impact Summary

| Feature | Models | Contracts | Resolver | DomainLogic | Mappers | Config |
|---------|--------|-----------|----------|-------------|---------|--------|
| System location namespace | New `ProjectRef`, `TaskRef`, `FolderRef` | `MoveAction` type change | New `$`-prefix detection | `_process_container_move` update | `_build_parent_ref` rewrite | New constants |
| Name resolution for writes | -- | -- | New `resolve_entity()` method | -- | -- | -- |
| Rich `{id, name}` references | Use new Ref types | -- | -- | -- | 4 mapper functions | -- |
| Tagged object `parent` | `Task.parent` type change | -- | -- | Cycle detection update | `_build_parent_ref` rewrite | -- |
| New `project` field | `Task.project` field | -- | -- | -- | `_map_task_row` update | -- |
| `inInbox` removal from output | `Task` field removal | -- | -- | -- | `_map_task_row` update | -- |
| `$inbox` in filters | -- | -- | Filter resolution update | Contradictory filter check | -- | -- |
| `PatchOrNone` elimination | -- | `MoveAction` type change | -- | -- | -- | -- |
| Better `before`/`after` errors | -- | -- | -- | `_process_anchor_move` update | -- | -- |
| `get_project("$inbox")` error | -- | -- | -- | New check | -- | -- |
| `list_projects` inbox warning | -- | -- | -- | New check | -- | -- |

---

## Component-Level Changes

### 1. `config.py` — New Constants

```python
SYSTEM_LOCATION_PREFIX = "$"
INBOX_ID = "$inbox"
INBOX_DISPLAY_NAME = "Inbox"
```

- All code references these constants — no magic strings
- Enables `value.startswith(SYSTEM_LOCATION_PREFIX)` pattern

### 2. `models/common.py` — New Reference Types, Remove `ParentRef`

**New models:**
- `ProjectRef(id, name)` — follows `TagRef` pattern
- `TaskRef(id, name)` — follows `TagRef` pattern
- `FolderRef(id, name)` — follows `TagRef` pattern

**Removed:**
- `ParentRef(type, id, name)` — replaced by `ProjectRef | TaskRef` union

**Tagged object wrapper** (new model for Task.parent discrimination):
```python
class TaskParent(OmniFocusBaseModel):
    """Tagged object: exactly one of project/task is set."""
    project: ProjectRef | None = None
    task: TaskRef | None = None
```
- Validation: exactly one key set (same pattern as `MoveAction`)
- Key IS the discriminator — no `type` field, no `exclude_defaults` risk

### 3. `models/task.py` — Field Changes

| Field | Before | After |
|-------|--------|-------|
| `parent` | `ParentRef \| None` | `TaskParent` (never null) |
| `project` | (new) | `ProjectRef` (never null) |
| `in_inbox` | `bool` | Removed |

### 4. `models/project.py` — Rich References

| Field | Before | After |
|-------|--------|-------|
| `folder` | `str \| None` | `FolderRef \| None` |
| `next_task` | `str \| None` | `TaskRef \| None` |

### 5. `models/tag.py` — Rich References

| Field | Before | After |
|-------|--------|-------|
| `parent` | `str \| None` | `TagRef \| None` |

### 6. `models/folder.py` — Rich References

| Field | Before | After |
|-------|--------|-------|
| `parent` | `str \| None` | `FolderRef \| None` |

### 7. `contracts/base.py` — `PatchOrNone` Removal

- Delete `PatchOrNone` type alias
- Remove from `__all__`
- Only consumer: `MoveAction.beginning`/`ending` (changed to `Patch[str]`)

### 8. `contracts/shared/actions.py` — `MoveAction` Type Change

| Field | Before | After |
|-------|--------|-------|
| `beginning` | `PatchOrNone[str]` | `Patch[str]` |
| `ending` | `PatchOrNone[str]` | `Patch[str]` |

- `null` becomes a hard error (caught by Pydantic — `str` doesn't accept `None`)
- Validator `_exactly_one_key` unchanged (still checks 4 keys)

### 9. `service/resolve.py` — System Location + Name Resolution for Writes

**New: `$`-prefix detection** as step 0 in all resolution methods.

Current `resolve_parent(id)` flow:
1. Try `get_project(id)` 
2. Try `get_task(id)`
3. Raise ValueError

New three-step flow for all entity resolution:
1. **`$`-prefix** -- system location lookup (immediate return or error for unknown `$` values)
2. **ID match** -- existing behavior (repository lookup)
3. **Name substring match** -- new (case-insensitive, error on multiple/zero matches)

**Key design question answered: Where does `$`-prefix detection live?**

In the Resolver. Specifically:
- A new private method `_check_system_location(value)` returns the resolved ID for `$inbox` or raises for unknown `$` prefixes
- `resolve_parent()` gains name resolution (step 3) and `$`-prefix (step 1) before existing ID lookup (step 2)
- `resolve_filter()` gains `$`-prefix handling before existing ID/substring cascade
- A new `resolve_container()` method combines the logic for `beginning`/`ending` fields (projects + tasks + `$inbox`)
- A new `resolve_anchor()` method for `before`/`after` fields (tasks only, name resolution, no `$inbox`)

**How name resolution extends from list filters to write fields:**

List filters (existing `resolve_filter`): value -> ID match -> substring match -> return list (0+ results)
Write fields (new `resolve_entity`): value -> `$` check -> ID match -> name substring match -> return exactly 1 or raise

The key difference: write resolution is **exact-one-or-error**, filter resolution is **best-effort-multi-match**. Two separate code paths with shared helpers (`_match_by_name` is close but needs adaptation for the write-side error messages and `$` prefix).

**Concrete method signatures:**

```python
# System location detection (shared)
def _resolve_system_location(self, value: str) -> str | None:
    """If $-prefixed, return canonical ID or raise. Returns None if not $-prefixed."""

# Write-side: exactly one result or error
async def resolve_entity(self, value: str, entity_type: str) -> str:
    """Three-step: $prefix -> ID -> name. Used by parent, beginning/ending."""

# Filter-side: add $inbox handling to existing flow
def resolve_filter(self, value: str, entities: Sequence[_HasIdAndName]) -> list[str]:
    """Existing + $prefix step. Returns list of matching IDs."""
```

### 10. `service/domain.py` — Business Rule Updates

**`_process_container_move`:**
- Currently handles `container_id: None` as inbox. After: no `None` case (Pydantic rejects `null`). `$inbox` string flows through resolver.
- Resolver returns `$inbox` as-is for system locations — no repository lookup needed.
- Cycle detection: skip for `$inbox` (inbox is not a task, can't create cycles).

**`_process_anchor_move`:**
- On task lookup failure: probe if `anchor_id` is a known container (project or `$inbox`)
- If yes: targeted error mentioning `beginning`/`ending`
- If no: existing "Anchor task not found" error

**New: contradictory filter detection** (in `_ListTasksPipeline` or `DomainLogic`):
- `project: "$inbox"` + `inInbox: false` -> hard error
- `project: "$inbox"` + `inInbox: true` -> silent (redundant)
- `inInbox: true` + `project: "Work"` -> empty result + warning

**New: `get_project("$inbox")` guard:**
- Service-level check before repository call
- Descriptive error: "Inbox is a system location, not a project."

**New: `list_projects` inbox warning:**
- After filter resolution, if name filter would have substring-matched "Inbox" -> warning

### 11. `repository/hybrid/hybrid.py` — Mapper Changes

**`_build_parent_ref` rewrite:**

Before: returns `{"type": "task/project", "id": ..., "name": ...} | None`
After: returns `{"project": {"id": ..., "name": ...}} | {"task": {"id": ..., "name": ...}}` (never null)

- Inbox case (no parent task, no containing project): `{"project": {"id": "$inbox", "name": "Inbox"}}`
- Uses constants from `config.py`

**New: `_build_project_ref` function:**
- Reads `containingProjectInfo` column (already fetched)
- If null -> `{"id": "$inbox", "name": "Inbox"}`
- If set -> `{"id": project_id, "name": project_name}` from lookup

**`_map_task_row` changes:**
- Add `"project": _build_project_ref(row, project_info_lookup)`
- Change `"parent"` to use rewritten `_build_parent_ref`
- Remove `"in_inbox"` key

**`_map_project_row` changes:**
- `"folder"` -> from bare `row["folder"]` to `{"id": folder_id, "name": folder_name}` using folder lookup
- `"next_task"` -> from bare `row["nextTask"]` to `{"id": task_id, "name": task_name}` using task name lookup

**`_map_tag_row` changes:**
- `"parent"` -> from bare `row["parent"]` to `{"id": tag_id, "name": tag_name}` using tag name lookup

**`_map_folder_row` changes:**
- `"parent"` -> from bare `row["parent"]` to `{"id": folder_id, "name": folder_name}` using folder lookup

**Data availability for enrichment:**
- Tag names: `_build_tag_name_lookup` already exists
- Task names: `task_name_lookup` already passed to `_map_task_row`
- Folder names: new lookup needed (simple dict from folder query — small collection)
- Project names: `project_info_lookup` already exists

### 12. `repository/bridge_only/adapter.py` — Parallel Mapper Changes

The bridge-only adapter has its own mapper for `ParentRef`. Same changes apply:
- Tagged object pattern for `parent`
- New `project` field
- Remove `inInbox`
- Rich references for all entities

### 13. `contracts/use_cases/add/tasks.py` — `parent` Handling

`AddTaskCommand.parent`:
- Type stays `str | None`
- `None` -> inbox + warning (service layer, not contract)
- `"$inbox"` -> inbox (resolver handles)
- String -> resolver three-step cascade

`AddTaskRepoPayload.parent`:
- After resolution, `$inbox` -> `None` for bridge (bridge expects null for inbox)
- This conversion happens in PayloadBuilder

### 14. `service/payload.py` — PayloadBuilder Changes

- When resolved parent is `$inbox`, convert to `None` for `AddTaskRepoPayload.parent`
- Move container payloads: when container is `$inbox`, convert to `None` for bridge

### 15. `agent_messages/` — Description Updates

- 7 tool descriptions updated for `{id, name}` reference format
- `list_tasks` description: explain `parent` vs `project` divergence for subtasks
- New error messages for system location errors, contradictory filters
- New warning for `parent: null` on add_tasks

---

## Data Flow Changes

### Write: `add_tasks` with `parent: "$inbox"`

```
Agent: {"parent": "$inbox"}
  -> AddTaskCommand(parent="$inbox")
  -> Service._AddTaskPipeline._resolve_parent()
    -> Resolver.resolve_entity("$inbox")
      -> _resolve_system_location("$inbox") -> returns "$inbox"
  -> PayloadBuilder: "$inbox" -> parent=None for bridge
  -> AddTaskRepoPayload(parent=None)
  -> Bridge: creates task in inbox
```

### Write: `add_tasks` with `parent: "My Project"`

```
Agent: {"parent": "My Project"}
  -> AddTaskCommand(parent="My Project")
  -> Service._AddTaskPipeline._resolve_parent()
    -> Resolver.resolve_entity("My Project")
      -> not $-prefix
      -> ID match: no project/task with id="My Project"
      -> Name match: find project where "my project" in name.lower()
        -> 1 match: return project.id
        -> 0 matches: error with suggestions
        -> 2+ matches: error listing all matches with IDs
  -> PayloadBuilder: uses resolved ID
```

### Write: `edit_tasks` with `ending: "$inbox"`

```
Agent: {"moveTo": {"ending": "$inbox"}}
  -> MoveAction(ending="$inbox")  [Patch[str], no null accepted]
  -> DomainLogic.process_move()
    -> _process_container_move("ending", "$inbox", task_id)
      -> Resolver.resolve_container("$inbox")
        -> $-prefix detected -> returns "$inbox"
      -> Skip cycle detection (inbox not a task)
      -> return {"position": "ending", "container_id": None}  [bridge format]
```

### Read: Task output with `project` and tagged `parent`

```
SQLite row:
  parent=null, containingProjectInfo=null  (root inbox task)
  -> parent: {"project": {"id": "$inbox", "name": "Inbox"}}
  -> project: {"id": "$inbox", "name": "Inbox"}

SQLite row:
  parent="tParentTask", containingProjectInfo="pWorkProject"  (subtask in project)
  -> parent: {"task": {"id": "tParentTask", "name": "Parent Task"}}
  -> project: {"id": "pWorkProject", "name": "Work"}
```

### Filter: `list_tasks(project="$inbox")`

```
Agent: {"project": "$inbox"}
  -> _ListTasksPipeline._resolve_project()
    -> Resolver.resolve_filter("$inbox", projects)
      -> $-prefix detected
      -> System location -> don't search projects
      -> Return special signal for inbox filter
    -> Convert to in_inbox=True on RepoQuery
  -> Check contradictory filters ($inbox + inInbox=false -> error)
```

---

## Suggested Build Order

The dependency chain drives phase ordering. Each phase builds on the previous.

### Phase 1: Foundation — Constants + New Models

**What:** `config.py` constants, `ProjectRef`, `TaskRef`, `FolderRef` in `models/common.py`

**Why first:** Every subsequent phase imports these. Zero risk — pure additions, no existing code changes.

**Scope:**
- Add 3 constants to `config.py`
- Add 3 new model classes to `models/common.py`
- `TaskParent` tagged-object wrapper model
- Unit tests for `TaskParent` validation (exactly-one-key)

**Does not touch:** `ParentRef` (still exists, removed later), `Task` model, mappers

### Phase 2: Resolver — System Locations + Write-Side Name Resolution

**What:** `$`-prefix detection, three-step entity resolution, `resolve_container()`, `resolve_anchor()`

**Why second:** The resolver is the central integration point. Write pipelines and filter pipelines both need it. Building it before the consumers means clean testing.

**Scope:**
- `_resolve_system_location()` private method
- `resolve_entity()` for write-side (parent, containers)
- `resolve_anchor()` for before/after (task-only, with container probe error)
- `resolve_filter()` updated for `$`-prefix
- Error messages in `agent_messages/errors.py`
- Tests: system location detection, name resolution cascade, ambiguity errors, unknown `$` prefix

**Dependencies:** Phase 1 (constants)

### Phase 3: Write Pipeline Updates — `$inbox` + Name Resolution in Adds/Edits

**What:** Wire resolver into `_AddTaskPipeline`, `_EditTaskPipeline`, `MoveAction` type change, `PatchOrNone` elimination

**Why third:** Requires Phase 2 resolver. Write pipelines are self-contained — they don't affect read output.

**Scope:**
- `_AddTaskPipeline._resolve_parent()` -> use `resolve_entity()` with `$`/name support
- `parent: null` -> warning (service layer)
- `MoveAction.beginning`/`ending` -> `Patch[str]` (no null)
- `_process_container_move()` -> `$inbox` to `None` conversion for bridge
- `_process_anchor_move()` -> container probe on failure for better error
- `PayloadBuilder` -> `$inbox` -> `None` conversion
- `PatchOrNone` deleted from `contracts/base.py`
- Tests: add with `$inbox`, add with name, edit move to `$inbox`, null rejection, name resolution in moves

**Dependencies:** Phase 2 (resolver)

### Phase 4: Read Output — Model Changes + Mapper Rewrites

**What:** `Task.parent` tagged object, `Task.project` field, `inInbox` removal, rich references on all entities

**Why fourth:** Requires Phase 1 models. Independent of write changes (Phase 3), but placing after writes means the full `$inbox` round-trip is testable. This is the highest-risk phase (touches every output model and every mapper).

**Scope:**
- `Task` model: new `project` field, new `parent` type, remove `in_inbox`
- `Project` model: `folder` -> `FolderRef`, `next_task` -> `TaskRef`
- `Tag` model: `parent` -> `TagRef`
- `Folder` model: `parent` -> `FolderRef`
- `_build_parent_ref()` rewrite (tagged object, never null, inbox as `$inbox`)
- New `_build_project_ref()` function
- `_map_task_row()` updates
- `_map_project_row()` updates (folder/next_task enrichment, new folder lookup)
- `_map_tag_row()` updates (parent enrichment, new tag parent lookup)
- `_map_folder_row()` updates (parent enrichment)
- Bridge-only adapter parallel changes
- `ParentRef` removed from `models/common.py`
- Tests: mapper unit tests, cross-path equivalence, output schema regression

**Dependencies:** Phase 1 (models)

### Phase 5: Filter Updates — `$inbox` in Filters + Contradictory Detection

**What:** `project: "$inbox"` accepted in `list_tasks`, contradictory filter detection, `list_projects` inbox warning

**Why fifth:** Requires Phase 2 (resolver `$`-prefix), Phase 4 (output models — test assertions use new shapes). Filter logic is localized to `_ListTasksPipeline` and `DomainLogic`.

**Scope:**
- `_ListTasksPipeline._resolve_project()` -> handle `$inbox` (convert to `in_inbox=True`)
- Contradictory filter detection: `$inbox` + `inInbox: false` -> error
- Redundant filter: `$inbox` + `inInbox: true` -> silent
- `inInbox: true` + real project -> warning about empty result
- `get_project("$inbox")` -> descriptive error
- `list_projects` -> inbox warning when name filter matches "Inbox"
- Tests: filter combinations, error messages, warning text

**Dependencies:** Phase 2 (resolver), Phase 4 (output models for assertions)

### Phase 6: Descriptions + Cleanup

**What:** Tool description updates in `agent_messages/descriptions.py`, final validation

**Why last:** Descriptions reference the final field shapes — must reflect the completed API.

**Scope:**
- 7 tool descriptions updated (`LIST_TASKS_TOOL_DOC`, etc.)
- `{id, name}` format for all reference fields
- `list_tasks` description: `parent` vs `project` explanation
- Remove stale description constants (e.g., `PARENT_REF_DOC`)
- AST enforcement test updates
- Output schema test updates (new field shapes)
- Cross-path equivalence test updates
- Golden master impact assessment (likely needs refresh for new output shape)

**Dependencies:** All previous phases

---

## Dependency Graph

```
Phase 1: Foundation (constants + models)
  |
  +---> Phase 2: Resolver ($prefix + name resolution)
  |       |
  |       +---> Phase 3: Write Pipelines ($inbox in adds/edits, PatchOrNone removal)
  |       |
  |       +---> Phase 5: Filters ($inbox in list_tasks, contradictory detection)
  |
  +---> Phase 4: Read Output (model changes + mapper rewrites)
  |
  +---> Phase 6: Descriptions + Cleanup (depends on all above)
```

Phases 3 and 4 are independent of each other (writes vs reads). Phase 5 depends on both 2 and 4.

---

## Key Integration Points

### 1. Resolver is the gateway for `$`-prefix

All `$`-prefix detection goes through the Resolver. No layer below (repository, bridge) ever sees `$inbox` as an ID -- the resolver translates it to `None` (for bridge payloads) or to a filter signal (for queries). This keeps the system location concept contained at the service boundary.

### 2. Bridge never sees `$inbox`

The bridge expects `null` for inbox. PayloadBuilder converts `$inbox` -> `None` before constructing repo payloads. This is consistent with "dumb bridge, smart Python."

### 3. Mappers produce `$inbox`, resolver consumes it

Read path: SQLite mapper detects "no containing project" -> emits `ProjectRef(id="$inbox", name="Inbox")`.
Write path: resolver detects `$inbox` -> routes to inbox handling.

Round-trip consistency: what the agent reads, it can write back.

### 4. `TaskParent` wrapper is output-only

The tagged object `{"project": {...}}` / `{"task": {...}}` pattern is only on the read side (output models). Write commands still use flat strings (`parent: "$inbox"`, `parent: "pXyz"`) -- the resolver handles the difference.

### 5. InMemoryBridge needs parallel updates

`InMemoryBridge` in `tests/doubles/` must produce the same output shapes as the SQLite mapper. The golden master tests enforce this. Any mapper change requires a parallel `InMemoryBridge` update.

---

## Anti-Patterns to Avoid

### Don't leak `$inbox` to the repository layer
Repository queries use IDs. `$inbox` is a service-layer concept. Convert to `in_inbox=True` or `parent=None` before it reaches the repo.

### Don't add a `type` discriminator field to `TaskParent`
Prior experience: `exclude_defaults=True` strips `Literal` defaults. The tagged-object pattern (key IS the discriminator) is proven in `MoveAction`.

### Don't make `project` field nullable
Every task has a containing project (inbox or real). Null would reintroduce the ambiguity this milestone eliminates.

### Don't resolve names in the repository layer
Name resolution is a service concern. Repository receives IDs only. This boundary is already established and must be maintained.

### Don't special-case `$inbox` in SQL queries
The inbox condition is already handled by the `inInbox` SQL column. Converting `project: "$inbox"` to `in_inbox=True` at the service layer reuses existing infrastructure.

---

## Sources

- Codebase analysis: `service/resolve.py`, `service/domain.py`, `service/service.py`, `contracts/base.py`, `contracts/shared/actions.py`, `models/common.py`, `models/task.py`, `repository/hybrid/hybrid.py`
- Milestone spec: `.research/updated-spec/MILESTONE-v1.3.1.md`
- Project context: `.planning/PROJECT.md`
