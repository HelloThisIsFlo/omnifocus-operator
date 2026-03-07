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

- [ ] **Phase 10: Model Overhaul** - Replace single-winner status enums with two-axis model, remove deprecated fields, update all tests
- [ ] **Phase 11: DataSource Protocol** - Abstract read path behind DataSource protocol, refactor Repository, create test infrastructure
- [ ] **Phase 12: SQLite Reader** - Implement SQLiteDataSource with read-only access, row-to-model mapping, and WAL-based freshness detection
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
**Plans**: TBD

Plans:
- [ ] 10-01: TBD
- [ ] 10-02: TBD

### Phase 11: DataSource Protocol
**Goal**: Repository layer consumes a unified DataSource protocol instead of Bridge + MtimeSource, with InMemoryDataSource for testing
**Depends on**: Phase 10
**Requirements**: ARCH-01, ARCH-02, ARCH-03
**Success Criteria** (what must be TRUE):
  1. A `DataSource` protocol exists with methods for fetching snapshot data and mtime, and both SQLite and Bridge implementations can satisfy it
  2. `OmniFocusRepository` accepts a DataSource instead of Bridge + MtimeSource directly
  3. An `InMemoryDataSource` exists and all repository-level tests use it (no direct Bridge dependency in repository tests)
**Plans**: TBD

Plans:
- [ ] 11-01: TBD

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
**Plans**: TBD

Plans:
- [ ] 12-01: TBD
- [ ] 12-02: TBD

### Phase 13: Fallback and Integration
**Goal**: OmniJS bridge remains available as a manual fallback, and server enters error-serving mode when SQLite is unavailable
**Depends on**: Phase 12
**Requirements**: FALL-01, FALL-02, FALL-03
**Success Criteria** (what must be TRUE):
  1. Setting `OMNIFOCUS_BRIDGE=omnijs` env var switches the read path from SQLite to the OmniJS bridge
  2. In OmniJS fallback mode, urgency is fully populated but availability is reduced to available/completed/dropped (no `blocked`)
  3. When SQLite database is not found and no fallback is configured, server enters error-serving mode with an actionable message showing the expected path and fallback instructions
**Plans**: TBD

Plans:
- [ ] 13-01: TBD

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
| 10. Model Overhaul | v1.1 | 0/? | Not started | - |
| 11. DataSource Protocol | v1.1 | 0/? | Not started | - |
| 12. SQLite Reader | v1.1 | 0/? | Not started | - |
| 13. Fallback and Integration | v1.1 | 0/? | Not started | - |
