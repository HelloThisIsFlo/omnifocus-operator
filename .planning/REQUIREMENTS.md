# Requirements: OmniFocus Operator

**Defined:** 2026-03-16
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2.1 Requirements

Requirements for Architectural Cleanup milestone. No new tools, no behavioral changes — pure internal quality. All 534+ existing tests must continue passing.

### Write Pipeline

- [ ] **PIPE-01**: add_task and edit_task have symmetric signatures at the service-repository boundary
- [ ] **PIPE-02**: Both write paths use the same pattern for bridge payload construction (no split between repo model_dump vs service dict-building)

### Model Taxonomy

- [ ] **MODL-01**: Three-layer model taxonomy established: Request (user intent), Domain (entities), Payload (bridge format)
- [ ] **MODL-02**: Write-side request models renamed to follow consistent convention distinguishing them from domain models
- [ ] **MODL-03**: Typed bridge payload models replace `dict[str, Any]` at the service-repository boundary
- [ ] **MODL-04**: All write-side sub-models (RepetitionRuleSpec, MoveToSpec, TagActionSpec, etc.) renamed to indicate their layer

### Service Decomposition

- [ ] **SVCR-01**: Validation logic extracted to dedicated module
- [ ] **SVCR-02**: Domain logic extracted to dedicated module (tag diff, repetition rule semantics)
- [ ] **SVCR-03**: Format conversion extracted to dedicated module
- [ ] **SVCR-04**: service.py converted to service/ package (preserves all import paths)
- [ ] **SVCR-05**: Each extracted module is independently testable

### Model Strictness

- [ ] **STRCT-01**: Write models reject unknown fields with clear errors (`extra="forbid"`)
- [ ] **STRCT-02**: Read models remain permissive (`extra="ignore"`)
- [ ] **STRCT-03**: `_Unset` sentinel works correctly with `extra="forbid"`

### Test Infrastructure

- [ ] **INFRA-01**: InMemoryBridge not importable from `omnifocus_operator.bridge`
- [ ] **INFRA-02**: Tests import InMemoryBridge via direct module path only
- [ ] **INFRA-03**: `"inmemory"` option removed from bridge/repository factory — no env var routing to test doubles

## Future Requirements

### v1.3 Read Tools
- SQL filtering for tasks, projects, tags
- List/count for all entities
- Substring search

### v1.4 Output & UI
- Perspectives support
- Field selection
- TaskPaper output format

### v1.5 Production Hardening
- Retry logic, crash recovery, fuzzy search

## Out of Scope

| Feature | Reason |
|---------|--------|
| New MCP tools | v1.2.1 is internal cleanup only — six tools unchanged |
| Behavioral changes | Refactoring must be invisible to agents using the server |
| InMemoryBridge physical relocation to tests/ | Import path complexity not worth it for a single file; removing from exports is sufficient |
| Pydantic experimental MISSING sentinel | Interesting but not a blocker; custom _Unset works and is well-tested |
| Automatic SQLite-to-OmniJS failover | Out of scope since v1.1 — silent fallback hides broken state |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| PIPE-01 | — | Pending |
| PIPE-02 | — | Pending |
| MODL-01 | — | Pending |
| MODL-02 | — | Pending |
| MODL-03 | — | Pending |
| MODL-04 | — | Pending |
| SVCR-01 | — | Pending |
| SVCR-02 | — | Pending |
| SVCR-03 | — | Pending |
| SVCR-04 | — | Pending |
| SVCR-05 | — | Pending |
| STRCT-01 | — | Pending |
| STRCT-02 | — | Pending |
| STRCT-03 | — | Pending |
| INFRA-01 | — | Pending |
| INFRA-02 | — | Pending |
| INFRA-03 | — | Pending |

**Coverage:**
- v1.2.1 requirements: 17 total
- Mapped to phases: 0
- Unmapped: 17 ⚠️

---
*Requirements defined: 2026-03-16*
*Last updated: 2026-03-16 after initial definition*
