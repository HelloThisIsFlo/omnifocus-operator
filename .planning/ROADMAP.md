# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-16)
- 🚧 **v1.2.1 Architectural Cleanup** — Phases 18-24 (in progress)

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

### v1.2.1 Architectural Cleanup (Phases 18-27)

- [x] **Phase 18: Write Model Strictness** - Write specs reject unknown fields; sentinel interaction validated (completed 2026-03-16)
- [x] **Phase 19: InMemoryBridge Export Cleanup** - Test double removed from production exports (completed 2026-03-17)
- [x] **Phase 20: Model Taxonomy** - Three-layer naming convention with typed bridge payloads (completed 2026-03-18)
- [x] **Phase 21: Write Pipeline Unification** - Symmetric add/edit signatures at service-repository boundary (completed 2026-03-19)
- [x] **Phase 22: Service Decomposition** - service.py becomes service/ package; all logic extracted to dedicated modules (gap closure in progress) (completed 2026-03-20)
- [x] **Phase 23: SimulatorBridge and Factory Cleanup** - SimulatorBridge removed from exports; bridge factory eliminated; PYTEST guard moved to RealBridge (completed 2026-03-20)
- [x] **Phase 24: Test Double Relocation** - All test double modules moved from src/ to tests/; production code structurally cannot import them (completed 2026-03-20)
- [x] **Phase 25: Patch/PatchOrClear type aliases for command models** - `Patch[T]`/`PatchOrClear[T]` aliases + `changed_fields()` helper (TYPE-01--04) (completed 2026-03-20)
- [x] **Phase 26: Replace InMemoryRepository with stateful InMemoryBridge** - Stateful InMemoryBridge, delete InMemoryRepository, real serialization path in tests (INFRA-10--12) (gap closure in progress) (completed 2026-03-21)
- [x] **Phase 27: Bridge contract tests (golden master)** - Golden master from RealBridge UAT, CI contract tests verify InMemoryBridge matches (INFRA-13--14) (gap closure in progress) (completed 2026-03-22)

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
**Plans:** 1/1 plans complete
Plans:
- [ ] 19-01-PLAN.md -- Remove test doubles from exports, migrate test imports, update factory

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
**Plans:** 2/2 plans complete
Plans:
- [ ] 20-01-PLAN.md -- Create contracts/ package with new model definitions and consolidated protocols
- [ ] 20-02-PLAN.md -- Migrate all source and test imports, typed repo signatures, delete old files

### Phase 21: Write Pipeline Unification
**Goal**: add_task and edit_task follow the same structural pattern at every layer boundary
**Depends on**: Phase 20 (typed payloads must exist before unifying the pipeline around them)
**Requirements**: PIPE-01, PIPE-02
**Success Criteria** (what must be TRUE):
  1. Repository protocol defines add_task and edit_task with symmetric signatures (same parameter and return types)
  2. Both write paths construct bridge payloads using the same pattern (no split between repo model_dump vs service dict-building)
  3. All three repository implementations (Hybrid, Bridge, InMemory) conform to the unified protocol
  4. All 534+ existing tests pass without behavioral changes
**Plans:** 2/2 plans complete
Plans:
- [ ] 21-01-PLAN.md -- Service-side payload construction convergence (kwargs dict pattern for add_task, snake_case elimination of camelCase roundtrip for edit_task)
- [ ] 21-02-PLAN.md -- BridgeWriteMixin extraction, exclude_unset standardization, explicit protocol conformance

### Phase 22: Service Decomposition
**Goal**: service.py is converted to a service/ package with all logic extracted to dedicated, independently testable modules; orchestrator is pure orchestration
**Depends on**: Phase 21 (unified pipeline makes payload-building logic unambiguous to extract)
**Requirements**: SVCR-01, SVCR-02, SVCR-03, SVCR-04, SVCR-05
**Success Criteria** (what must be TRUE):
  1. `service/` is a Python package; `from omnifocus_operator.service import OperatorService` still works
  2. Format conversion functions (build_add_payload, build_edit_payload) live in a dedicated module, not in the orchestrator
  3. Validation logic (name checks) lives in a dedicated module, separate from resolution
  4. Domain logic (tag diff, repetition rule semantics, lifecycle, no-op detection) lives in a dedicated module
  5. Each extracted module can be imported and tested without instantiating OperatorService
  6. The orchestrator reads as a short sequence of validate, resolve, domain, convert, delegate steps per write method
  7. All entity existence checks route through Resolver
  8. Null-means-clear intent normalization is centralized in DomainLogic
  9. All 579+ existing tests pass without modification
