# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-16)
- ✅ **v1.2.1 Architectural Cleanup** — Phases 18-28 (shipped 2026-03-23)
- ✅ **v1.2.2 FastMCP v3 Migration** — Phases 29-31 (shipped 2026-03-26)
- ✅ **v1.2.3 Repetition Rule Write Support** — Phases 32-33.1 (shipped 2026-03-29)
- 🚧 **v1.3 Read Tools** — Phases 34-38 (in progress)

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

<details>
<summary>✅ v1.2.1 Architectural Cleanup (Phases 18-28) — SHIPPED 2026-03-23</summary>

- [x] Phase 18: Write Model Strictness (2/2 plans) — completed 2026-03-16
- [x] Phase 19: InMemoryBridge Export Cleanup (1/1 plans) — completed 2026-03-17
- [x] Phase 20: Model Taxonomy (2/2 plans) — completed 2026-03-18
- [x] Phase 21: Write Pipeline Unification (2/2 plans) — completed 2026-03-19
- [x] Phase 22: Service Decomposition (4/4 plans) — completed 2026-03-20
- [x] Phase 23: SimulatorBridge and Factory Cleanup (1/1 plans) — completed 2026-03-20
- [x] Phase 24: Test Double Relocation (1/1 plans) — completed 2026-03-20
- [x] Phase 25: Patch/PatchOrClear Type Aliases (1/1 plans) — completed 2026-03-20
- [x] Phase 26: Replace InMemoryRepository (5/5 plans) — completed 2026-03-21
- [x] Phase 27: Bridge Contract Tests (4/4 plans) — completed 2026-03-22
- [x] Phase 28: Golden Master Expansion (4/4 plans) — completed 2026-03-23

</details>

<details>
<summary>✅ v1.2.2 FastMCP v3 Migration (Phases 29-31) — SHIPPED 2026-03-26</summary>

- [x] Phase 29: Dependency Swap & Imports (2/2 plans) — completed 2026-03-26
- [x] Phase 30: Test Client Migration (2/2 plans) — completed 2026-03-26
- [x] Phase 31: Middleware & Logging (2/2 plans) — completed 2026-03-26

</details>

<details>
<summary>✅ v1.2.3 Repetition Rule Write Support (Phases 32-33.1) — SHIPPED 2026-03-29</summary>

- [x] Phase 32: Read Model Rewrite (2/2 plans) — completed 2026-03-28
- [x] Phase 32.1: Output Schema Validation Gap (3/3 plans) — completed 2026-03-28
- [x] Phase 33: Write Model, Validation & Bridge (5/5 plans) — completed 2026-03-28
- [x] Phase 33.1: Flat Frequency Refactor (5/5 plans) — completed 2026-03-29

</details>

### v1.3 Read Tools (In Progress)

**Milestone Goal:** Give agents the ability to query, filter, browse, and count OmniFocus entities — tasks, projects, tags, folders, and perspectives.

- [x] **Phase 34: Contracts and Query Foundation** — Typed query models, ListResult container, query builder, protocol extensions (completed 2026-03-29)
- [x] **Phase 35: SQL Repository** — HybridRepository list methods with filtered SQL queries for all 5 entity types (completed 2026-03-30)
- [ ] **Phase 36: In-Memory Fallback** — BridgeRepository list methods with filter.py predicates mirroring SQL semantics
- [ ] **Phase 37: Service Orchestration** — List pipelines with shorthand expansion, default exclusions, validation, "did you mean?" suggestions
- [ ] **Phase 38: Server Registration and Integration** — 5 new MCP tools wired end-to-end with cross-path equivalence validation

## Phase Details

### Phase 34: Contracts and Query Foundation
**Goal**: Typed query contracts and SQL generation exist as independently testable pure functions
**Depends on**: Phase 33.1 (v1.2.3 complete)
**Requirements**: INFRA-01, INFRA-04
**Success Criteria** (what must be TRUE):
  1. ListTasksQuery and ListProjectsQuery models accept all specified filter fields and reject unknown fields
  2. ListTagsQuery and ListFoldersQuery models accept a status list with OR semantics and default to remaining
  3. ListResult[T] includes items list and total_count integer, and serializes correctly via FastMCP (test_output_schema passes)
  4. query_builder pure functions produce parameterized SQL strings (no string interpolation of user values) for task and project queries
  5. Repository and Service protocols declare list method signatures that downstream phases implement
**Plans:** 2/2 plans complete
Plans:
- [ ] 34-01-PLAN.md — Query contracts, ListResult[T], protocol extensions
- [ ] 34-02-PLAN.md — Parameterized SQL query builder (TDD)

