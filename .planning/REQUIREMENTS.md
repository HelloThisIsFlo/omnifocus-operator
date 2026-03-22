# Requirements: OmniFocus Operator

**Defined:** 2026-03-16
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2.1 Requirements

Requirements for Architectural Cleanup milestone. No new tools, no behavioral changes — pure internal quality. All 534+ existing tests must continue passing.

### Write Pipeline

- [x] **PIPE-01**: add_task and edit_task have symmetric signatures at the service-repository boundary
- [x] **PIPE-02**: Both write paths use the same pattern for bridge payload construction (no split between repo model_dump vs service dict-building)

### Model Taxonomy

- [x] **MODL-01**: Three-layer model taxonomy established: Request (user intent), Domain (entities), Payload (bridge format)
- [x] **MODL-02**: Write-side request models renamed to follow consistent convention distinguishing them from domain models
- [x] **MODL-03**: Typed bridge payload models replace `dict[str, Any]` at the service-repository boundary
- [x] **MODL-04**: All write-side sub-models (RepetitionRuleSpec, MoveToSpec, TagActionSpec, etc.) renamed to indicate their layer

### Service Decomposition

- [x] **SVCR-01**: Validation logic extracted to dedicated module
- [x] **SVCR-02**: Domain logic extracted to dedicated module (tag diff, repetition rule semantics)
- [x] **SVCR-03**: Format conversion extracted to dedicated module
- [x] **SVCR-04**: service.py converted to service/ package (preserves all import paths)
- [x] **SVCR-05**: Each extracted module is independently testable

### Model Strictness

- [x] **STRCT-01**: Write models reject unknown fields with clear errors (`extra="forbid"`)
- [x] **STRCT-02**: Read models remain permissive (`extra="ignore"`)
- [x] **STRCT-03**: `_Unset` sentinel works correctly with `extra="forbid"`

### Test Infrastructure

- [x] **INFRA-01**: InMemoryBridge not importable from `omnifocus_operator.bridge`
- [x] **INFRA-02**: Tests import InMemoryBridge via direct module path only
- [x] **INFRA-03**: `"inmemory"` option removed from bridge/repository factory — no env var routing to test doubles
- [x] **INFRA-04**: SimulatorBridge not importable from `omnifocus_operator.bridge`
- [x] **INFRA-05**: Tests import SimulatorBridge via direct module path only
- [x] **INFRA-06**: `OMNIFOCUS_BRIDGE` environment variable removed — repository factory creates RealBridge directly
- [x] **INFRA-07**: Bridge factory (`create_bridge`) removed — env var reading absorbed into repository factory, PYTEST safety guard moved to `RealBridge.__init__`
- [x] **INFRA-08**: All test double modules physically located under `tests/`, not `src/` (InMemoryBridge, BridgeCall, InMemoryRepository, ConstantMtimeSource, SimulatorBridge)
- [x] **INFRA-09**: No production code (`src/`) imports test doubles — crossing the `src/`→`tests/` boundary is structurally impossible
- [x] **INFRA-10**: `InMemoryBridge` maintains mutable in-memory state and handles `add_task`/`edit_task` commands as a stateful test double
- [x] **INFRA-11**: `InMemoryRepository` deleted — write test infrastructure routes through the bridge serialization layer
- [x] **INFRA-12**: Write tests exercise the real serialization path (`BridgeWriteMixin`, `model_dump(by_alias=True)`, snapshot parsing) via the stateful `InMemoryBridge`
- [x] **INFRA-13**: Golden master of expected bridge behavior captured from RealBridge via UAT and committed to the repo
- [x] **INFRA-14**: CI contract tests verify InMemoryBridge output matches the committed golden master

### Type Expressiveness

- [x] **TYPE-01**: Patchable command model fields annotated with `Patch[T]` type alias (`Union[T, _Unset]`) — patch semantics visible in the annotation
- [x] **TYPE-02**: Clearable command model fields annotated with `PatchOrClear[T]` type alias (`Union[T, None, _Unset]`) — `None`-means-clear visible in the annotation
- [x] **TYPE-03**: JSON schema output identical before and after type alias migration
- [x] **TYPE-04**: `changed_fields()` helper on `CommandModel` returns only fields explicitly set by the caller

### Golden Master Coverage

