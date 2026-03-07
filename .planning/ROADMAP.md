# Roadmap: OmniFocus Operator

## Milestones

- v1.0 Foundation -- Phases 1-9 (shipped 2026-03-07)
- v1.1 HUGE Performance Upgrade -- Phases 10-13 (in progress)

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

### v1.1 HUGE Performance Upgrade (In Progress)

**Milestone Goal:** Replace OmniJS bridge read path with direct SQLite cache access for dramatically faster, more accurate data retrieval. Introduces two-axis status model (Urgency + Availability) replacing single-winner enums.

**Phase Numbering:**
- Integer phases (10, 11, 12, 13): Planned milestone work
- Decimal phases (e.g., 10.1): Urgent insertions (marked with INSERTED)

- [x] **Phase 10: Model Overhaul** - Replace single-winner status enums with two-axis model, remove deprecated fields, update all tests (gap closure in progress) (completed 2026-03-07)
- [x] **Phase 11: DataSource Protocol** - Abstract read path behind Repository protocol, refactor Repository into package, create test infrastructure (completed 2026-03-07)
- [x] **Phase 12: SQLite Reader** - Implement HybridRepository with read-only SQLite access, row-to-model mapping, and WAL-based freshness detection (completed 2026-03-07)
- [ ] **Phase 13: Fallback and Integration** - Bridge fallback mode via env var, error-serving when SQLite unavailable, server wiring

## Phase Details

### Phase 10: Model Overhaul
**Goal**: All Pydantic models reflect the two-axis status contract (Urgency + Availability) and deprecated fields are removed
**Depends on**: Nothing (first phase of v1.1; builds on shipped v1.0)
**Requirements**: MODEL-01, MODEL-02, MODEL-03, MODEL-04, MODEL-05, MODEL-06
**Success Criteria** (what must be TRUE):
  1. Task and Project entities expose `urgency` (overdue/due_soon/none) and `availability` (available/blocked/completed/dropped) fields instead of a single status enum
  2. `TaskStatus` and `ProjectStatus` enums no longer exist in the codebase; `Urgency` and `Availability` enums are used everywhere
  3. Fields `active`, `effective_active`, `completed` (bool), `sequential`, `completed_by_children`, `should_use_floating_time_zone`, `contains_singleton_actions`, and `allows_next_action` are removed from their respective models
  4. All existing tests pass with the new model shape (no test left referencing removed fields or old enums)
**Plans**: 4 plans

Plans:
- [x] 10-01-PLAN.md -- Add Urgency/Availability enums and bridge adapter module
- [x] 10-02-PLAN.md -- Migrate all models to two-axis status, update tests and factories
- [x] 10-03-PLAN.md -- Wire adapter into repository, clean up bridge.js, create UAT script
- [ ] 10-04-PLAN.md -- GAP CLOSURE: Remove dead effectiveCompletionDate from Project, remove ScheduleType.none, unify Tag/Folder availability

### Phase 11: DataSource Protocol
**Goal**: Repository layer consumes a Repository protocol instead of being a single concrete class, with BridgeRepository and InMemoryRepository implementations
**Depends on**: Phase 10
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. A `Repository` protocol exists with `get_all()` method returning `AllEntities`, and both BridgeRepository and InMemoryRepository satisfy it
  2. Service layer accepts `Repository` protocol instead of concrete `OmniFocusRepository`
  3. An `InMemoryRepository` exists and all repository-level and service-level tests use it (no direct Bridge dependency in repository/service tests)
**Plans**: 3 plans

Plans:
- [x] 11-01-PLAN.md -- Create repository package with protocol, BridgeRepository, InMemoryRepository, relocate MtimeSource
- [x] 11-02-PLAN.md -- Update consumers (service, server, tests), create architecture doc
- [ ] 11-03-PLAN.md -- GAP CLOSURE: Rename DatabaseSnapshot to AllEntities and get_snapshot() to get_all()

### Phase 12: SQLite Reader
**Goal**: Server reads OmniFocus data directly from SQLite cache with WAL-based freshness detection, no OmniFocus process required
**Depends on**: Phase 11
**Requirements**: SQLITE-01, SQLITE-02, SQLITE-03, SQLITE-04, FRESH-01, FRESH-02
**Success Criteria** (what must be TRUE):
  1. Full OmniFocus snapshot loads from SQLite cache in ~46ms with correct two-axis status (urgency + availability) on every entity
  2. SQLite connections use read-only mode (`?mode=ro`) and a fresh connection is created per read (no stale WAL reads)
  3. Server returns valid data when OmniFocus is not running
  4. After a bridge write, the server detects WAL file mtime change and waits for fresh data before responding (poll every 50ms, 2s timeout)
  5. When WAL file does not exist, freshness falls back to main `.db` file mtime
**Plans**: 2 plans

Plans:
- [ ] 12-01-PLAN.md -- HybridRepository core: SQLite queries, row-to-model mapping, test fixtures
- [ ] 12-02-PLAN.md -- WAL-based freshness detection, repository wiring, UAT script

### Phase 13: Fallback and Integration
**Goal**: OmniJS bridge remains available as a manual fallback, and server enters error-serving mode when SQLite is unavailable
**Depends on**: Phase 12
**Requirements**: FALL-01, FALL-02, FALL-03
**Success Criteria** (what must be TRUE):
  1. Setting `OMNIFOCUS_REPOSITORY=bridge` env var switches the read path from SQLite to the OmniJS bridge
  2. In OmniJS fallback mode, urgency is fully populated but availability is reduced to available/completed/dropped (no `blocked`)
  3. When SQLite database is not found and no fallback is configured, server enters error-serving mode with an actionable message showing the expected path and instructions to set `OMNIFOCUS_REPOSITORY=bridge`
**Plans**: 2 plans

Plans:
- [ ] 13-01-PLAN.md -- Repository factory, server lifespan restructuring, error-serving for SQLite-not-found
- [ ] 13-02-PLAN.md -- Bridge availability limitation test (FALL-02), configuration docs update

## Progress

**Execution Order:**
Phases execute in numeric order: 10 -> 11 -> 12 -> 13

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
| 10. Model Overhaul | 4/4 | Complete    | 2026-03-07 | - |
| 11. DataSource Protocol | 3/3 | Complete    | 2026-03-07 | - |
| 12. SQLite Reader | 2/2 | Complete    | 2026-03-07 | - |
| 13. Fallback and Integration | v1.1 | 0/2 | Not started | - |
