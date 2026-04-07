# Phase 42: Read Output Restructure - Research

**Researched:** 2026-04-06
**Domain:** Pydantic model restructuring, SQLite/bridge mapper enrichment, tool description updates
**Confidence:** HIGH

## Summary

Phase 42 restructures the read-side output of all entity models. The core changes: (1) Task `parent` becomes a tagged discriminated object (never null), (2) new `project` field on Task, (3) `inInbox` removed from output, (4) all cross-entity references (folder, next_task, tag parent, folder parent) become `{id, name}` rich objects, (5) all tool descriptions rewritten to new format.

The codebase has strong established patterns for all required changes. The `MoveAction` model provides the exact template for the exactly-one validator on the new `ParentRef`. Existing lookup builders (`_build_tag_name_lookup`, `_build_task_name_lookup`, `_build_project_info_lookup`) provide the pattern for the new `_build_folder_name_lookup`. The adapter layer already transforms parent refs -- it just needs to output the new shape.

**Primary recommendation:** Layer changes bottom-up: models first (ParentRef + field type changes), then mappers/adapters (produce new shapes), then bridge_only filters (fix broken attribute access), then descriptions (verbatim from CONTEXT.md).

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions
- D-01: Reuse the name `ParentRef` for the new tagged object wrapper model
- D-02: Wrapper model with `project: ProjectRef | None = None` and `task: TaskRef | None = None`, plus exactly-one `@model_validator`
- D-03: `Task.parent: ParentRef` -- never null, no default. Inbox uses `{"project": {"id": "$inbox", "name": "Inbox"}}`
- D-04: `Task.project: ProjectRef` -- never null, no default. Source: `containingProjectInfo` SQLite column
- D-05: ParentRef class docstring: `"Direct parent of this task. Exactly one key present: 'project' or 'task', each with {id, name}."`
- D-06: `$inbox` detail goes on the `project` field description within ParentRef
- D-07: Delete `in_inbox: bool` from `Task` model
- D-08: `in_inbox` filter parameter on `list_tasks` STAYS
- D-09: Bridge_only filter switches from `t.in_inbox` to `t.project.id == SYSTEM_LOCATIONS["inbox"].id`
- D-09a: OmniFocus bridge `inInbox` only flags root-level inbox tasks; `project.id == "$inbox"` covers full hierarchy. Behavioral change intentional.
- D-10: Delete old `ParentRef(type, id, name)` from `models/common.py`, new `ParentRef` takes its place
- D-11: Update `models/__init__.py` imports, `_ns`, `__all__`, `model_rebuild()`
- D-12: Update all consumers: `hybrid.py` mapper, `adapter.py`, bridge_only filters, test fixtures, `conftest.py`
- D-13: Targeted single-row queries for `get_*` methods
- D-14: Full lookups for bulk paths. New: `_build_folder_name_lookup()`. Existing lookups passed to additional mappers
- D-15: Mapper function signatures gain additional lookup parameters
- D-18: All 7 tool description constants verbatim (see CONTEXT.md)
- D-19 through D-26: All field-level descriptions verbatim (see CONTEXT.md)

### Claude's Discretion
- D-16: Mapper helper split -- whether to split `_build_parent_ref` into two functions or build both fields inline
- D-17: Bridge adapter architecture for cross-entity enrichment
- `models/__init__.py` wiring details
- Test organization for new model shapes
- Whether adapter strips `inInbox` from bridge data explicitly or relies on model ignoring extras

