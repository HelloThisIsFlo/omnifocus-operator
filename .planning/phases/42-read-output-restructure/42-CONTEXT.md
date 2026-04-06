# Phase 42: Read Output Restructure - Context

**Gathered:** 2026-04-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Task output uses tagged parent discriminator (never null), includes new `project` field, removes `inInbox` from output, and all entity cross-references use rich `{id, name}` objects. All tool descriptions updated for changed output fields. No new tools, no filter changes, no write changes.

</domain>

<decisions>
## Implementation Decisions

### Tagged Parent Model (MODL-04, MODL-05)
- **D-01:** Reuse the name `ParentRef` for the new tagged object wrapper model — old `ParentRef` is deleted and replaced in the same phase
- **D-02:** Wrapper model with `project: ProjectRef | None = None` and `task: TaskRef | None = None`, plus exactly-one `@model_validator` — same pattern as `MoveAction`
- **D-03:** `Task.parent: ParentRef` — never null, no default. Inbox tasks use `{"project": {"id": "$inbox", "name": "Inbox"}}`
- **D-04:** `Task.project: ProjectRef` — never null, no default. Containing project at any nesting depth, or `$inbox` for inbox tasks. Data source: `containingProjectInfo` SQLite column (already available in `project_info_lookup`)

### ParentRef Docstring (follows MoveAction pattern)
- **D-05:** Class docstring: `"Direct parent of this task. Exactly one key present: 'project' or 'task', each with {id, name}."`
- **D-06:** `$inbox` detail goes on the `project` field description within ParentRef, not the class docstring

### inInbox Removal from Output (MODL-07)
- **D-07:** Delete `in_inbox: bool` from `Task` model
- **D-08:** `in_inbox` filter parameter on `list_tasks` STAYS (filter vs output are independent)
- **D-09:** Bridge_only filter switches from `t.in_inbox` to `t.project.id == SYSTEM_LOCATIONS["inbox"].id` — this broadens the filter to include subtasks of inbox tasks (correct per milestone spec)
- **D-09a:** Note: OmniFocus bridge `inInbox` only flags root-level inbox tasks. Our `project.id == "$inbox"` covers the full hierarchy. Golden master should confirm this understanding. If wrong, fix in a follow-up.

### ParentRef Removal (MODL-08)
- **D-10:** Delete old `ParentRef(type, id, name)` from `models/common.py`. New `ParentRef` (tagged wrapper) takes its place in the same file
- **D-11:** Update `models/__init__.py` imports, `_ns`, `__all__`, `model_rebuild()`
- **D-12:** Update all consumers: `hybrid.py` mapper, `adapter.py`, bridge_only filters, test fixtures, `conftest.py`

### Enrichment Strategy (READ-03 through READ-07)
- **D-13:** Targeted single-row queries for `get_*` methods (follow existing `_read_task()` pattern: query only the one name needed)
- **D-14:** Full lookups for bulk paths (`_read_all`, `list_*`). New lookup needed: `_build_folder_name_lookup()`. Existing lookups `tag_name_lookup` and `task_name_lookup` passed to additional mappers
- **D-15:** Mapper function signatures gain additional lookup parameters (no context object/dataclass — just add params, follow existing pattern)

### Mapper Helper Split
- **D-16:** Claude's discretion on whether to split `_build_parent_ref` into two functions or build both fields inline in `_map_task_row`

### Bridge Adapter Enrichment
- **D-17:** Claude's discretion on adapter architecture — must produce same output shape as SQLite path. Cross-entity lookups needed (build name dicts from entity lists before per-entity adaptation). Cross-path equivalence tests enforce consistency

### Tool Descriptions — Format (DESC-01, DESC-02)
- **D-18:** New format for ALL tool descriptions:
  1. Tool description (one line)
  2. *(blank line)*
  3. `Fields:` (or `Fields per task:` for list tools) — flowing, no line breaks between items
  4. *(blank line)*
  5. Notable field explanations — one per line, format: `fieldName: explanation`
  6. NO "The response uses camelCase field names." — removed everywhere
  7. NO "Key" prefix — just "Fields:" or "Fields per [entity]:"

