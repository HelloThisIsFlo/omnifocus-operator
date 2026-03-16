# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-16)
- 🚧 **v1.2.1 Architectural Cleanup** — Phases 18-22 (in progress)

## Phases

<details>
<summary>✅ v1.0 Foundation (Phases 1-9) — SHIPPED 2026-03-07</summary>

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
<summary>✅ v1.1 HUGE Performance Upgrade (Phases 10-13) — SHIPPED 2026-03-07</summary>

- [x] Phase 10: Model Overhaul (4/4 plans) — completed 2026-03-07
- [x] Phase 11: DataSource Protocol (3/3 plans) — completed 2026-03-07
- [x] Phase 12: SQLite Reader (2/2 plans) — completed 2026-03-07
- [x] Phase 13: Fallback and Integration (2/2 plans) — completed 2026-03-07

</details>

<details>
<summary>✅ v1.2 Writes & Lookups (Phases 14-17) — SHIPPED 2026-03-16</summary>

- [x] Phase 14: Model Refactor & Lookups (2/2 plans) — completed 2026-03-07
- [x] Phase 15: Write Pipeline & Task Creation (4/4 plans) — completed 2026-03-08
- [x] Phase 16: Task Editing (6/6 plans) — completed 2026-03-09
- [x] Phase 16.1: Actions Grouping (3/3 plans) — completed 2026-03-09
- [x] Phase 16.2: Bridge Tag Simplification (3/3 plans) — completed 2026-03-10
- [x] Phase 17: Task Lifecycle (3/3 plans) — completed 2026-03-12

</details>

### 🚧 v1.2.1 Architectural Cleanup (Phases 18-22)

- [x] **Phase 18: Write Model Strictness** - Write specs reject unknown fields; sentinel interaction validated (completed 2026-03-16)
- [ ] **Phase 19: InMemoryBridge Export Cleanup** - Test double removed from production exports
- [ ] **Phase 20: Model Taxonomy** - Three-layer naming convention with typed bridge payloads
- [ ] **Phase 21: Write Pipeline Unification** - Symmetric add/edit signatures at service-repository boundary
- [ ] **Phase 22: Service Decomposition** - service.py becomes service/ package; all logic extracted to dedicated modules

## Phase Details

### Phase 18: Write Model Strictness
**Goal**: Write models catch agent mistakes at validation time instead of silently discarding unknown fields
**Depends on**: Nothing (independent of all other v1.2.1 work)
**Requirements**: STRCT-01, STRCT-02, STRCT-03
**Success Criteria** (what must be TRUE):
  1. Constructing a write model (TaskCreateSpec, TaskEditSpec, etc.) with an unrecognized field raises a Pydantic ValidationError containing the field name
  2. Read models (Task, Project, Tag) continue accepting unknown fields without error
  3. TaskEditSpec with _Unset sentinel defaults validates and round-trips correctly under extra="forbid"
  4. All 534+ existing tests pass without modification
**Plans:** 2/2 plans complete
Plans:
- [ ] 18-01-PLAN.md -- WriteModel base class, re-parent write specs, server error handler, strictness tests
- [ ] 18-02-PLAN.md -- Warning string consolidation into warnings.py

### Phase 19: InMemoryBridge Export Cleanup
**Goal**: Test doubles are not importable from production package paths
**Depends on**: Nothing (independent of all other v1.2.1 work)
**Requirements**: INFRA-01, INFRA-02, INFRA-03
**Success Criteria** (what must be TRUE):
  1. `from omnifocus_operator.bridge import InMemoryBridge` raises ImportError
  2. All tests that use InMemoryBridge import it via the direct module path (`bridge.in_memory`)
  3. Bridge/repository factory functions have no "inmemory" option -- test code instantiates the bridge directly
  4. All 534+ existing tests pass after import path migration
**Plans**: TBD

### Phase 20: Model Taxonomy
**Goal**: Write-side models follow a consistent three-layer naming convention (Request / Domain / Payload) with typed bridge payloads replacing dict[str, Any]
**Depends on**: Phase 18 (strictness config must be settled before renaming models)
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04
**Success Criteria** (what must be TRUE):
  1. Every write-side model class name indicates which layer it belongs to (request models, domain models, and payload models are distinguishable by name alone)
  2. Sub-models (RepetitionRuleSpec, MoveToSpec, TagActionSpec, etc.) are renamed to indicate their layer
  3. Typed Pydantic models exist for bridge payloads, replacing raw dict[str, Any] at the service-repository boundary
  4. All existing import paths that changed have backward-compatible aliases or all call sites are updated
  5. All 534+ existing tests pass without modification to assertions (only import paths may change)
**Plans**: TBD

### Phase 21: Write Pipeline Unification
**Goal**: add_task and edit_task follow the same structural pattern at every layer boundary
**Depends on**: Phase 20 (typed payloads must exist before unifying the pipeline around them)
**Requirements**: PIPE-01, PIPE-02
**Success Criteria** (what must be TRUE):
  1. Repository protocol defines add_task and edit_task with symmetric signatures (same parameter and return types)
  2. Both write paths construct bridge payloads using the same pattern (no split between repo model_dump vs service dict-building)
  3. All three repository implementations (Hybrid, Bridge, InMemory) conform to the unified protocol
  4. All 534+ existing tests pass without behavioral changes
**Plans**: TBD

### Phase 22: Service Decomposition
**Goal**: service.py is converted to a service/ package with all logic extracted to dedicated, independently testable modules; orchestrator is pure orchestration
**Depends on**: Phase 21 (unified pipeline makes payload-building logic unambiguous to extract)
**Requirements**: SVCR-01, SVCR-02, SVCR-03, SVCR-04, SVCR-05
**Success Criteria** (what must be TRUE):
  1. `service/` is a Python package; `from omnifocus_operator.service import OperatorService` still works
  2. Format conversion functions (build_add_payload, build_edit_payload) live in a dedicated module, not in the orchestrator
  3. Validation logic (name checks, parent resolution, tag resolution) lives in a dedicated module
  4. Domain logic (tag diff, repetition rule semantics, lifecycle, no-op detection) lives in a dedicated module
  5. Each extracted module can be imported and tested without instantiating OperatorService
  6. The orchestrator reads as a short sequence of validate, domain, convert, delegate steps per write method
  7. All 534+ existing tests pass without modification
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 18 -> 19 -> 20 -> 21 -> 22
(Phases 18 and 19 are independent and could execute in either order.)

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
| 14. Model Refactor & Lookups | v1.2 | 2/2 | Complete | 2026-03-07 |
| 15. Write Pipeline & Task Creation | v1.2 | 4/4 | Complete | 2026-03-08 |
| 16. Task Editing | v1.2 | 6/6 | Complete | 2026-03-09 |
| 16.1. Actions Grouping | v1.2 | 3/3 | Complete | 2026-03-09 |
| 16.2. Bridge Tag Simplification | v1.2 | 3/3 | Complete | 2026-03-10 |
| 17. Task Lifecycle | v1.2 | 3/3 | Complete | 2026-03-12 |
| 18. Write Model Strictness | 2/2 | Complete    | 2026-03-16 | - |
| 19. InMemoryBridge Export Cleanup | v1.2.1 | 0/TBD | Not started | - |
| 20. Model Taxonomy | v1.2.1 | 0/TBD | Not started | - |
| 21. Write Pipeline Unification | v1.2.1 | 0/TBD | Not started | - |
| 22. Service Decomposition | v1.2.1 | 0/TBD | Not started | - |