**Plans:** 4/4 plans complete
Plans:
- [x] 22-01-PLAN.md -- Create service/ package, extract resolve.py, domain.py, payload.py; rewrite service.py as thin orchestrator
- [x] 22-02-PLAN.md -- Unit tests for extracted modules (test_service_resolve.py, test_service_domain.py, test_service_payload.py)
- [x] 22-03-PLAN.md -- Split validate.py from resolve.py, add resolve_task to Resolver, route all entity checks through Resolver
- [x] 22-04-PLAN.md -- Centralize null-means-clear intent normalization in DomainLogic

### Phase 23: SimulatorBridge and Factory Cleanup
**Goal**: SimulatorBridge removed from production exports and bridge factory eliminated — repository factory creates RealBridge directly, PYTEST safety guard lives in RealBridge.__init__
**Depends on**: Phase 19 (InMemoryBridge cleanup removes "inmemory", leaving "simulator" + "real" in factory)
**Requirements**: INFRA-04, INFRA-05, INFRA-06, INFRA-07
**Success Criteria** (what must be TRUE):
  1. `from omnifocus_operator.bridge import SimulatorBridge` raises ImportError
  2. All tests that use SimulatorBridge import it via the direct module path (`bridge.simulator`)
  3. `OMNIFOCUS_BRIDGE` env var is not read anywhere in production code
  4. `create_bridge()` function and `bridge/factory.py` module removed — repository factory instantiates RealBridge directly
  5. PYTEST safety guard (`PYTEST_CURRENT_TEST` check) lives in `RealBridge.__init__` — blocks instantiation during automated testing regardless of call site
  6. All 534+ existing tests pass after migration
**Plans:** 1/1 plans complete
Plans:
- [x] 23-01-PLAN.md -- PYTEST guard migration to RealBridge, bridge factory deletion, export cleanup, repository factory simplification, test migration

## Progress

**Execution Order:**
Phases execute in numeric order: 18 -> 19 -> 20 -> 21 -> 22 -> 23 -> 24 -> 25 -> 26 -> 27
(Phases 18 and 19 are independent and could execute in either order. Phase 23 depends on Phase 19. Phase 24 depends on Phase 23. Phases 25-27 are sequential.)

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
| 19. InMemoryBridge Export Cleanup | 1/1 | Complete    | 2026-03-17 | - |
| 20. Model Taxonomy | 2/2 | Complete    | 2026-03-18 | - |
| 21. Write Pipeline Unification | 2/2 | Complete    | 2026-03-19 | - |
| 22. Service Decomposition | 4/4 | Complete    | 2026-03-20 | - |
| 23. SimulatorBridge and Factory Cleanup | v1.2.1 | 1/1 | Complete    | 2026-03-20 |
| 24. Test Double Relocation | v1.2.1 | 1/1 | Complete    | 2026-03-20 |

### Phase 24: Test Double Relocation
**Goal**: All test double modules physically moved from `src/` to `tests/` — production code structurally cannot import test doubles
**Depends on**: Phase 23 (SimulatorBridge export + factory cleanup must be complete so all test doubles are already decoupled from production imports)
**Requirements**: INFRA-08, INFRA-09
**Success Criteria** (what must be TRUE):
  1. No test double modules exist under `src/omnifocus_operator/` (InMemoryBridge, BridgeCall, InMemoryRepository, ConstantMtimeSource, SimulatorBridge)
  2. All test double modules live under `tests/` (e.g., `tests/doubles/` or similar)
  3. No file in `src/` imports from the test doubles location
  4. All test files import test doubles from their new `tests/` location
  5. All 534+ existing tests pass after relocation
