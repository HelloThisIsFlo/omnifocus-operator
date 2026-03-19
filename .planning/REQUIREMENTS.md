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

- [ ] **SVCR-01**: Validation logic extracted to dedicated module
- [ ] **SVCR-02**: Domain logic extracted to dedicated module (tag diff, repetition rule semantics)
- [ ] **SVCR-03**: Format conversion extracted to dedicated module
- [ ] **SVCR-04**: service.py converted to service/ package (preserves all import paths)
- [ ] **SVCR-05**: Each extracted module is independently testable

### Model Strictness

- [x] **STRCT-01**: Write models reject unknown fields with clear errors (`extra="forbid"`)
- [x] **STRCT-02**: Read models remain permissive (`extra="ignore"`)
- [x] **STRCT-03**: `_Unset` sentinel works correctly with `extra="forbid"`

### Test Infrastructure

- [x] **INFRA-01**: InMemoryBridge not importable from `omnifocus_operator.bridge`
- [x] **INFRA-02**: Tests import InMemoryBridge via direct module path only
- [x] **INFRA-03**: `"inmemory"` option removed from bridge/repository factory — no env var routing to test doubles
- [ ] **INFRA-04**: SimulatorBridge not importable from `omnifocus_operator.bridge`
- [ ] **INFRA-05**: Tests import SimulatorBridge via direct module path only
- [ ] **INFRA-06**: `OMNIFOCUS_BRIDGE` environment variable removed — repository factory creates RealBridge directly
- [ ] **INFRA-07**: Bridge factory (`create_bridge`) removed — env var reading absorbed into repository factory, PYTEST safety guard moved to `RealBridge.__init__`
- [ ] **INFRA-08**: All test double modules physically located under `tests/`, not `src/` (InMemoryBridge, BridgeCall, InMemoryRepository, ConstantMtimeSource, SimulatorBridge)
- [ ] **INFRA-09**: No production code (`src/`) imports test doubles — crossing the `src/`→`tests/` boundary is structurally impossible

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
| SVCR-01 | Phase 22 | Pending |
| SVCR-02 | Phase 22 | Pending |
| SVCR-03 | Phase 22 | Pending |
| SVCR-04 | Phase 22 | Pending |
| SVCR-05 | Phase 22 | Pending |
| INFRA-04 | Phase 23 | Pending |
| INFRA-05 | Phase 23 | Pending |
| INFRA-06 | Phase 23 | Pending |
| INFRA-07 | Phase 23 | Pending |
| INFRA-08 | Phase 24 | Pending |
| INFRA-09 | Phase 24 | Pending |

**Coverage:**
- v1.2.1 requirements: 23 total
- Mapped to phases: 23
- Unmapped: 0

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-17 after Phase 24 requirements added (test double relocation)*