### Phase 35: SQL Repository
**Goal**: Agents can retrieve filtered entity lists via the SQL read path with sub-46ms performance
**Depends on**: Phase 34
**Requirements**: TASK-01, TASK-02, TASK-03, TASK-04, TASK-05, TASK-06, TASK-07, TASK-08, TASK-09, TASK-10, TASK-11, PROJ-01, PROJ-02, PROJ-03, PROJ-04, PROJ-05, PROJ-06, PROJ-07, BROWSE-01, BROWSE-02, BROWSE-03, INFRA-02
**Success Criteria** (what must be TRUE):
  1. HybridRepository.list_tasks returns tasks matching any single filter (inbox, flagged, project, tags, has_children, estimated_minutes_max, availability, search) and excludes completed/dropped by default
  2. HybridRepository.list_projects returns projects matching status/folder/review_due_within/flagged filters and defaults to remaining
  3. HybridRepository.list_tags and list_folders return entities filtered by status list with OR logic, defaulting to remaining
  4. HybridRepository.list_perspectives returns all perspectives (built-in + custom) with id, name, and builtin flag
  5. Filtered SQL queries execute measurably faster than full snapshot load
**Plans:** 2/2 plans complete
Plans:
- [x] 35-01-PLAN.md — list_tasks + list_projects with query builder, lookups, pagination
- [x] 35-02-PLAN.md — list_tags + list_folders + list_perspectives with fetch-all + Python filter

### Phase 36: In-Memory Fallback
**Goal**: BridgeRepository produces identical filtered results to the SQL path for every filter combination
**Depends on**: Phase 35
**Requirements**: INFRA-03
**Success Criteria** (what must be TRUE):
  1. BridgeRepository implements the same list methods as HybridRepository using in-memory predicates
  2. Each predicate in filter.py mirrors its SQL counterpart (same case semantics, NULL handling, OR/AND logic)
  3. Cross-path equivalence tests confirm SQL and in-memory paths return identical results for the same query inputs
**Plans**: TBD

### Phase 37: Service Orchestration
**Goal**: Service layer resolves agent-friendly inputs into concrete repository queries with validation and defaults
**Depends on**: Phase 36
**Requirements**: INFRA-06, INFRA-07
**Success Criteria** (what must be TRUE):
  1. _ListTasksPipeline applies default completed/dropped exclusion and validates offset-requires-limit
  2. _ListProjectsPipeline expands status shorthands (remaining, available, all), parses review_due_within durations, and validates inputs
  3. Simple list pass-throughs (tags, folders, perspectives) forward query models to the repository without unnecessary pipeline overhead
  4. Invalid filter values produce educational error messages that tell the agent what went wrong and what valid values look like
  5. When a name-based filter (project, folder, tags) returns zero results, the service emits a "did you mean?" warning with close matches (using difflib or similar) by fetching the full entity list and computing similarity
**Plans**: TBD

### Phase 38: Server Registration and Integration
**Goal**: Agents can call 5 new MCP tools that return filtered, paginated entity lists with total counts
**Depends on**: Phase 37
**Requirements**: INFRA-05
**Success Criteria** (what must be TRUE):
  1. list_tasks, list_projects, list_tags, list_folders, list_perspectives are registered as MCP tools and callable via Client
  2. Tool descriptions enumerate all valid filter values and include enough context for an LLM to call correctly without external docs
  3. Paginated responses include total_count reflecting total matches (not just the page size)
  4. End-to-end integration tests confirm the full path from MCP tool call through service to repository and back
**Plans**: TBD

## Progress

**Execution Order:**
Phases execute in numeric order: 34 → 35 → 36 → 37 → 38

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 22/23 | Complete | 2026-03-07 |
| 10-13 | v1.1 | 11/11 | Complete | 2026-03-07 |
| 14-17 | v1.2 | 21/21 | Complete | 2026-03-16 |
| 18-28 | v1.2.1 | 27/27 | Complete | 2026-03-23 |
| 29-31 | v1.2.2 | 6/6 | Complete | 2026-03-26 |
| 32-33.1 | v1.2.3 | 15/15 | Complete | 2026-03-29 |
| 34. Contracts and Query Foundation | v1.3 | 0/2 | Complete    | 2026-03-29 |
| 35. SQL Repository | v1.3 | 2/2 | Complete    | 2026-03-30 |
| 36. In-Memory Fallback | v1.3 | 0/0 | Not started | - |
| 37. Service Orchestration | v1.3 | 0/0 | Not started | - |
| 38. Server Registration and Integration | v1.3 | 0/0 | Not started | - |