### Tool Descriptions — Verbatim Constants (DESC-01, DESC-02)

**IMPORTANT: The plan MUST include these descriptions verbatim. The executor MUST use exact wording, not paraphrase.**

**GET_TASK_TOOL_DOC:**
```python
GET_TASK_TOOL_DOC = (
    "Look up a single task by its ID.\n"
    "\n"
    "Fields: urgency, availability, dueDate, deferDate, plannedDate, "
    "effectiveDueDate, flagged, effectiveFlagged, "
    "tags [{id, name}], parent (project {id, name} or task {id, name}), "
    "project {id, name}, repetitionRule.\n"
    "\n"
    "parent: direct container — a project or parent task.\n"
    "project: containing project at any nesting depth, or $inbox.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)
```

**GET_PROJECT_TOOL_DOC:**
```python
GET_PROJECT_TOOL_DOC = (
    "Look up a single project by its ID.\n"
    "\n"
    "Fields: urgency, availability, dueDate, deferDate, plannedDate, "
    "effectiveDueDate, flagged, effectiveFlagged, "
    "tags [{id, name}], nextTask {id, name}, folder {id, name}, "
    "reviewInterval, nextReviewDate.\n"
    "\n"
    "nextTask: first available (unblocked) task — useful for identifying what to work on next.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)
```

**GET_TAG_TOOL_DOC:**
```python
GET_TAG_TOOL_DOC = (
    "Look up a single tag by its ID.\n"
    "\n"
    "Fields: availability, childrenAreMutuallyExclusive, parent {id, name}.\n"
    "\n"
    "childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."
)
```

**LIST_TASKS_TOOL_DOC:**
```python
LIST_TASKS_TOOL_DOC = (
    "List and filter tasks. All filters combine with AND logic.\n"
    "\n"
    "Returns a flat list. Reconstruct hierarchy using parent (direct container) "
    "or project (containing project at any depth). "
    "For root tasks both point to the same project; for subtasks they diverge. "
    "Inbox tasks use project id=\"$inbox\".\n"
    "\n"
    "Response: {items, total, hasMore, warnings?}\n"
    "\n"
    "Fields per task: urgency, availability, flagged, effectiveFlagged, "
    "dueDate, deferDate, plannedDate, effectiveDueDate, effectiveDeferDate, "
    "estimatedMinutes, tags [{id, name}], "
    "parent (project {id, name} or task {id, name}), "
    "project {id, name}, hasChildren, repetitionRule, completionDate.\n"
    "\n"
    "parent: direct container — a project or parent task.\n"
    "project: containing project at any nesting depth, or $inbox.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)
```

**LIST_PROJECTS_TOOL_DOC:**
```python
LIST_PROJECTS_TOOL_DOC = (
    "List and filter projects. All filters combine with AND logic.\n"
    "\n"
    "Response: {items, total, hasMore, warnings?}\n"
    "\n"
    "Fields per project: urgency, availability, flagged, effectiveFlagged, "
    "dueDate, deferDate, plannedDate, effectiveDueDate, "
    "tags [{id, name}], folder {id, name}, nextTask {id, name}, "
    "reviewInterval, nextReviewDate, hasChildren, repetitionRule, completionDate.\n"
    "\n"
    "nextTask: first available (unblocked) task — useful for identifying what to work on next.\n"
    "effective*: inherited from the parent hierarchy when not set directly."
)
```

**LIST_TAGS_TOOL_DOC:**
```python
LIST_TAGS_TOOL_DOC = (
    "List and filter tags.\n"
    "\n"
    "Returns a flat list. Each tag includes a parent field {id, name} "
    "that can be used to reconstruct hierarchy.\n"
    "\n"
    "Response: {items, total, hasMore}\n"
    "\n"
    "Fields per tag: availability, childrenAreMutuallyExclusive, parent {id, name}.\n"
    "\n"
    "childrenAreMutuallyExclusive: when true, child tags behave like radio buttons."
)
```