### Deferred Ideas (OUT OF SCOPE)
- `in_inbox` SQL filter alignment with `project.id == "$inbox"` -- Phase 43 (FILT-01)
- Additional system locations (`$forecast`, `$flagged`) -- SLOC-F01, future milestone
- Position field, full task object in edit response, path field, field selection, null-stripping -- all future scope

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MODL-04 | Task `parent` uses tagged object discriminator | New ParentRef model with exactly-one validator (D-02), MoveAction pattern |
| MODL-05 | Task `parent` never null, inbox = `ProjectRef($inbox)` | D-03, SYSTEM_LOCATIONS config |
| MODL-06 | Task has `project` field (ProjectRef, never null) | D-04, `containingProjectInfo` already in SQLite |
| MODL-07 | `inInbox` removed from Task output | D-07, D-08 (filter stays), D-09 (bridge_only filter fix) |
| MODL-08 | Old `ParentRef` model removed | D-10, new ParentRef replaces it |
| READ-01 | Task `project` field present with `{id, name}` | Mapper enrichment via `project_info_lookup` |
| READ-02 | Inbox tasks have `project: {id: "$inbox", name: "Inbox"}` | SYSTEM_LOCATIONS constants |
| READ-03 | `Project.folder` returns `FolderRef {id, name}` | New `_build_folder_name_lookup()` |
| READ-04 | `Project.next_task` returns `TaskRef {id, name}` | Existing `task_name_lookup` |
| READ-05 | `Tag.parent` returns `TagRef {id, name}` | Existing `tag_name_lookup` |
| READ-06 | `Folder.parent` returns `FolderRef {id, name}` | New `folder_name_lookup` |
| READ-07 | Enriched references across all tools | Cross-path equivalence tests (32 parametrized) |
| DESC-01 | `list_tasks` describes `parent` vs `project` | Verbatim constant in D-18 |
| DESC-02 | All descriptions use `{id, name}` format | Verbatim constants D-18, D-19 through D-26 |

</phase_requirements>

## Architecture Patterns

### Change Map

```
models/common.py          -- Delete old ParentRef, create new ParentRef (tagged wrapper)
                          -- No changes to ProjectRef, TaskRef, FolderRef, TagRef
models/task.py            -- parent: ParentRef (not Optional), add project: ProjectRef, remove in_inbox
models/project.py         -- folder: FolderRef | None, next_task: TaskRef | None
models/tag.py             -- parent: TagRef | None
models/folder.py          -- parent: FolderRef | None
models/__init__.py        -- Update _ns, model_rebuild() calls

repository/hybrid/hybrid.py:
  _build_parent_ref()     -- Return tagged dict: {"project": {id, name}} or {"task": {id, name}}
  _build_folder_name_lookup()  -- NEW: {folder_id: folder_name}
  _map_task_row()         -- Add "project" field, remove "in_inbox", parent uses new shape
  _map_project_row()      -- folder: {id, name}, next_task: {id, name}
  _map_tag_row()          -- parent: {id, name}
  _map_folder_row()       -- parent: {id, name}
  _read_all()             -- Build folder_name_lookup, pass to mappers
  _read_task()            -- Build project field (targeted query)
  _read_project()         -- Build folder/next_task enrichment (targeted queries)
  _read_tag()             -- Build tag parent name (targeted query)
  _list_tasks_sync()      -- Pass folder_name_lookup to mapper
  _list_projects_sync()   -- Pass folder_name_lookup + task_name_lookup to mapper

repository/bridge_only/adapter.py:
  _adapt_parent_ref()     -- Build tagged dict + project field from bridge data
  adapt_snapshot()        -- Cross-entity enrichment: build name dicts, enrich all entities

repository/bridge_only/bridge_only.py:
  list_tasks() line 157   -- t.in_inbox -> t.project.id == SYSTEM_LOCATIONS["inbox"].id
  list_tasks() line 162   -- t.parent.id in pid_set -> t.project.id in pid_set
  list_projects() line 207 -- p.folder in fid_set -> p.folder.id in fid_set

agent_messages/descriptions.py -- 7 tool doc constants + 8 field description constants
```

### Pattern: Tagged Wrapper Model (from MoveAction)

The new ParentRef follows the MoveAction exactly-one pattern. Key difference: MoveAction uses `CommandModel` with `UNSET`; ParentRef uses `OmniFocusBaseModel` with `None`.

