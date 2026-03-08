# Roadmap: OmniFocus Operator

## Milestones

- v1.0 Foundation -- Phases 1-9 (shipped 2026-03-07)
- v1.1 HUGE Performance Upgrade -- Phases 10-13 (shipped 2026-03-07)
- v1.2 Writes & Lookups -- Phases 14-17 (in progress)

## Phases

<details>
<summary>v1.0 Foundation (Phases 1-9) -- SHIPPED 2026-03-07</summary>

- [x] Phase 1: Project Scaffolding (1/1 plans)
- [x] Phase 2: Data Models (2/2 plans)
- [x] Phase 3: Bridge Protocol and InMemoryBridge (1/1 plans)
- [x] Phase 4: Repository and Snapshot Management (1/1 plans)
- [x] Phase 5: Service Layer and MCP Server (3/3 plans)
- [x] Phase 6: File IPC Engine (3/3 plans)
- [x] Phase 7: SimulatorBridge and Mock Simulator (2/2 plans)
- [x] Phase 8: RealBridge and End-to-End Validation (2/2 plans)
- [x] Phase 8.1: JS Bridge Script and IPC Overhaul (3/4 plans -- 08.1-04 skipped)
- [x] Phase 8.2: Model Alignment with BRIDGE-SPEC (3/3 plans)
- [x] Phase 9: Error-Serving Degraded Mode (1/1 plans)

</details>

<details>
<summary>v1.1 HUGE Performance Upgrade (Phases 10-13) -- SHIPPED 2026-03-07</summary>

- [x] Phase 10: Model Overhaul (4/4 plans) -- completed 2026-03-07
- [x] Phase 11: DataSource Protocol (3/3 plans) -- completed 2026-03-07
- [x] Phase 12: SQLite Reader (2/2 plans) -- completed 2026-03-07
- [x] Phase 13: Fallback and Integration (2/2 plans) -- completed 2026-03-07

</details>

### v1.2 Writes & Lookups (In Progress)

**Milestone Goal:** Enable agents to look up individual entities by ID and create/edit tasks in OmniFocus, validating the write pipeline end-to-end.

- [x] **Phase 14: Model Refactor & Lookups** - Unified parent field, rename list_all to get_all, and get-by-ID tools (completed 2026-03-07)
- [x] **Phase 15: Write Pipeline & Task Creation** - Full write pipeline through bridge with add_tasks tool (completed 2026-03-08)
- [ ] **Phase 16: Task Editing** - Patch semantics, tag modes, and task movement via edit_tasks
- [ ] **Phase 17: Task Lifecycle** - Complete, drop, and reactivate tasks via edit_tasks

## Phase Details

### Phase 14: Model Refactor & Lookups
**Goal**: Agents can inspect individual entities by ID using updated models with a unified parent structure
**Depends on**: Phase 13
**Requirements**: NAME-01, MODL-01, MODL-02, LOOK-01, LOOK-02, LOOK-03, LOOK-04
**Success Criteria** (what must be TRUE):
  1. Agent calling `get_all` (not `list_all`) receives the full database snapshot with tasks showing `parent: { type, id }` or `parent: null` instead of separate project/parent fields
  2. Agent can call `get_task` with an ID and receive the complete Task object including urgency and availability
  3. Agent can call `get_project` or `get_tag` with an ID and receive the complete object
  4. Agent calling any get-by-ID tool with a non-existent ID receives a clear "not found" error message (not a crash or empty response)
**Plans**: 2 plans

Plans:
- [ ] 14-01-PLAN.md -- Model refactor (ParentRef, Task parent field, adapter, repo mapper) + rename list_all to get_all
- [ ] 14-02-PLAN.md -- Get-by-ID tools (get_task, get_project, get_tag) across all layers

### Phase 15: Write Pipeline & Task Creation
**Goal**: Agents can create tasks in OmniFocus through the full write pipeline (MCP -> Service -> Repository -> Bridge -> invalidate snapshot)
**Depends on**: Phase 14
**Requirements**: CREA-01, CREA-02, CREA-03, CREA-04, CREA-05, CREA-06, CREA-07, CREA-08
**Success Criteria** (what must be TRUE):
  1. Agent can call `add_tasks` with just a name and the task appears in OmniFocus inbox
  2. Agent can call `add_tasks` with a parent ID (project or task) and the task appears under that parent -- without the agent specifying whether the ID is a project or task
  3. Agent can set tags, dates, flag, estimated_minutes, and note on creation and they all persist correctly in OmniFocus
  4. After creating a task, the agent's next `get_all` or `get_task` call returns fresh data reflecting the write
  5. Invalid inputs (missing name, non-existent parent, non-existent tags) return clear validation errors before anything is written