**LIST_FOLDERS_TOOL_DOC:**
```python
LIST_FOLDERS_TOOL_DOC = (
    "List and filter folders.\n"
    "\n"
    "Returns a flat list. Each folder includes a parent field {id, name} "
    "that can be used to reconstruct hierarchy.\n"
    "\n"
    "Response: {items, total, hasMore}\n"
    "\n"
    "Fields per folder: availability, parent {id, name}."
)
```

### Field-Level Descriptions
- **D-19:** PLACEHOLDER — field-level description constants (`NEXT_TASK`, `FOLDER_PARENT_DESC`, new `TASK_PROJECT_DESC`, updated `PARENT_REF_DOC` inner field descriptions) to be finalized in a follow-up discussion before planning. Must follow "no 'or null'" rule from milestone spec.

### Claude's Discretion
- Mapper helper split (D-16)
- Bridge adapter architecture for cross-entity enrichment (D-17)
- `models/__init__.py` wiring details
- Test organization for new model shapes
- Whether adapter strips `inInbox` from bridge data explicitly or relies on model ignoring extras

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone spec (primary source of truth)
- `.research/updated-spec/MILESTONE-v1.3.1.md` — Full design spec. Sections: Task Output Model Changes (lines 59-98), Rich References on All Output Models (lines 209-233), DL-12 tagged object decision (lines 453-462)

### Architecture & conventions
- `docs/architecture.md` — Three-layer architecture, Method Object pattern, "Dumb Bridge, Smart Python"
- `docs/model-taxonomy.md` — Core models (no suffix, `models/`), contract models (`contracts/`), naming conventions
- `docs/structure-over-discipline.md` — Schema = documentation, correct path = only path

### Models (modification targets)
- `src/omnifocus_operator/models/common.py` — `ParentRef` (delete old, create new), `ProjectRef`, `TaskRef`, `FolderRef`, `TagRef`
- `src/omnifocus_operator/models/task.py` — `Task.parent` (type change), add `Task.project`, remove `Task.in_inbox`
- `src/omnifocus_operator/models/project.py` — `Project.folder` (str → FolderRef), `Project.next_task` (str → TaskRef)
- `src/omnifocus_operator/models/tag.py` — `Tag.parent` (str → TagRef)
- `src/omnifocus_operator/models/folder.py` — `Folder.parent` (str → FolderRef)
- `src/omnifocus_operator/models/__init__.py` — Re-exports, `_ns`, `model_rebuild()`

### Repository layer (mapper rewrites)
- `src/omnifocus_operator/repository/hybrid/hybrid.py` — `_build_parent_ref` (rewrite), `_map_task_row` (add project field, remove in_inbox), `_map_project_row` (enrich folder + next_task), `_map_tag_row` (enrich parent), `_map_folder_row` (enrich parent), `_read_all` (add folder_name_lookup), `_read_project` / `_read_tag` (add targeted enrichment queries)
- `src/omnifocus_operator/repository/bridge_only/adapter.py` — `_adapt_parent_ref` (rewrite for tagged object + project field), cross-entity enrichment for folder/tag/folder parents
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — Filter updates: line 157 (`in_inbox` → `project.id`), line 162 (`parent.id` → `project.id`), line 207 (`folder` string → `folder.id`)

### Descriptions (update targets)
- `src/omnifocus_operator/agent_messages/descriptions.py` — 7 tool doc constants + field-level description constants

### System location constants
- `src/omnifocus_operator/config.py` — `SYSTEM_LOCATIONS["inbox"].id`, `.name` — use these, never hardcode

### Prior phases
- `.planning/phases/39-foundation-constants-reference-models/39-CONTEXT.md` — D-04: Ref models in common.py. D-03: import constants from config.py
- `.planning/phases/40-resolver-system-location-detection-name-resolution/40-CONTEXT.md` — Resolver cascade, SystemLocation dataclass
- `.planning/phases/41-write-pipeline-inbox-in-add-edit/41-CONTEXT.md` — PatchOrNone eliminated, null rejection validators