```python
# Source: CONTEXT.md D-02, verified against contracts/shared/actions.py [VERIFIED: codebase]
class ParentRef(OmniFocusBaseModel):
    __doc__ = PARENT_REF_DOC  # D-24
    
    project: ProjectRef | None = Field(default=None, description=PARENT_REF_PROJECT_FIELD)  # D-25
    task: TaskRef | None = Field(default=None, description=PARENT_REF_TASK_FIELD)  # D-26

    @model_validator(mode="after")
    def _exactly_one_key(self) -> ParentRef:
        has_project = self.project is not None
        has_task = self.task is not None
        if has_project == has_task:  # Both set or neither set
            msg = "Exactly one of 'project' or 'task' must be set."
            raise ValueError(msg)
        return self
```

### Pattern: Mapper Enrichment (existing)

```python
# Current pattern in _build_parent_ref -- gains project field [VERIFIED: codebase]
# After: returns (parent_dict, project_dict) tuple or builds both inline
def _build_parent_ref(row, project_info_lookup, task_name_lookup):
    parent_task_id = row["parent"]
    if parent_task_id is not None:
        return {"task": {"id": parent_task_id, "name": task_name_lookup.get(parent_task_id, "")}}
    # ... project case returns {"project": {...}}
    # ... inbox case returns {"project": {"id": "$inbox", "name": "Inbox"}}
```

### Pattern: Lookup Builder (existing, extend)

```python
# Existing pattern [VERIFIED: codebase hybrid.py line 461-496]
def _build_folder_name_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Execute _FOLDERS_SQL and return {folder_id: folder_name}."""
    rows = conn.execute(_FOLDERS_SQL).fetchall()
    return {row["persistentIdentifier"]: row["name"] for row in rows}
```

### Pattern: Targeted Single-Row Enrichment (existing)

```python
# Current pattern in _read_task for parent resolution [VERIFIED: codebase hybrid.py line 678-686]
# Extend to _read_project (folder name, next_task name) and _read_tag (parent tag name)
parent_task_id = row["parent"]
if parent_task_id is not None:
    name_row = conn.execute(
        "SELECT name FROM Task WHERE persistentIdentifier = ?", (parent_task_id,)
    ).fetchone()
```

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Inbox parent ref | Hardcoded `"$inbox"` / `"Inbox"` strings | `SYSTEM_LOCATIONS["inbox"].id` / `.name` | Single source of truth, tested |
| Exactly-one validation | Manual if/else chains | `@model_validator` (MoveAction pattern) | Proven pattern in codebase |
| Cross-entity name resolution | N+1 queries per entity | Batch lookup dicts | Performance: one query per entity type, O(1) lookups |

## Common Pitfalls

### Pitfall 1: Bridge_only Filter Breakage
- **What goes wrong:** After `parent` changes shape from `ParentRef(type, id, name)` to tagged wrapper `ParentRef(project=ProjectRef|None, task=TaskRef|None)`, the filter `t.parent.id in pid_set` breaks (`.id` is no longer a direct attribute)
- **How to avoid:** Use `t.project.id in pid_set` -- the new `project` field on Task is the correct filter target (D-09)
- **Specific lines:** `bridge_only.py` line 157 (`in_inbox`), line 162 (`project_ids`), line 207 (`folder_ids`)

### Pitfall 2: Simulator Data Shape Mismatch
- **What goes wrong:** `simulator/data.py` uses new-shape camelCase dicts with `"inInbox"`, `"project": "proj-sim-001"`, `"parent": None`. The adapter must transform these to the new model shape
- **How to avoid:** The adapter's `_adapt_parent_ref` must produce tagged dict + project field. Simulator data keeps `"inInbox"` in raw form; adapter consumes it to build project field, then it can be stripped or ignored
- **Warning sign:** `ValidationError` on `Task.parent` or `Task.project` during simulator tests

### Pitfall 3: exclude_defaults=True and Literal Fields
- **What goes wrong:** If ParentRef used `Literal` discriminator fields, `exclude_defaults=True` would strip them from output
- **How to avoid:** Use `project: ProjectRef | None = None` + `task: TaskRef | None = None` -- the set field retains its value, the unset field is excluded (correct behavior per DL-12 decision)

