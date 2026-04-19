---
status: diagnosed
phase: 56-task-property-surface
source: [56-VERIFICATION.md]
started: 2026-04-19T22:30:00Z
updated: 2026-04-19T23:30:00Z
---

## Current Test

[all items closed; phase has 2 gaps logged below]

## Tests

### 1. FLAG-07 behavioral meaning in live MCP client
expected: The `list_tasks` tool description mentions `isSequential: only the next-in-line child is available` and `dependsOnChildren: real task waiting on children` with behavioral meaning — not just field presence.
result: passed
notes: Verified by agent (Claude Code) against the live dev MCP server. Both FLAG-07 phrases present verbatim in the list_tasks tool description reaching the model: "isSequential: only the next-in-line child is available. Agents reasoning about actionability must NOT over-count -- a sequential parent's children are ordered." and "dependsOnChildren: this task is a real unit of work waiting on children, not a container. Treat as a discrete task, not a collapsible grouping." Also confirmed: hierarchy include group lists `parent, hasChildren, type, completesWithChildren` (HIER-01); default fields include all five FLAG-01..05 presence flags.

### 2. Create-default resolution writes explicit preference value
expected: Adding a task via `add_tasks` while omitting `completesWithChildren` and `type`, then reading it back via `get_task`, returns values matching the user's actual OmniFocus preferences (`OFMCompleteWhenLastItemComplete` / `OFMTaskDefaultSequential`) — NOT OmniFocus's implicit defaults.
result: passed
notes: Tested live against OmniFocus. Control task (explicit `completesWithChildren=false`, `type=sequential`) round-tripped verbatim — write path confirmed end-to-end through `bridge.js:handleAddTask`. Default task (both fields omitted) resolved to `completesWithChildren=true`, `type=parallel`; these match user's observed OmniFocus behavior (auto-complete on child completion, parallel-by-default for new task groups). The underlying OF preferences are not exposed in the OF settings UI on this installation, so disambiguating "server read prefs" vs "server landed on factory defaults" can't be done by toggling — but (a) values are consistent with observed OF behavior, (b) InMemoryBridge-backed tests already prove the service asks preferences before writing, and (c) no regression observed.

### 3. No-suppression invariant via live round-trip
expected: `list_tasks` with `include=['hierarchy']` on a sequential task that has children and does NOT complete with children returns BOTH the default-response derived flags (`isSequential: true`, `dependsOnChildren: true`) AND the hierarchy group fields (`type: 'sequential'`, `hasChildren: true`, `completesWithChildren: false`) independently — both pipelines emit, no de-duplication.
result: passed
notes: Tested live. Created throwaway sequential parent (completesWithChildren=false) with 2 children in Inbox; ran list_tasks with include=['hierarchy'] + search filter. Response contained all 5 expected fields together: isSequential=true, dependsOnChildren=true (default-response derived flags) AND type='sequential', hasChildren=true, completesWithChildren=false (hierarchy group). Confirms FLAG-06 / HIER-04 invariant against the live OF database. Test data dropped after capture.

### 4. `singleActions` rejection error rendering
expected: `add_tasks` with `type='singleActions'` surfaces a generic Pydantic enum error in the live MCP client — not a custom educational message, no mention of "project only".
result: passed
notes: Tested live via Claude Code CLI. add_tasks with type='singleActions' returned the standard Pydantic StrEnum error: `Task 1: str-enum[TaskType]: Input should be 'parallel' or 'sequential'`. No custom message, no "project only" text. Valid values are surfaced in the error itself so the agent can self-correct on retry. No task created — rejection happens before the bridge call.

### 5. Capture the golden master baseline
expected: `tests/golden_master/snapshots/task_property_surface_baseline.json` committed with the normalized serialized output of `list_tasks(include=['hierarchy'])` for a fully-loaded task. Procedure documented in `tests/golden_master/snapshots/README.md`. **Agents must NOT run `GOLDEN_MASTER_CAPTURE=1` — human-only per CLAUDE.md.**
result: issues
notes: 56-07's golden master implementation diverges from the project's established convention. The project pattern (`uat/capture_golden_master.py` running against RealBridge → JSON fixtures in numbered subfolders → replayed against InMemoryBridge by `test_bridge_contract.py`) was bypassed. 56-07 instead built a self-referential InMemoryBridge → InMemoryBridge "baseline" with an env-var capture mode. Self-referential because both capture and comparison run against InMemoryBridge — proves serialization-roundtrip stability, not parity with real OF. Capture procedure as written should NOT be followed; doing so would commit a baseline derived from the wrong source. See gap entry below.

