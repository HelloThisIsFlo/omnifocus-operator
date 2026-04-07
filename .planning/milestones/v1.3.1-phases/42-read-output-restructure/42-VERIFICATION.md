---
phase: 42-read-output-restructure
verified: 2026-04-06T21:45:00Z
status: passed
score: 12/12 must-haves verified
overrides_applied: 0
re_verification:
  previous_status: passed
  previous_score: 12/12
  note: "Previous verification was written at 20:30Z, before plan 04 (gap closure) completed at 21:19Z. This verification covers the complete phase including plan 04 fixes."
  gaps_closed:
    - "ParentRef serialization now excludes the None branch (plan 04 fix)"
    - "Root-task parent correctly classified as project parent in both code paths (plan 04 fix)"
    - "Project nextTask self-reference guard added to both hybrid and bridge paths (plan 04 fix)"
  gaps_remaining: []
  regressions: []
gaps: []
deferred: []
---

# Phase 42: Read Output Restructure — Verification Report

**Phase Goal:** Task output uses tagged parent discriminator (never null), includes project field, and all entity cross-references use rich {id, name} objects. Descriptions updated for all changed output fields.
**Verified:** 2026-04-06T21:45:00Z
**Status:** passed
**Re-verification:** Yes — previous verification pre-dated plan 04 (gap closure); this is a full re-check of all 12 success criteria including plan 04 fixes.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Task `parent` is a tagged object (`{"project": {id, name}}` or `{"task": {id, name}}`) — never null | VERIFIED | `ParentRef` in `models/common.py` has `project: ProjectRef | None` and `task: TaskRef | None` with `@model_validator(_exactly_one_key)`. `Task.parent: ParentRef` — required field, no default. |
| 2 | Inbox tasks have `parent: {"project": {id: "$inbox", name: "Inbox"}}` | VERIFIED | `_build_parent_and_project` in `hybrid.py` and `_adapt_parent_ref` in `adapter.py` both produce `inbox_ref` using `SYSTEM_LOCATIONS["inbox"]` when `containingProjectInfo` is None / no project assigned. |
| 3 | Task has a `project` field with `{id, name}` of containing project at any depth — never null, `$inbox` for inbox | VERIFIED | `Task.project: ProjectRef = Field(description=TASK_PROJECT_DESC)` — required, no default. All code paths produce it. Task schema shows `project` in `required` list. |
| 4 | `inInbox` field is absent from Task JSON output and schema | VERIFIED | `task.py` has no `in_inbox` field. `Task.model_json_schema()` confirmed free of `inInbox`/`in_inbox`. No production code references `t.in_inbox` or `task.in_inbox`. |
| 5 | `ParentRef` model is removed from the codebase | VERIFIED | Old `ParentRef(type: str, id: str, name: str)` is gone. `models/common.py` `ParentRef` now has only `project: ProjectRef | None` and `task: TaskRef | None` — no `type` field. The name was reused for the tagged wrapper (confirmed by plan notes and code inspection). |
| 6 | `Project.folder` returns `FolderRef {id, name}` instead of bare folder ID | VERIFIED | `project.py`: `folder: FolderRef | None = Field(default=None, description=PROJECT_FOLDER_DESC)`. `_map_project_row` produces `{"id": row["folder"], "name": folder_name_lookup.get(...)}`. `_enrich_project` in adapter converts bare string to `{id, name}`. |
| 7 | `Project.next_task` returns `TaskRef {id, name}` instead of bare task ID | VERIFIED | `project.py`: `next_task: TaskRef | None = Field(default=None, description=NEXT_TASK)`. `_map_project_row` line 428 guards against self-reference (`row["nextTask"] != task_id`) before producing `{id, name}`. |
| 8 | `Tag.parent` returns `TagRef {id, name}` instead of bare tag ID | VERIFIED | `tag.py`: `parent: TagRef | None = Field(default=None, description=TAG_PARENT_DESC)`. `_map_tag_row` produces enriched dict via `tag_name_lookup`. `_enrich_tag` handles bridge path. |
| 9 | `Folder.parent` returns `FolderRef {id, name}` instead of bare folder ID | VERIFIED | `folder.py`: `parent: FolderRef | None = Field(default=None, description=FOLDER_PARENT_DESC)`. `_map_folder_row` produces enriched dict via `folder_name_lookup`. `_enrich_folder` handles bridge path. |
| 10 | Enriched references are consistent across `get_*`, `list_*`, and `get_all` tools | VERIFIED | All 7 call sites in `hybrid.py` updated (`_read_all`, `_read_project`, `_read_tag`, `_list_tasks_sync`, `_list_projects_sync`, `_list_tags_sync`, `_list_folders_sync`). Bridge `adapt_snapshot` calls `_enrich_project`, `_enrich_tag`, `_enrich_folder`. 83 cross-path equivalence + output schema tests pass. |
| 11 | `list_tasks` description explains `parent` (immediate container) vs `project` (containing project at any depth) | VERIFIED | `LIST_TASKS_TOOL_DOC` contains: "Reconstruct hierarchy using parent (direct container) or project (containing project at any depth). For root tasks both point to the same project; for subtasks they diverge." |
| 12 | All descriptions use `{id, name}` format for enriched reference fields | VERIFIED | All 7 tool constants (GET_TASK, GET_PROJECT, GET_TAG, LIST_TASKS, LIST_PROJECTS, LIST_TAGS, LIST_FOLDERS) verified programmatically — all use `{id, name}` notation; no `camelCase` references in any of the 7. |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/models/common.py` | Tagged ParentRef with exactly-one validator and exclude_none model_dump | VERIFIED | `@model_validator(_exactly_one_key)`, `model_dump` override with `exclude_none=True` default, `project: ProjectRef | None`, `task: TaskRef | None` |
| `src/omnifocus_operator/models/task.py` | `parent: ParentRef`, `project: ProjectRef`, no `in_inbox` | VERIFIED | Required fields with no defaults; `in_inbox` absent; schema shows both in `required` |
| `src/omnifocus_operator/models/project.py` | `folder: FolderRef | None`, `next_task: TaskRef | None` | VERIFIED | Both enriched ref types present with descriptions |
| `src/omnifocus_operator/models/tag.py` | `parent: TagRef | None` | VERIFIED | Enriched ref type with `TAG_PARENT_DESC` |
| `src/omnifocus_operator/models/folder.py` | `parent: FolderRef | None` | VERIFIED | Enriched ref type with `FOLDER_PARENT_DESC` |
| `src/omnifocus_operator/agent_messages/descriptions.py` | All 7 tool constants + 8 new field constants | VERIFIED | `PARENT_REF_DOC`, `NEXT_TASK`, `FOLDER_PARENT_DESC`, `PROJECT_FOLDER_DESC`, `TAG_PARENT_DESC`, `TASK_PROJECT_DESC`, `PARENT_REF_PROJECT_FIELD`, `PARENT_REF_TASK_FIELD` — all exact values confirmed |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | `_build_folder_name_lookup`, `_build_parent_and_project`, is_root_in_project guard, nextTask self-ref guard | VERIFIED | Lines 288 (`_build_parent_and_project`), 312-316 (`is_root_in_project`), 428 (`nextTask != task_id`), 536 (`_build_folder_name_lookup`) |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | Tagged parent + enriched refs + is_root_in_project guard + nextTask self-ref guard | VERIFIED | `_adapt_parent_ref` (line 148) with `is_root_in_project` (line 164), `_enrich_project` with self-reference check (line 306), `_enrich_tag`, `_enrich_folder`, `SYSTEM_LOCATIONS` import |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` | Filters use new field paths | VERIFIED | Line 160: `t.project.id == inbox_id`, line 167: `t.project.id in pid_set`, folder_ids filter uses `p.folder.id` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/common.py ParentRef` | `models/task.py Task.parent` | import | WIRED | `from omnifocus_operator.models.common import ActionableEntity, ParentRef, ProjectRef` |
| `_build_parent_and_project` | `_map_task_row` | call returning tuple | WIRED | Line 346: `parent_ref, project_ref = _build_parent_and_project(...)` |
| `_build_folder_name_lookup` | `_map_project_row`, `_map_folder_row` in _read_all, _list_projects_sync, _list_folders_sync | lookup parameter | WIRED | Lines 650, 883, 941 in hybrid.py |
| `adapter.py adapt_snapshot` | `_enrich_project`, `_enrich_tag`, `_enrich_folder` | direct calls | WIRED | Lines 360-364 in adapter.py |
| `descriptions.py tool constants` | `server.py` tool registration | `description=CONSTANT` parameter | WIRED | Lines 146, 158, 245 in server.py import and use `GET_TASK_TOOL_DOC`, `GET_PROJECT_TOOL_DOC`, `LIST_TASKS_TOOL_DOC` |
| `SYSTEM_LOCATIONS` | `hybrid.py` and `bridge_only.py` | import | WIRED | Both files confirmed to import and use `SYSTEM_LOCATIONS["inbox"]` |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `hybrid.py _map_task_row` | `parent_ref`, `project_ref` | `_build_parent_and_project` → SQLite `parent` column + `containingProjectInfo` + `project_info_lookup` | Yes — SQL joins populate real project IDs and names | FLOWING |
| `hybrid.py _map_project_row` | `folder`, `next_task` | `folder_name_lookup` (`_build_folder_name_lookup`) and `task_name_lookup` | Yes — both lookups populated from DB queries; self-reference guard filters out empty-project nextTask | FLOWING |
| `hybrid.py _map_tag_row` | `parent` | `tag_name_lookup` from Context table query | Yes — populated from real SQLite query | FLOWING |
| `adapter.py _adapt_parent_ref` | `parent`, `project` | Bridge fields `parent`, `project`, `parentName`, `projectName` | Yes — bridge provides real IDs and names from OmniFocus | FLOWING |
| `adapter.py _enrich_project` | `folder`, `next_task` | `folder_names` and `task_names` dicts built from bridge snapshot | Yes — populated from full bridge snapshot entity lists; self-reference guard on nextTask | FLOWING |

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `ParentRef(project=...).model_dump()` — no `task: null` key | `{'project': {'id': 'proj-001', 'name': 'My Project'}}` | PASS |
| `ParentRef(task=...).model_dump()` — no `project: null` key | `{'task': {'id': 'task-001', 'name': 'My Task'}}` | PASS |
| `Task.model_json_schema()` — `parent` and `project` in required, no `inInbox` | Required: `[..., 'parent', 'project']`; no `inInbox` | PASS |
| All 7 description constants contain `{id, name}` notation | Verified programmatically | PASS |
| Full test suite (1604 tests) | 1604 passed, 98.08% coverage, 24.41s | PASS |
| Output schema + cross-path equivalence tests (83 tests) | 83 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MODL-04 | 42-01 | Task `parent` uses tagged object discriminator | SATISFIED | New `ParentRef` with `project\|task` fields and exactly-one validator; model_dump excludes None branch |
| MODL-05 | 42-01 | Task `parent` never null — inbox as `$inbox` ProjectRef | SATISFIED | `Task.parent: ParentRef` required; all paths produce non-null using `SYSTEM_LOCATIONS["inbox"]` |
| MODL-06 | 42-01 | Task has `project` field (`ProjectRef`), never null | SATISFIED | `Task.project: ProjectRef` required field; all code paths produce it |
| MODL-07 | 42-01 | `inInbox` removed from Task output | SATISFIED | Field absent from `task.py` and schema; no production code references it |
| MODL-08 | 42-01 | Old `ParentRef(type, id, name)` removed | SATISFIED | Old type field gone; new tagged wrapper uses `project\|task` keys only |
| READ-01 | 42-02 | Task `project` field present with `{id, name}` at any nesting depth | SATISFIED | `_build_parent_and_project` resolves via `containingProjectInfo` at any depth |
| READ-02 | 42-02 | Inbox tasks have `project: {id: "$inbox", name: "Inbox"}` | SATISFIED | Fallback to `inbox_ref` using `SYSTEM_LOCATIONS["inbox"]` when no `containingProjectInfo` |
| READ-03 | 42-02 | `Project.folder` returns `FolderRef {id, name}` | SATISFIED | `_map_project_row` produces enriched dict; `_enrich_project` handles bridge path |
| READ-04 | 42-02 + 42-04 | `Project.next_task` returns `TaskRef {id, name}`, null when no children | SATISFIED | `_map_project_row` produces `{id, name}` dict; plan 04 added `row["nextTask"] != task_id` self-reference guard |
| READ-05 | 42-02 | `Tag.parent` returns `TagRef {id, name}` | SATISFIED | `_map_tag_row` produces enriched dict via `tag_name_lookup` |
| READ-06 | 42-02 | `Folder.parent` returns `FolderRef {id, name}` | SATISFIED | `_map_folder_row` produces enriched dict via `folder_name_lookup` |
| READ-07 | 42-03 | Enriched references work across `get_*`, `list_*`, and `get_all` | SATISFIED | All 7 call sites in `hybrid.py` updated; bridge `adapt_snapshot` enriches bulk path |
| DESC-01 | 42-01 | `list_tasks` description explains `parent` vs `project` hierarchy | SATISFIED | `LIST_TASKS_TOOL_DOC` contains explicit parent vs project explanation with divergence for subtasks |
| DESC-02 | 42-01 | All descriptions use `{id, name}` format for enriched reference fields | SATISFIED | All 7 tool constants verified — GET_TASK, GET_PROJECT, GET_TAG, LIST_TASKS, LIST_PROJECTS, LIST_TAGS, LIST_FOLDERS |

### Anti-Patterns Found

No blockers or warnings. All `None` checks in tests are on legitimately nullable fields (`Tag.parent`, `Folder.parent`, `Project.folder`, `Project.next_task`). No production code references old field shapes.

### Human Verification Required

None — all success criteria are verifiable programmatically. The test suite (1604 tests, 98% coverage) covers the full read path including schema validation, cross-path equivalence, ParentRef serialization edge cases, and the plan 04 bug fixes.

### Gaps Summary

No gaps. All 12 roadmap success criteria verified. All 14 requirement IDs from plan frontmatter (MODL-04 through MODL-08, READ-01 through READ-07, DESC-01, DESC-02) are satisfied with concrete code evidence.

Plan 04 gap closure is confirmed complete: ParentRef serializes only the set branch (exclude_none), root-task parent is correctly classified as project parent in both hybrid and bridge paths, and project nextTask self-reference is filtered out in both paths. 1604 tests pass (up from 1598 pre-plan 04, with 5 new regression tests added).

**Note on SC #5 wording:** The roadmap states "ParentRef model is removed from the codebase" but REQUIREMENTS.md (MODL-08) and the plans clarify this means the *old* `ParentRef(type, id, name)` shape is removed. The implementation reused the `ParentRef` name for the new tagged wrapper — this is the correct interpretation per plan 01 decisions.

---

_Verified: 2026-04-06T21:45:00Z_
_Verifier: Claude (gsd-verifier)_
