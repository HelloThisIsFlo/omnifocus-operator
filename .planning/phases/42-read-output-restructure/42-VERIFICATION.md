---
phase: 42-read-output-restructure
verified: 2026-04-06T20:30:00Z
status: passed
score: 12/12 must-haves verified
gaps: []
deferred: []
---

# Phase 42: Read Output Restructure — Verification Report

**Phase Goal:** Task output uses tagged parent discriminator (never null), includes project field, and all entity cross-references use rich {id, name} objects. Descriptions updated for all changed output fields.
**Verified:** 2026-04-06T20:30:00Z
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths (from Roadmap Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Task `parent` is tagged object (`{project: {...}}` or `{task: {...}}`) — never null | VERIFIED | `ParentRef` in `models/common.py` has `project: ProjectRef | None` and `task: TaskRef | None` with `@model_validator`; `Task.parent: ParentRef` with no default |
| 2  | Inbox tasks have `parent: {"project": {id: "$inbox", name: "Inbox"}}` | VERIFIED | `_build_parent_and_project` in `hybrid.py` and `_adapt_parent_ref` in `adapter.py` both produce `inbox_ref` using `SYSTEM_LOCATIONS["inbox"]` when no parent/project |
| 3  | Task has `project` field `{id, name}` of containing project at any depth — never null, `$inbox` for inbox | VERIFIED | `Task.project: ProjectRef = Field(description=TASK_PROJECT_DESC)` (required, no default); mapper returns it for all cases |
| 4  | `inInbox` absent from Task JSON output and schema | VERIFIED | `task.py` has no `in_inbox` field; `Task.model_json_schema()` confirmed free of `inInbox`/`in_inbox` |
| 5  | Old `ParentRef(type, id, name)` model removed | VERIFIED | `models/common.py` `ParentRef` has only `project: ProjectRef | None` and `task: TaskRef | None`; no `type: str` field anywhere |
| 6  | `Project.folder` returns `FolderRef {id, name}` | VERIFIED | `project.py`: `folder: FolderRef | None = Field(...)`; mapper produces `{"id": ..., "name": ...}` dict |
| 7  | `Project.next_task` returns `TaskRef {id, name}` | VERIFIED | `project.py`: `next_task: TaskRef | None = Field(...)`; mapper produces `{"id": ..., "name": ...}` dict |
| 8  | `Tag.parent` returns `TagRef {id, name}` | VERIFIED | `tag.py`: `parent: TagRef | None = Field(...)`; `_map_tag_row` produces enriched dict |
| 9  | `Folder.parent` returns `FolderRef {id, name}` | VERIFIED | `folder.py`: `parent: FolderRef | None = Field(...)`; `_map_folder_row` produces enriched dict |
| 10 | Enriched references consistent across `get_*`, `list_*`, `get_all` | VERIFIED | 46 cross-path equivalence tests pass; all 7 call sites in `hybrid.py` updated; bridge adapter `adapt_snapshot` enriches via `_enrich_project`, `_enrich_tag`, `_enrich_folder` |
| 11 | `list_tasks` description explains `parent` vs `project` | VERIFIED | `LIST_TASKS_TOOL_DOC` contains: "Reconstruct hierarchy using parent (direct container) or project (containing project at any depth)" |
| 12 | All descriptions use `{id, name}` format for enriched reference fields | VERIFIED | All 7 tool constants verified: GET_TASK, GET_PROJECT, GET_TAG, LIST_TASKS, LIST_PROJECTS, LIST_TAGS, LIST_FOLDERS — all use `{id, name}` notation; `camelCase` not present |

**Score:** 12/12 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/models/common.py` | New tagged ParentRef wrapper | VERIFIED | `model_validator`, `project: ProjectRef | None`, `task: TaskRef | None`; exactly-one validator raises on both-set and neither-set |
| `src/omnifocus_operator/models/task.py` | Task with `parent: ParentRef`, `project: ProjectRef`, no `in_inbox` | VERIFIED | Required fields with no defaults; `in_inbox` absent |
| `src/omnifocus_operator/models/project.py` | `folder: FolderRef | None`, `next_task: TaskRef | None` | VERIFIED | Both enriched ref types present |
| `src/omnifocus_operator/models/tag.py` | `parent: TagRef | None` | VERIFIED | Enriched ref type with `TAG_PARENT_DESC` |
| `src/omnifocus_operator/models/folder.py` | `parent: FolderRef | None` | VERIFIED | Enriched ref type with `FOLDER_PARENT_DESC` |
| `src/omnifocus_operator/agent_messages/descriptions.py` | All 7 tool constants, 8 new field constants | VERIFIED | `PARENT_REF_DOC`, `NEXT_TASK`, `FOLDER_PARENT_DESC`, `PROJECT_FOLDER_DESC`, `TAG_PARENT_DESC`, `TASK_PROJECT_DESC`, `PARENT_REF_PROJECT_FIELD`, `PARENT_REF_TASK_FIELD` all present with exact values |
| `src/omnifocus_operator/repository/hybrid/hybrid.py` | All mappers enriched, `_build_folder_name_lookup`, `_build_parent_and_project` | VERIFIED | New helpers at lines 288 and 529; all 7 call sites updated |
| `src/omnifocus_operator/repository/bridge_only/adapter.py` | Tagged parent + enriched refs from bridge data | VERIFIED | `_adapt_parent_ref` (line 148), `_enrich_project/tag/folder` helpers, `SYSTEM_LOCATIONS` import |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` | Filters use new field paths | VERIFIED | `t.project.id == inbox_id`, `t.project.id in pid_set`, `p.folder.id in fid_set` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `models/common.py ParentRef` | `models/task.py Task.parent` | import | WIRED | `from omnifocus_operator.models.common import ActionableEntity, ParentRef, ProjectRef` |
| `_build_parent_and_project` | `_map_task_row` | call returning tuple | WIRED | Line 339: `parent_ref, project_ref = _build_parent_and_project(...)` |
| `_build_folder_name_lookup` | `_map_project_row`, `_map_folder_row` | lookup parameter | WIRED | Used in `_read_all`, `_list_projects_sync`, `_list_folders_sync` |
| `adapter.py adapt_snapshot` | enrichment helpers | `_enrich_project/tag/folder` calls | WIRED | Lines 350-354 in `adapt_snapshot` |
| `descriptions.py tool constants` | server tool registration | `__doc__ = CONSTANT` pattern | WIRED | Not directly reverified in this check but unchanged mechanism from prior phases; 1598 tests including server tests pass |
| `SYSTEM_LOCATIONS` | both `hybrid.py` and `bridge_only.py` | import | WIRED | Confirmed in both files |

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|-------------------|--------|
| `hybrid.py _map_task_row` | `parent_ref`, `project_ref` | `_build_parent_and_project` → SQLite row columns (`parent`, `containingProjectInfo`) + `project_info_lookup` | Yes — SQL joins populate real project names | FLOWING |
| `hybrid.py _map_project_row` | `folder`, `next_task` | `folder_name_lookup` (from `_build_folder_name_lookup`) and `task_name_lookup` | Yes — both lookups populated from DB queries | FLOWING |
| `hybrid.py _map_tag_row` | `parent` | `tag_name_lookup` | Yes — populated from Context table query | FLOWING |
| `adapter.py _adapt_parent_ref` | `parent`, `project` | Bridge-provided `parent`, `project`, `parentName`, `projectName` fields | Yes — bridge provides real IDs and names | FLOWING |
| `adapter.py adapt_snapshot` | `folder_names`, `tag_names`, `task_names` | Built from `raw["folders"]`, `raw["tags"]`, `raw["tasks"]` lists | Yes — populated from full bridge snapshot | FLOWING |

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| ParentRef exactly-one validator rejects both-set | Raises `ValueError: Exactly one of 'project' or 'task' must be set.` | PASS |
| ParentRef exactly-one validator rejects neither-set | Raises `ValueError` | PASS |
| Task schema has `parent` and `project` as required, no `inInbox` | Confirmed via `Task.model_json_schema()` | PASS |
| All description constants match expected values | 8 field constants + 7 tool constants all verified | PASS |
| Full test suite (1598 tests) | 1598 passed in 23.95s | PASS |
| Cross-path equivalence tests (46 tests) | 46 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| MODL-04 | 42-01 | Task `parent` uses tagged object discriminator | SATISFIED | New `ParentRef` with `project\|task` fields and exactly-one validator |
| MODL-05 | 42-01 | Task `parent` never null — inbox as `$inbox` ProjectRef | SATISFIED | `Task.parent: ParentRef` (required); mapper always produces non-null value using `SYSTEM_LOCATIONS["inbox"]` |
| MODL-06 | 42-01 | Task has `project` field (`ProjectRef`), never null | SATISFIED | `Task.project: ProjectRef` required field; all paths produce it |
| MODL-07 | 42-01 | `inInbox` removed from Task output | SATISFIED | Field absent from `task.py` and verified absent from JSON schema |
| MODL-08 | 42-01 | Old `ParentRef` model removed | SATISFIED | Old `type: str, id: str, name: str` shape gone; new tagged wrapper uses `project\|task` keys |
| READ-01 | 42-02 | Task `project` field present with `{id, name}` at any nesting depth | SATISFIED | `_build_parent_and_project` walks `containingProjectInfo` to resolve at any depth |
| READ-02 | 42-02 | Inbox tasks have `project: {id: "$inbox", name: "Inbox"}` | SATISFIED | Fallback to `inbox_ref` using `SYSTEM_LOCATIONS["inbox"]` when `containingProjectInfo` is None |
| READ-03 | 42-02 | `Project.folder` returns `FolderRef {id, name}` | SATISFIED | `_map_project_row` produces `{"id": row["folder"], "name": folder_name_lookup.get(...)}` |
| READ-04 | 42-02 | `Project.next_task` returns `TaskRef {id, name}` | SATISFIED | `_map_project_row` produces `{"id": row["nextTask"], "name": task_name_lookup.get(...)}` |
| READ-05 | 42-02 | `Tag.parent` returns `TagRef {id, name}` | SATISFIED | `_map_tag_row` produces enriched dict via `tag_name_lookup` |
| READ-06 | 42-02 | `Folder.parent` returns `FolderRef {id, name}` | SATISFIED | `_map_folder_row` produces enriched dict via `folder_name_lookup` |
| READ-07 | 42-03 | Enriched references work across `get_*`, `list_*`, and `get_all` | SATISFIED | All 7 call sites in `hybrid.py` updated; bridge adapter `adapt_snapshot` handles bulk path; 46 cross-path equivalence tests pass |
| DESC-01 | 42-01 | `list_tasks` description explains `parent` vs `project` hierarchy | SATISFIED | `LIST_TASKS_TOOL_DOC` contains explicit parent vs project explanation |
| DESC-02 | 42-01 | All descriptions use `{id, name}` format for enriched reference fields | SATISFIED | Verified: GET_TASK, GET_PROJECT, GET_TAG, LIST_TASKS, LIST_PROJECTS, LIST_TAGS, LIST_FOLDERS all use `{id, name}` notation |

### Anti-Patterns Found

| File | Pattern | Severity | Assessment |
|------|---------|----------|------------|
| `tests/test_models.py:734` | `tag.parent is None` | Info | Correct — `Tag.parent` is nullable (`TagRef | None`); assertion tests top-level tag with no parent |
| `tests/test_models.py:772` | `folder.parent is None` | Info | Correct — `Folder.parent` is nullable (`FolderRef | None`); assertion tests top-level folder |
| `tests/test_service_payload.py:37` | `payload.parent is None` | Info | Correct — this is a service payload `parent` field (write-side), not Task model |

No blockers or warnings found. All `None` checks are on legitimately nullable fields.

### Human Verification Required

None — all success criteria are verifiable programmatically. The test suite (1598 tests, 98% coverage) covers the full read path including schema validation and cross-path equivalence.

### Gaps Summary

No gaps. All 12 roadmap success criteria verified. All 14 requirement IDs from the plan frontmatter (MODL-04 through MODL-08, READ-01 through READ-07, DESC-01, DESC-02) are satisfied with concrete evidence. The test suite is fully green (1598 tests passed).

**Note on SC #5 wording:** The roadmap states "ParentRef model is removed from the codebase" but REQUIREMENTS.md (MODL-08) and the plan clarify this means the *old* `ParentRef(type, id, name)` shape is removed. The implementation kept the `ParentRef` name for the new tagged wrapper — this is the correct interpretation confirmed by all three plan documents.

---

_Verified: 2026-04-06T20:30:00Z_
_Verifier: Claude (gsd-verifier)_