**Plans**: 3 plans

Plans:
- [x] 15-01-PLAN.md -- Write models (TaskCreateSpec, TaskCreateResult) + bridge.js add_task handler + snapshot->get_all rename
- [ ] 15-02-PLAN.md -- Repository + service layer (protocol, validation, parent/tag resolution, factory wiring)
- [ ] 15-03-PLAN.md -- MCP add_tasks tool registration + end-to-end integration tests

### Phase 16: Task Editing
**Goal**: Agents can modify existing tasks using patch semantics -- changing fields, managing tags, and moving tasks between parents
**Depends on**: Phase 15
**Requirements**: EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-08, EDIT-09
**Success Criteria** (what must be TRUE):
  1. Agent can call `edit_tasks` omitting fields to leave them unchanged, setting fields to null to clear them, or setting values to update them
  2. Agent can replace all tags, add tags without removing existing, or remove specific tags -- and mixing replace with add/remove is rejected with a clear error
  3. Agent can move a task to a different project, to a different parent task, or to inbox by setting parent to null
  4. After editing a task, the agent's next read call returns the updated data
**Plans**: 3 plans

Plans:
- [ ] 16-01-PLAN.md -- Write models (UNSET sentinel, TaskEditSpec, MoveToSpec, TaskEditResult) + bridge.js handleEditTask
- [ ] 16-02-PLAN.md -- Repository protocol extension + service layer (validation, cycle detection, tag modes, moveTo resolution)
- [ ] 16-03-PLAN.md -- MCP edit_tasks tool registration + end-to-end integration tests

### Phase 17: Task Lifecycle
**Goal**: Agents can change task lifecycle state -- completing, dropping, and reactivating tasks
**Depends on**: Phase 15
**Requirements**: LIFE-01, LIFE-02, LIFE-03, LIFE-04, LIFE-05
**Success Criteria** (what must be TRUE):
  1. Agent can mark a task as complete via `edit_tasks` and the task's availability changes to `completed`
  2. Agent can drop a task via `edit_tasks` and the task's availability changes to `dropped`
  3. Agent can reactivate a completed task via `edit_tasks` and the task becomes available again
  4. Edge cases for repeating tasks and dropped task reactivation are documented and handled with clear errors or documented behavior
**Plans**: TBD

Plans:
- [ ] 17-01: TBD
- [ ] 17-02: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 14 -> 15 -> 16 -> 17
(Phases 16 and 17 both depend on 15 but execute sequentially)

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1. Project Scaffolding | v1.0 | 1/1 | Complete | 2026-03-01 |
| 2. Data Models | v1.0 | 2/2 | Complete | 2026-03-01 |
| 3. Bridge Protocol and InMemoryBridge | v1.0 | 1/1 | Complete | 2026-03-01 |
| 4. Repository and Snapshot Management | v1.0 | 1/1 | Complete | 2026-03-01 |
| 5. Service Layer and MCP Server | v1.0 | 3/3 | Complete | 2026-03-02 |
| 6. File IPC Engine | v1.0 | 3/3 | Complete | 2026-03-03 |
| 7. SimulatorBridge and Mock Simulator | v1.0 | 2/2 | Complete | 2026-03-03 |
| 8. RealBridge and E2E Validation | v1.0 | 2/2 | Complete | 2026-03-04 |
| 8.1. JS Bridge Script and IPC Overhaul | v1.0 | 3/4 | Complete | 2026-03-05 |
| 8.2. Model Alignment (BRIDGE-SPEC) | v1.0 | 3/3 | Complete | 2026-03-06 |
| 9. Error-Serving Degraded Mode | v1.0 | 1/1 | Complete | 2026-03-06 |
| 10. Model Overhaul | v1.1 | 4/4 | Complete | 2026-03-07 |
| 11. DataSource Protocol | v1.1 | 3/3 | Complete | 2026-03-07 |
| 12. SQLite Reader | v1.1 | 2/2 | Complete | 2026-03-07 |
| 13. Fallback and Integration | v1.1 | 2/2 | Complete | 2026-03-07 |
| 14. Model Refactor & Lookups | 2/2 | Complete    | 2026-03-07 | - |
| 15. Write Pipeline & Task Creation | 4/4 | Complete    | 2026-03-08 | - |
| 16. Task Editing | v1.2 | 0/3 | Not started | - |
| 17. Task Lifecycle | v1.2 | 0/? | Not started | - |