### Pitfall 4: Forgetting to Pass Lookups in All Code Paths
- **What goes wrong:** `_map_project_row`, `_map_tag_row`, `_map_folder_row` gain new parameters. Easy to miss a call site
- **Call sites to update:**
  - `_read_all()` -- bulk path, all mappers
  - `_list_tasks_sync()` -- passes lookups to `_map_task_row`
  - `_list_projects_sync()` -- passes lookups to `_map_project_row`
  - `_list_tags_sync()` -- passes lookup to `_map_tag_row`
  - `_list_folders_sync()` -- passes lookup to `_map_folder_row`
  - `_read_project()` -- targeted queries for folder name, next_task name
  - `_read_tag()` -- targeted query for parent tag name
- **Warning sign:** `KeyError` or validation error on missing `id`/`name` in Ref objects

### Pitfall 5: Cross-Path Equivalence Test Data
- **What goes wrong:** The 32 parametrized cross-path tests use neutral seed data that must produce identical output from both repos. After model changes, the neutral data format and seed adapters need updating
- **How to avoid:** Update `tests/conftest.py` `make_task_dict` (parent shape, project field, remove inInbox-as-model-field), neutral data in cross-path tests, and both seed adapters (bridge-format, SQLite-format)

### Pitfall 6: Task.project for Subtasks
- **What goes wrong:** A subtask's `parent` is `{"task": {id, name}}` but `project` must still resolve to the containing project at any depth. The `containingProjectInfo` SQLite column already provides this -- it points to the project at any nesting level
- **How to avoid:** For SQLite path: use `project_info_lookup` keyed by `containingProjectInfo`. For bridge path: the bridge provides `project` as the containing project ID (not the parent task), so adapt accordingly

## Code Examples

### New ParentRef Output Shape

```json
// Root task in a project
{
  "parent": {"project": {"id": "pJKx9xL5beb", "name": "Q3 Roadmap"}},
  "project": {"id": "pJKx9xL5beb", "name": "Q3 Roadmap"}
}

// Subtask
{
  "parent": {"task": {"id": "oRx3bL_UYq7", "name": "Review slides"}},
  "project": {"id": "pJKx9xL5beb", "name": "Q3 Roadmap"}
}

// Inbox task
{
  "parent": {"project": {"id": "$inbox", "name": "Inbox"}},
  "project": {"id": "$inbox", "name": "Inbox"}
}
```

### Bridge Adapter Cross-Entity Enrichment

