---
status: complete
phase: 56-task-property-surface
source: [56-VERIFICATION.md]
started: 2026-04-19T22:30:00Z
updated: 2026-04-20T19:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. FLAG-07 behavioral meaning in live MCP client
expected: The `list_tasks` tool description mentions `isSequential: only the next-in-line child is available` and `dependsOnChildren: real task waiting on children` with behavioral meaning — not just field presence. After 56-08: the `list_projects` and `get_project` tool descriptions should also now surface `isSequential` on projects (updated scope — FLAG-04 applies cross-entity).
result: passed
notes: Verified by agent (Claude Code) against the live dev MCP server. Both FLAG-07 phrases present verbatim in the list_tasks tool description reaching the model: "isSequential: only the next-in-line child is available. Agents reasoning about actionability must NOT over-count -- a sequential parent's children are ordered." and "dependsOnChildren: this task is a real unit of work waiting on children, not a container. Treat as a discrete task, not a collapsible grouping." Also confirmed: hierarchy include group lists `parent, hasChildren, type, completesWithChildren` (HIER-01); default fields include all five FLAG-01..05 presence flags. **Post-56-08 re-check (2026-04-20):** live `list_projects` tool schema confirms `isSequential` is in `Default fields (always returned)` and surfaces the behavioral-flag section "isSequential: Only the next-in-line child is available; later children are blocked until earlier ones complete." — `IS_SEQUENTIAL_DESC` no longer prefixes "Tasks-only." `get_project` schema similarly carries `isSequential` in its fields list. Live wire call `list_projects(search: "GM", include: ["*"])` returned 6 projects — `GM-Phase56-SequentialProj` alone carried `isSequential: true` and `type: "sequential"` together (no-suppression invariant on projects, FLAG-06/HIER-04 cross-entity); 5 parallel projects correctly stripped `isSequential`; all three `type` enum values observed (`parallel`, `sequential`, `singleActions`); `completesWithChildren` emitted on all projects (NEVER_STRIP). Task-side no-suppression verified on a freshly-created sequential parent with 2 children in `GM-Phase56-ParallelProj` — parent emitted all five fields together (`isSequential: true`, `dependsOnChildren: true`, `type: "sequential"`, `hasChildren: true`, `completesWithChildren: false`); semantic correctness confirmed via child availability (Child-1 `available`, Child-2 `blocked` — sequential semantic on the wire). Test subtree consolidated under a single inbox task (`🧪 GM-LiveCheck-Cleanup (delete me)`) for manual deletion.

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

### 5. Capture the golden master baseline (GOLD-01 live capture)
expected: `tests/golden_master/snapshots/09-task-property-surface/*.json` committed with normalized raw-bridge fixtures for the 8 Phase 56 scenarios declared in `uat/capture_golden_master.py`. Capture runs against the real Bridge (live OmniFocus) via `uv run python uat/capture_golden_master.py`. Procedure documented in `tests/golden_master/snapshots/README.md`. **Human-only per SAFE-01/02 + CLAUDE.md — agents must NOT run this script.**
result: passed
notes: Human-run capture against live OmniFocus completed 2026-04-20. 8 JSON fixtures committed to `tests/golden_master/snapshots/09-task-property-surface/` in commit `19906902` (the capture also regenerated all pre-existing snapshot folders because the Phase 56 field surface — `isSequential`, `completesWithChildren`, `hasAttachments`, `hasNote` — now projects across every scenario). `test_bridge_contract.py` green at 96 passed. Idempotency verified — partial re-captures (first 7 scenarios) produced identical JSON, so the commit is authoritative.

**Capture-script fixes landed during this UAT cycle (H-01 + two follow-ups):** (a) `_check_leftover_tasks` retry loop now excludes `known_task_ids` in addition to `known_project_ids`, mirroring the initial check — commit `8f3ad11d`. (b) Ctrl+C mid-capture now consolidates created tasks under `🧪 GM-Cleanup (capture ...)` via `except (KeyboardInterrupt, asyncio.CancelledError)` with `current_task().uncancel()` — commit `b1722f9d`. (c) Phase 5 renamed from `_phase_5_consolidation` to `_phase_5_cleanup` and now resets `note=""` on the preserved `GM-Phase56-Attached` task so scenario 04's touch doesn't drift the preserved task's baseline across runs — same commit.

## Summary

total: 5
passed: 5
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

### G1. `isSequential` should also surface on Project (FLAG-04 design correction)

source_test: 1 (FLAG-07 description copy review surfaced this)
status: resolved
resolved_by: 56-08 (Phase 56 gap-closure plan)
resolved_date: 2026-04-20
resolution_notes: `is_sequential` hoisted from `Task` to `ActionableEntity`; `enrich_project_presence_flags` added to `DomainLogic` and wired into `get_all_data`, `get_project`, `_ListProjectsPipeline._delegate`; `PROJECT_DEFAULT_FIELDS` gains `isSequential`; `LIST_PROJECTS_TOOL_DOC` and `GET_PROJECT_TOOL_DOC` surface the field; `IS_SEQUENTIAL_DESC` drops the tasks-only prefix; REQUIREMENTS.md FLAG-04 wording revised. `dependsOnChildren` (FLAG-05) stays tasks-only by explicit design — projects are always containers. Verified by 56-VERIFICATION.md re-run (status: human_needed, 9/9 must-haves).

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
status: resolved
resolved_by: 56-09 (Phase 56 gap-closure plan, scaffolding half) + human UAT capture (pending, tracked as Test 5 pending)
resolved_date: 2026-04-20
resolution_notes: 56-07's wrong-pattern artifacts fully removed — `tests/golden_master/test_task_property_surface_golden.py` deleted, `GOLDEN_MASTER_CAPTURE` env var purged from all source, baseline-file section of README removed. Canonical pattern restored — 8 new scenarios declared in `uat/capture_golden_master.py` targeting `tests/golden_master/snapshots/09-task-property-surface/`, `test_bridge_contract.py` discovers the new subfolder via its existing sorted-iterdir loop, skip-when-absent contract honoured. Audit confirmed no normalize.py changes needed (all Phase 56 raw-bridge fields are deterministic booleans). Capture half legitimately deferred to human UAT per SAFE-01/02 — now tracked as Test 5 (pending) rather than a gap.

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