## Summary

total: 5
passed: 4
issues: 1
pending: 0
skipped: 0
blocked: 0

## Gaps

### G1. `isSequential` should also surface on Project (FLAG-04 design correction)

source_test: 1 (FLAG-07 description copy review surfaced this)
status: open

description: FLAG-04 was implemented as tasks-only based on the original requirement text, but the semantic applies equally to projects — a project with `type == 'sequential'` has the same "next-in-line child available" behavior as a sequential parent task. Should be hoisted to `ActionableEntity` (already hosts the other shared presence flags `has_note`, `has_repetition`, `has_attachments`, `completes_with_children`).

work_required:
  - Hoist `is_sequential` to `ActionableEntity` (single field declaration; remove from Task)
  - Add `enrich_project_presence_flags(project)` to `DomainLogic`
  - Wire enrichment into `get_all_data`, `get_project`, `_ListProjectsPipeline._delegate`
  - Add `"isSequential"` to `PROJECT_DEFAULT_FIELDS` in `config.py`
  - Update `IS_SEQUENTIAL_DESC` (drop "Tasks-only." prefix)
  - Update `LIST_PROJECTS_TOOL_DOC` to surface `isSequential` + add a project-only `_PROJECT_BEHAVIORAL_FLAGS_NOTE` fragment
  - Update `REQUIREMENTS.md` FLAG-04 wording (currently says "tasks-only — projects use full type enum via hierarchy include")
  - Test parity vs Task: domain truth-table for project (3 type cases), service integration tests for `get_project`/`list_projects`/`get_all`, model field/default tests, descriptions field-uses-constant test
  - Flip 4 existing negative assertions ("project doesn't have isSequential") to positive
  - Note: `dependsOnChildren` (FLAG-05) stays tasks-only — projects are always containers

prior_attempt: A working implementation was prototyped in this session (12 files, +137/-50 lines, 4 new tests, 2409 total passing) and then reverted to keep Phase 56 close-out clean. The implementation worked end-to-end but was deferred for proper treatment in its own phase/polish work.

### G2. Golden master for task property surface uses wrong pattern

source_test: 5 (golden master capture)
status: open

description: 56-07's `tests/golden_master/test_task_property_surface_golden.py` + `tests/golden_master/snapshots/README.md` + the planned `task_property_surface_baseline.json` capture diverge from the project's established golden master convention. Project pattern: capture against the **real Bridge** (live OmniFocus) via `uat/capture_golden_master.py` → JSON fixtures in numbered subfolders (`01-add/` through `08-repetition/`) → replayed against `InMemoryBridge` by `test_bridge_contract.py` after normalization (VOLATILE / PRESENCE_CHECK / UNCOMPUTED categories per `tests/golden_master/normalize.py`). 56-07 built a self-referential InMemoryBridge-only "baseline" with an env-var capture switch — proves serialization round-trip stability, not parity with real OF, which is the point of golden master.

work_required:
  - Decide fate of 56-07's pattern: delete (cleanest), repurpose as a separately-named "serialization snapshot test" not under golden_master/, or leave dormant
  - Add a new scenario subfolder `tests/golden_master/snapshots/09-task-property-surface/` (or similar) for the new field surface
  - Extend `uat/capture_golden_master.py` with scenarios exercising the new fields:
    - Sequential parent task with children, completesWithChildren=false (covers isSequential, dependsOnChildren, type, hasChildren, completesWithChildren in default + hierarchy)
    - Parent task auto-complete (completesWithChildren=true)
    - Tasks with notes/attachments/repetitions (covers hasNote, hasRepetition, hasAttachments)
    - Mix of project types (parallel, sequential, singleActions) for projects
  - Extend normalization helpers if any new field is volatile
  - Add corresponding scenarios in `test_bridge_contract.py` to discover and replay
  - Capture against live OF (manual UAT)
  - Commit fixtures as part of follow-up work, not Phase 56

note: Plan 56-07 explicitly stated "compare-and-skip-when-missing infrastructure" but built compare-and-skip against an InMemoryBridge baseline rather than against a real-Bridge baseline. The intent was right (defer human capture), the implementation diverged from project convention.