### Requirements
- `.planning/REQUIREMENTS.md` — MODL-04 through MODL-08, READ-01 through READ-07, DESC-01, DESC-02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `MoveAction` exactly-one validator in `contracts/shared/actions.py` — proven pattern for the new `ParentRef` tagged wrapper
- `_build_tag_name_lookup()`, `_build_task_name_lookup()`, `_build_project_info_lookup()` in `hybrid.py` — existing lookup builders to extend
- `SYSTEM_LOCATIONS["inbox"]` in `config.py` — `SystemLocation(id="$inbox", name="Inbox", type=EntityType.PROJECT)` for building inbox refs
- `TagRef(id, name)` in `models/common.py` — template pattern for all Ref models

### Established Patterns
- Row mappers return `dict[str, Any]`, Pydantic validates via `model_validate()` — enriched dicts flow through same pipeline
- Individual `get_*` methods build targeted ad-hoc lookups (minimal queries) vs bulk paths build full lookups
- Agent-facing docstrings: `__doc__ = CONSTANT` from `descriptions.py` with AST enforcement test
- `exclude_defaults=True` used in serialization — tagged objects avoid `Literal` fields for this reason (DL-12)

### Integration Points
- `_map_task_row()` — gains `project` field output, loses `in_inbox`, parent changes shape
- `_map_project_row()` — gains `folder_name_lookup` and `task_name_lookup` params for enrichment
- `_map_tag_row()` — gains `tag_name_lookup` param for parent enrichment
- `_map_folder_row()` — gains `folder_name_lookup` param for parent enrichment
- `bridge_only.py` filters — 3 lines break after model changes (see canonical_refs above)
- `test_output_schema.py` — auto-validates serialized output against JSON Schema, catches regressions
- Cross-path equivalence tests (32 parametrized) — enforce SQL and bridge paths produce identical output

### Gotchas
- Bridge_only `list_projects` filter (line 207): `p.folder in fid_set` breaks after `folder` becomes `FolderRef` — must become `p.folder.id in fid_set`
- Bridge_only `list_tasks` filter (line 162): `t.parent.id in pid_set` breaks — `parent` is now a wrapper with `project`/`task` keys. Use `t.project.id in pid_set` instead
- Bridge `inInbox` only flags root inbox tasks; `project.id == "$inbox"` covers full hierarchy. Behavioral change is intentional (correct per spec) but golden master should confirm
- Simulator fixture data (`simulator/data.py`) keeps `"inInbox"` in raw data — adapter consumes it to build `project` field, then strips it

</code_context>

<specifics>
## Specific Ideas

- All 7 tool description constants are verbatim in D-18 section — executor MUST use exact wording
- Field-level descriptions are a placeholder (D-19) — will be finalized before planning
- `SYSTEM_LOCATIONS["inbox"].id` and `.name` for all inbox references — never hardcode `"$inbox"` or `"Inbox"`
- Golden master re-capture required after this phase (mapper rewrites). Human-only per GOLD-01. Already noted in STATE.md

</specifics>

<deferred>
## Deferred Ideas

- Field-level descriptions (D-19) — follow-up discussion needed before planning
- `in_inbox` SQL filter alignment with `project.id == "$inbox"` — Phase 43 scope (FILT-01)
- Additional system locations (`$forecast`, `$flagged`) — SLOC-F01, future milestone

### Reviewed Todos (not folded)
- "Add position field to expose child task ordering" — future scope, not related to output restructure
- "Consider returning full task object in edit_tasks response" — edit pipeline, not read output
- "Add path field for hierarchical entities" — tracked as pending todo, separate concern
- "Field selection with curated defaults for read tools" — v1.4 scope
- "Null-stripping for read tool responses" — v1.4 scope
- "Move no-op warning check ordinal position not just container" — service layer, unrelated

</deferred>

---

*Phase: 42-read-output-restructure*
*Context gathered: 2026-04-06*