```python
# Adapter must build name lookups from entity lists before per-entity adaptation
# [ASSUMED -- architecture detail, D-17 discretion]
def adapt_snapshot(raw: dict[str, Any]) -> dict[str, Any]:
    # Build cross-entity name lookups first
    project_names = {p["id"]: p["name"] for p in raw.get("projects", [])}
    task_names = {t["id"]: t["name"] for t in raw.get("tasks", [])}
    tag_names = {t["id"]: t["name"] for t in raw.get("tags", [])}
    folder_names = {f["id"]: f["name"] for f in raw.get("folders", [])}
    
    for task in raw.get("tasks", []):
        _adapt_task(task, project_names, task_names)
    for project in raw.get("projects", []):
        _adapt_project(project, folder_names, task_names)
    for tag in raw.get("tags", []):
        _adapt_tag(tag, tag_names)
    for folder in raw.get("folders", []):
        _adapt_folder(folder, folder_names)
    return raw
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pydantic |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/ -x -q --no-header` |
| Full suite command | `uv run pytest tests/ -q` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MODL-04 | Tagged parent discriminator | unit | `uv run pytest tests/test_output_schema.py -x -q` | Yes (schema validation) |
| MODL-05 | Parent never null, inbox = $inbox | unit | `uv run pytest tests/ -k "inbox and parent" -x -q` | Needs new tests |
| MODL-06 | Task.project field present | unit | `uv run pytest tests/ -k "project" -x -q` | Needs new tests |
| MODL-07 | inInbox absent from output | unit | `uv run pytest tests/test_output_schema.py -x -q` | Yes (schema catches) |
| MODL-08 | Old ParentRef removed | unit | grep-based CI check | N/A |
| READ-03 | Project.folder = FolderRef | unit | `uv run pytest tests/test_hybrid_repository.py -x -q` | Needs updates |
| READ-04 | Project.next_task = TaskRef | unit | `uv run pytest tests/test_hybrid_repository.py -x -q` | Needs updates |
| READ-05 | Tag.parent = TagRef | unit | `uv run pytest tests/test_hybrid_repository.py -x -q` | Needs updates |
| READ-06 | Folder.parent = FolderRef | unit | `uv run pytest tests/test_hybrid_repository.py -x -q` | Needs updates |
| READ-07 | Enriched refs across all tools | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | Yes (needs data updates) |
| DESC-01 | list_tasks description | unit | `uv run pytest tests/ -k "description" -x -q` | Yes (AST enforcement) |
| DESC-02 | {id, name} format in descriptions | unit | `uv run pytest tests/ -k "description" -x -q` | Yes (AST enforcement) |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/ -x -q --no-header`
- **Per wave merge:** `uv run pytest tests/ -q`
- **Phase gate:** Full suite green before `/gsd-verify-work`

### Wave 0 Gaps
- Existing tests cover schema validation (`test_output_schema.py`) and cross-path equivalence (`test_cross_path_equivalence.py`)
- Tests need DATA updates (fixtures, neutral data) rather than new test files
- New assertions needed for: inbox parent shape, project field presence, enriched ref shapes
- No new test framework or infrastructure required

## Security Domain

Not applicable. This phase is purely data-model restructuring with no authentication, input validation from external sources, cryptography, or access control changes. All changes are internal read-side output shape transformations.

## Assumptions Log

| # | Claim | Section | Risk if Wrong |
|---|-------|---------|---------------|
| A1 | Bridge adapter enrichment can build name dicts from entity lists before per-entity adaptation | Code Examples | Adapter architecture may need different approach -- low risk, D-17 is discretion area |
| A2 | `containingProjectInfo` SQLite column correctly resolves to the project at any nesting depth for subtasks | Architecture Patterns | If wrong, subtask `project` field would be incorrect -- verifiable in golden master |

## Open Questions

1. **Bridge adapter: does it receive entity IDs or names in raw data?**
   - What we know: Bridge sends `"project": "proj-id"` and `"parent": "task-id"` as string IDs, plus `"projectName"` and `"parentName"` convenience fields
   - What's clear: The adapter already handles this mapping in `_adapt_parent_ref`
   - Recommendation: Extend existing pattern -- use name fields where available, build cross-entity lookups for folder/tag/next_task names

2. **Simulator data: explicit strip of `inInbox` or model ignores extras?**
   - What we know: Pydantic's `model_validate` with strict mode off ignores extra fields by default (depends on `model_config`)
   - Recommendation: Check `OmniFocusBaseModel` config. If extras are forbidden, adapter must explicitly strip `inInbox`. If ignored, no action needed. This is Claude's discretion per CONTEXT.md.

## Sources

### Primary (HIGH confidence)
- Codebase grep and file reads -- all model files, mapper code, adapter, descriptions, config
- CONTEXT.md D-01 through D-26 -- locked decisions verified against codebase structure
- Cross-path equivalence test structure (`test_cross_path_equivalence.py`)

### Secondary (MEDIUM confidence)
- MoveAction validator pattern -- verified in `contracts/shared/actions.py`
- `exclude_defaults=True` behavior with Optional fields -- standard Pydantic v2 behavior [VERIFIED: codebase uses this pattern]

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- pure Pydantic v2, no new dependencies
- Architecture: HIGH -- all patterns already exist in codebase, extending not inventing
- Pitfalls: HIGH -- identified from direct code reading, specific line numbers documented

**Research date:** 2026-04-06
**Valid until:** 2026-05-06 (stable -- internal refactoring, no external dependencies)