- [ ] **GOLD-01**: Golden master scenarios reorganized into numbered subfolders (`01-add/` through `07-inheritance/`) with ~43 scenarios covering all bridge code paths
- [ ] **GOLD-02**: Capture script rewritten for new folder structure with extended manual prerequisites (3 projects, 2 tags)
- [ ] **GOLD-03**: Contract tests discover and replay scenarios in subfolder sort order without external manifest

### Field Normalization

- [ ] **NORM-01**: `completionDate` and `dropDate` verified via presence-check normalization (null vs `"<set>"` sentinel) instead of stripped as volatile
- [ ] **NORM-02**: `effectiveCompletionDate` and `effectiveDropDate` verified via same presence-check normalization
- [ ] **NORM-03**: `effectiveFlagged`, `effectiveDueDate`, `effectiveDeferDate`, `effectivePlannedDate` verified via exact match — InMemoryBridge computes these via ancestor-chain inheritance (project → task hierarchy)
- [ ] **NORM-04**: `repetitionRule` verified via exact match (null for now — write support not yet implemented)

## Future Requirements

### v1.3 Read Tools
- SQL filtering for tasks, projects, tags
- List/count for all entities
- Substring search

### v1.4 Field Selection & Writes
- Field selection (projection on read tools)
- Task deletion
- Notes append (field graduation)

### v1.4.1 Fuzzy Search
- Typo-tolerant search on list_tasks/count_tasks

### v1.4.2 TaskPaper Output
- Alternative output format (~5x token reduction)

### v1.4.3 Project Writes
- Project creation and editing

### v1.5 UI & Perspectives
- Perspective switching and reading
- Deep link (open task in UI)

### v1.6 Production Hardening
- Retry logic, crash recovery, fuzzy search

## Out of Scope

| Feature | Reason |
|---------|--------|
| New MCP tools | v1.2.1 is internal cleanup only — six tools unchanged |
| Behavioral changes | Refactoring must be invisible to agents using the server |
| ~~InMemoryBridge physical relocation to tests/~~ | ~~Import path complexity not worth it for a single file~~ — Revisited: now 5 test doubles, Phase 24 handles relocation |
| Pydantic experimental MISSING sentinel | Interesting but not a blocker; custom _Unset works and is well-tested |
| Automatic SQLite-to-OmniJS failover | Out of scope since v1.1 — silent fallback hides broken state |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| STRCT-01 | Phase 18 | Complete |
| STRCT-02 | Phase 18 | Complete |
| STRCT-03 | Phase 18 | Complete |
| INFRA-01 | Phase 19 | Complete |
| INFRA-02 | Phase 19 | Complete |
| INFRA-03 | Phase 19 | Complete |
| MODL-01 | Phase 20 | Complete |
| MODL-02 | Phase 20 | Complete |
| MODL-03 | Phase 20 | Complete |
| MODL-04 | Phase 20 | Complete |
| PIPE-01 | Phase 21 | Complete |
| PIPE-02 | Phase 21 | Complete |
| SVCR-01 | Phase 22 | Complete |
| SVCR-02 | Phase 22 | Complete |
| SVCR-03 | Phase 22 | Complete |
| SVCR-04 | Phase 22 | Complete |
| SVCR-05 | Phase 22 | Complete |
| INFRA-04 | Phase 23 | Complete |
| INFRA-05 | Phase 23 | Complete |
| INFRA-06 | Phase 23 | Complete |
| INFRA-07 | Phase 23 | Complete |
| INFRA-08 | Phase 24 | Complete |
| INFRA-09 | Phase 24 | Complete |
| TYPE-01 | Phase 25 | Complete |
| TYPE-02 | Phase 25 | Complete |
| TYPE-03 | Phase 25 | Complete |
| TYPE-04 | Phase 25 | Complete |
| INFRA-10 | Phase 26 | Complete |
| INFRA-11 | Phase 26 | Complete |
| INFRA-12 | Phase 26 | Complete |
| INFRA-13 | Phase 27 | Complete |
| INFRA-14 | Phase 27 | Complete |
| GOLD-01 | Phase 28 | Pending |
| GOLD-02 | Phase 28 | Pending |
| GOLD-03 | Phase 28 | Pending |
| NORM-01 | Phase 28 | Pending |
| NORM-02 | Phase 28 | Pending |
| NORM-03 | Phase 28 | Pending |
| NORM-04 | Phase 28 | Pending |

**Coverage:**
- v1.2.1 requirements: 39 total
- Mapped to phases: 39
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-22 after Phase 28 requirements defined*