**Plans:** 1/1 plans complete
Plans:
- [x] 24-01-PLAN.md -- Create tests/doubles/ package, relocate all test doubles, migrate imports, negative import tests

### Phase 25: Patch/PatchOrClear type aliases for command models
**Goal**: Command model field annotations use `Patch[T]` and `PatchOrClear[T]` type aliases to make patch semantics self-documenting — pure readability change with identical JSON schema output
**Depends on**: Phase 24
**Requirements**: TYPE-01, TYPE-02, TYPE-03, TYPE-04
**Success Criteria** (what must be TRUE):
  1. All patchable command model fields use `Patch[T]` annotation instead of raw `T | _Unset`
  2. All clearable command model fields use `PatchOrClear[T]` annotation instead of raw `T | None | _Unset`
  3. JSON schema output is identical before and after the migration
  4. `changed_fields()` on any `CommandModel` instance returns a dict of only explicitly set fields (UNSET values excluded)
  5. All existing tests pass without modification
**Plans:** 1/1 plans complete

Plans:
- [x] 25-01-PLAN.md -- Define Patch/PatchOrClear/PatchOrNone aliases, changed_fields(), migrate all annotations, schema identity tests

### Phase 26: Replace InMemoryRepository with stateful InMemoryBridge
**Goal**: InMemoryRepository deleted and replaced by a stateful InMemoryBridge — write tests exercise the real serialization path instead of an independent simulation that can drift
**Depends on**: Phase 25
**Requirements**: INFRA-10, INFRA-11, INFRA-12
**Success Criteria** (what must be TRUE):
  1. `InMemoryBridge` maintains mutable task/project/tag state and handles `add_task`/`edit_task` bridge commands
  2. `InMemoryRepository` module is deleted — no repository test double simulates write behavior independently of the bridge layer
  3. Write tests exercise `BridgeWriteMixin`, `model_dump(by_alias=True)`, and snapshot parsing through the stateful `InMemoryBridge`
  4. All existing tests pass without behavioral changes
**Plans:** 5/5 plans complete

Plans:
- [x] 26-01-PLAN.md -- Rewrite InMemoryBridge to stateful with add_task/edit_task command handlers
- [x] 26-02-PLAN.md -- Migrate all test files from InMemoryRepository to BridgeRepository, delete InMemoryRepository
- [x] 26-03-PLAN.md -- Split StubBridge from InMemoryBridge (gap closure: UAT Test 2)
- [x] 26-04-PLAN.md -- Snapshot marker infrastructure + TestOperatorService/TestAddTask fixture refactor (gap closure: UAT Test 4)
- [x] 26-05-PLAN.md -- TestEditTask fixture refactor (gap closure: UAT Test 4)

### Phase 27: Bridge contract tests (golden master)
**Goal**: Golden master pattern proves behavioral equivalence between InMemoryBridge and RealBridge — UAT captures expected bridge behavior, CI verifies the test double matches
**Depends on**: Phase 26
**Requirements**: INFRA-13, INFRA-14
**Success Criteria** (what must be TRUE):
  1. Golden master of expected bridge behavior exists, captured from RealBridge via UAT
  2. Golden master is committed to the repo as the source of truth for "what OmniFocus actually does"
  3. CI contract tests verify InMemoryBridge output matches the committed golden master
  4. All existing tests pass
**Plans:** 4/4 plans complete

Plans:
- [x] 27-01-PLAN.md -- Fix InMemoryBridge behavioral gaps (parent/tag resolution) + golden master normalization infrastructure
- [x] 27-02-PLAN.md -- Capture script (UAT), CI contract tests, human-verify checkpoint
- [x] 27-03-PLAN.md -- Make InMemoryBridge return raw bridge format + fix service regression (gap closure)
- [x] 27-04-PLAN.md -- Update golden master infrastructure for raw format + re-capture (gap closure)

### Phase 28: Expand golden master coverage and normalize lifecycle date fields

**Goal:** [To be planned]
**Requirements**: TBD
**Depends on:** Phase 27
**Plans:** 0 plans

Plans:
- [ ] TBD (run /gsd:plan-phase 28 to break down)
