# Roadmap: OmniFocus Operator

## Milestones

- ✅ **v1.0 Foundation** — Phases 1-9 (shipped 2026-03-07)
- ✅ **v1.1 HUGE Performance Upgrade** — Phases 10-13 (shipped 2026-03-07)
- ✅ **v1.2 Writes & Lookups** — Phases 14-17 (shipped 2026-03-16)
- ✅ **v1.2.1 Architectural Cleanup** — Phases 18-28 (shipped 2026-03-23)
- 🚧 **v1.2.2 FastMCP v3 Migration** — Phases 29-31 (in progress)

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

### v1.2.2 FastMCP v3 Migration (In Progress)

**Milestone Goal:** Migrate from `mcp.server.fastmcp` to standalone `fastmcp>=3` -- infrastructure upgrade with no new tools or behavioral changes.

- [x] **Phase 29: Dependency Swap & Imports** (2/2 plans) — completed 2026-03-26
- [x] **Phase 30: Test Client Migration** - Replace test plumbing with 3-line Client(server) pattern (completed 2026-03-26)
- [x] **Phase 31: Middleware & Logging** - Automatic tool logging via middleware, dual-handler stderr + file logging (completed 2026-03-26)

## Phase Details

### Phase 29: Dependency Swap & Imports
**Goal**: Server runs on fastmcp>=3 with identical behavior -- all 6 tools functional, progress reporting in batch ops, docs updated
**Depends on**: Nothing (first phase of v1.2.2)
**Requirements**: DEP-01, DEP-02, DEP-03, DEP-04, PROG-01, PROG-02, DOC-01, DOC-02
**Status**: ✓ Complete (2026-03-26)
**Plans:** 2 plans
- [x] 29-01-PLAN.md -- Dependency swap, import migration, Context types, lifespan shorthand
- [x] 29-02-PLAN.md -- Progress reporting in batch handlers, README and landing page updates

### Phase 30: Test Client Migration
**Goal**: Test infrastructure uses fastmcp's native Client pattern -- all manual plumbing deleted
**Depends on**: Phase 29
**Requirements**: TEST-01, TEST-02, TEST-03, TEST-04, TEST-05
**Success Criteria** (what must be TRUE):
  1. `_ClientSessionProxy` class no longer exists in conftest.py
  2. `run_with_client` helper no longer exists in test_server.py
  3. Server tests use `async with Client(server) as client` for all tool invocations
  4. Error assertions use `pytest.raises(ToolError)` instead of `is_error` boolean checks
  5. All existing tests pass -- zero regressions from client migration
**Plans:** 2/2 plans complete
- [x] 30-01-PLAN.md -- Fixture swap, field renames, error assertion migration in conftest.py + test_server.py
- [x] 30-02-PLAN.md -- run_with_client caller migration, simulator files, dead code + import cleanup

### Phase 31: Middleware & Logging
**Goal**: Tool call logging happens automatically via middleware, with dual-handler stderr + file logging under correct namespace
**Depends on**: Phase 30
**Requirements**: MW-01, MW-02, MW-03, LOG-01, LOG-02, LOG-03, LOG-04, LOG-05
**Success Criteria** (what must be TRUE):
  1. `ToolLoggingMiddleware` logs tool name, timing, and errors for every tool call automatically
  2. `log_tool_call()` function and its 6 call sites are deleted from server.py
  3. Adding a new tool requires zero logging boilerplate -- middleware fires without wiring
  4. Server logs appear on stderr (visible in Claude Desktop logs)
  5. Server logs are written to `~/Library/Logs/omnifocus-operator.log` for persistent debugging
  6. All loggers use `omnifocus_operator.*` namespace hierarchy
  7. The stderr hijacking misdiagnosis comment is removed from `__main__.py`
  8. `ctx.info()` / `ctx.warning()` are not called anywhere in production code
**Plans:** 2/2 plans complete
- [x] 31-01-PLAN.md -- ToolLoggingMiddleware creation, server wiring, log_tool_call deletion
- [x] 31-02-PLAN.md -- Dual-handler logging setup, __name__ convention across all modules

## Progress

**Execution Order:**
Phases execute in numeric order: 29 → 30 → 31

| Phase | Milestone | Plans Complete | Status | Completed |
|-------|-----------|----------------|--------|-----------|
| 1-9 | v1.0 | 22/23 | Complete | 2026-03-07 |
| 10-13 | v1.1 | 11/11 | Complete | 2026-03-07 |
| 14-17 | v1.2 | 21/21 | Complete | 2026-03-16 |
| 18-28 | v1.2.1 | 27/27 | Complete | 2026-03-23 |
| 29. Dependency Swap & Imports | v1.2.2 | 2/2 | Complete | 2026-03-26 |
| 30. Test Client Migration | v1.2.2 | 2/2 | Complete    | 2026-03-26 |
| 31. Middleware & Logging | v1.2.2 | 2/2 | Complete   | 2026-03-26 |
