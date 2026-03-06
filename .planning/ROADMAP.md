# Roadmap: OmniFocus Operator

## Overview

OmniFocus Operator delivers a working MCP server that exposes OmniFocus as structured task infrastructure for AI agents. The build order follows the dependency graph bottom-up: data models first, then the bridge abstraction, then the repository/snapshot layer, then the MCP server surface, then the file IPC engine, and finally the concrete bridge implementations (simulator and real). Each phase delivers a testable, coherent capability that the next phase builds on. By Phase 8, the full pipeline is proven end-to-end with real OmniFocus interaction validated manually by the user.

## Phases

**Phase Numbering:**

- Integer phases (1, 2, 3): Planned milestone work
- Decimal phases (2.1, 2.2): Urgent insertions (marked with INSERTED)

Decimal phases appear between their surrounding integers in numeric order.

- **Phase 1: Project Scaffolding** - Python project structure with uv, src layout, dev tooling, and CI-ready configuration
- **Phase 2: Data Models** - Pydantic models for all OmniFocus entities derived from bridge script output shape
- **Phase 3: Bridge Protocol and InMemoryBridge** - Abstract bridge interface and test-oriented in-memory implementation
- **Phase 4: Repository and Snapshot Management** - In-memory database snapshot with mtime freshness, dedup lock, and cache pre-warming
- **Phase 5: Service Layer and MCP Server** - Three-layer architecture wired up with list_all tool and DI via lifespan
- **Phase 6: File IPC Engine** - Atomic file-based IPC with async I/O, dispatch protocol, timeout handling, and startup cleanup
- **Phase 7: SimulatorBridge and Mock Simulator** - File IPC bridge without URL trigger plus standalone simulator script for integration testing
- **Phase 8: RealBridge and End-to-End Validation** - Production bridge with URL scheme trigger, full test suite, and safety guardrails enforced

## Phase Details

### Phase 1: Project Scaffolding

**Goal**: A runnable Python project with all tooling configured so that subsequent phases can immediately write code, run tests, and lint
**Depends on**: Nothing (first phase)
**Requirements**: ARCH-03
**Success Criteria** (what must be TRUE):

1. `uv run pytest` executes successfully (even with zero tests) from a clean checkout
2. `uv run ruff check` and `uv run mypy` run without configuration errors
3. Project uses `src/omnifocus_operator/` layout with a `__init__.py` that can be imported
4. `pyproject.toml` declares `mcp>=1.26.0` as runtime dependency and dev tools (ruff, mypy, pytest, pytest-asyncio) as dev dependencies
**Plans**: 1 plan

Plans:

- [ ] 01-01-PLAN.md — Scaffold Python project with uv, src/ layout, all dev tooling, pre-commit, and CI

### Phase 2: Data Models

**Goal**: Typed Pydantic models for every OmniFocus entity that match the bridge script output shape exactly, with camelCase serialization aliases
**Depends on**: Phase 1
**Requirements**: MODL-01, MODL-02, MODL-03, MODL-04, MODL-05, MODL-06, MODL-07
**Success Criteria** (what must be TRUE):

1. A sample JSON payload from the bridge script round-trips through model parsing and serialization without data loss
2. `DatabaseSnapshot` model accepts a full dump payload containing tasks, projects, tags, folders, and perspectives
3. All models use snake_case field names in Python and serialize to camelCase via aliases
4. Models can be instantiated in tests with `populate_by_name=True` (no alias juggling in test code)
**Plans**: 2 plans

Plans:

- [ ] 02-01-PLAN.md — Base model hierarchy, enums, common models, test fixtures (MODL-07)
- [ ] 02-02-PLAN.md — Entity models (Task, Project, Tag, Folder, Perspective), DatabaseSnapshot, full test suite (MODL-01 through MODL-06)

### Phase 3: Bridge Protocol and InMemoryBridge

**Goal**: A pluggable bridge abstraction that decouples all upstream code from OmniFocus, with a test implementation that returns data from memory
**Depends on**: Phase 2
**Requirements**: BRDG-01, BRDG-02
**Success Criteria** (what must be TRUE):

1. Bridge protocol defines `send_command(operation, params) -> response` as a typed interface
2. InMemoryBridge returns a realistic DatabaseSnapshot from memory when `dump_all` is called
3. Any code accepting the bridge protocol works identically with InMemoryBridge or any future implementation (no type errors, no isinstance checks)
**Plans**: 1 plan

Plans:

- [ ] 03-01-PLAN.md — Bridge protocol, error hierarchy, and InMemoryBridge (TDD)

### Phase 4: Repository and Snapshot Management

**Goal**: A repository that loads and caches a full database snapshot, serves reads from memory, and refreshes only when OmniFocus data changes
**Depends on**: Phase 3
**Requirements**: SNAP-01, SNAP-02, SNAP-03, SNAP-04, SNAP-05, SNAP-06
**Success Criteria** (what must be TRUE):

1. First call to repository triggers a bridge dump and returns a populated DatabaseSnapshot
2. Subsequent calls return the cached snapshot without calling the bridge again (verifiable via call count)
3. When the mtime source changes, the next read triggers a fresh dump that atomically replaces the cached snapshot
4. Concurrent reads while a dump is in progress do not trigger additional dumps (lock prevents parallel storms)
5. Repository pre-warms the cache at startup so the first external request hits warm data
**Plans**: 1 plan

Plans:

- [ ] 04-01-PLAN.md — OmniFocusRepository with MtimeSource, caching, concurrency lock, pre-warm (TDD)

### Phase 5: Service Layer and MCP Server

**Goal**: A running MCP server with the `list_all` tool that returns the full structured database, wired with dependency injection so the bridge implementation is swappable at startup
**Depends on**: Phase 4
**Requirements**: ARCH-01, ARCH-02, TOOL-01, TOOL-02, TOOL-03, TOOL-04
**Success Criteria** (what must be TRUE):

1. `list_all` tool returns the full DatabaseSnapshot as structured Pydantic data when invoked via MCP protocol
2. Tool includes MCP annotations (`readOnlyHint: true`, `idempotentHint: true`) in its registration
3. Server outputs structured schema (from Pydantic models) in the tool's output definition
4. All server output goes to stderr; stdout is reserved exclusively for MCP protocol traffic
5. Switching from InMemoryBridge to any other bridge requires zero code changes in MCP or service layers (configuration only)
**Plans**: 3 plans

Plans:

- [ ] 05-01-PLAN.md — OperatorService, ConstantMtimeSource, bridge factory (TDD)
- [ ] 05-02-PLAN.md — MCP server with lifespan, list_all tool, entry point, integration tests (TDD)
- [ ] 05-03-PLAN.md — Gap closure: seed InMemoryBridge factory with realistic sample data for camelCase UAT

### Phase 6: File IPC Engine

**Goal**: A robust async file IPC mechanism that can exchange commands and responses between the Python server and an external process via the filesystem
**Depends on**: Phase 1
**Requirements**: IPC-01, IPC-02, IPC-03, IPC-04, IPC-05, IPC-06
**Success Criteria** (what must be TRUE):

1. File writes use atomic pattern (write to `.tmp`, then `os.replace()` to final path) -- no partial reads possible
2. All file I/O operations are non-blocking in async context (no event loop stalls)
3. Dispatch strings follow `<uuid>::::<operation>` format and reject invalid UUIDs
4. IPC base directory is configurable (defaults to OmniFocus 4 sandbox path, overridable for dev/test)
5. Timeout at 10 seconds produces an actionable error message that names OmniFocus explicitly
6. Server startup sweeps orphaned request/response files from IPC directory
**Plans**: 3 plans

Plans:

- [x] 06-01-PLAN.md — RealBridge core IPC mechanics: atomic writes, async polling, dispatch protocol, timeout handling (TDD)
- [x] 06-02-PLAN.md — IPC directory config, PID-based orphan sweep, factory wiring, package exports (TDD)
- [x] 06-03-PLAN.md — Gap closure: wire sweep_orphaned_files into server startup lifespan (IPC-06 UAT fix)

### Phase 7: SimulatorBridge and Mock Simulator

**Goal**: A file-based IPC bridge and companion simulator script that prove the full IPC pipeline works without requiring OmniFocus to be running
**Depends on**: Phase 5, Phase 6
**Requirements**: BRDG-03, TEST-01
**Success Criteria** (what must be TRUE):

1. SimulatorBridge sends commands via file IPC and receives responses -- full round-trip without URL scheme trigger
2. Mock simulator script runs as a standalone Python process, watches for request files, and writes response files
3. MCP server can be started with SimulatorBridge and the `list_all` tool returns data produced by the simulator
**Plans**: 2 plans

Plans:

- [ ] 07-01-PLAN.md — SimulatorBridge class, factory wiring, lifespan update, exports, unit tests (BRDG-03)
- [ ] 07-02-PLAN.md — Mock simulator package with realistic data, CLI entry point, integration tests (TEST-01, BRDG-03)

### Phase 8: RealBridge and End-to-End Validation

**Goal**: The production bridge that communicates with live OmniFocus, a complete test suite covering all layers, and enforced safety guardrails preventing automated real-database interaction
**Depends on**: Phase 7
**Requirements**: BRDG-04, SAFE-01, SAFE-02, TEST-02, TEST-03
**Success Criteria** (what must be TRUE):

1. RealBridge sends commands via file IPC and triggers OmniFocus via `omnifocus:///omnijs-run` URL scheme
2. Full pipeline is testable end-to-end via InMemoryBridge with zero OmniFocus dependency (no test imports or uses RealBridge)
3. pytest suite has tests for each layer (models, bridge, repository, service, MCP server) and all pass
4. No automated test, CI configuration, or script references RealBridge -- grep for RealBridge in test files returns zero matches
5. RealBridge interaction is documented as manual UAT only, with clear instructions for the user to test against their live database
**Plans**: 2 plans

Plans:

- [x] 08-01-PLAN.md — RealBridge URL scheme trigger, factory safety guard, FileMtimeSource wiring, test refactoring (BRDG-04, SAFE-01)
- [ ] 08-02-PLAN.md — CI safety step, UAT framework, CLAUDE.md safety rules, test coverage audit (SAFE-01, SAFE-02, TEST-02, TEST-03)

## Progress

**Execution Order:**
Phases execute in numeric order: 1 -> 2 -> 3 -> 4 -> 5 -> 6 -> 7 -> 8


| Phase                                   | Plans Complete | Status      | Completed |
| --------------------------------------- | -------------- | ----------- | --------- |
| 1. Project Scaffolding                  | 0/0            | Not started | -         |
| 2. Data Models                          | 0/0            | Not started | -         |
| 3. Bridge Protocol and InMemoryBridge   | 0/0            | Not started | -         |
| 4. Repository and Snapshot Management   | 0/0            | Not started | -         |
| 5. Service Layer and MCP Server         | 0/0            | Not started | -         |
| 6. File IPC Engine                      | 0/0            | Not started | -         |
| 7. SimulatorBridge and Mock Simulator   | 0/0            | Not started | -         |
| 8. RealBridge and End-to-End Validation | 0/0            | Not started | -         |



### Phase 08.2: Enforce fail-fast model fields, fix bridge status helpers, and redesign RepetitionRule (INSERTED)

**Goal:** Full alignment of the bridge script (JS) and Python models/enums with the empirically-verified BRIDGE-SPEC -- per-entity status resolvers, RepetitionRule redesign with 4 fields, fail-fast on all required fields, TagRef format, url fields, and model hierarchy restructuring
**Requirements**: B1-B14, P1-P17, T1-T11
**Depends on:** Phase 08.1
**Plans:** 2/3 plans executed

Plans:
- [ ] 08.2-01-PLAN.md — Bridge JS: per-entity status resolvers, RepetitionRule resolvers, field updates, Vitest tests
- [ ] 08.2-02-PLAN.md — Python: per-entity enums, model hierarchy restructuring, entity model updates, namespace rebuild
- [ ] 08.2-03-PLAN.md — Test infrastructure: conftest factories, test_models.py, seed data alignment

### Phase 08.1: OmniFocus Bridge Script — Author JS bridge, wire into RealBridge IPC, fix UAT (INSERTED)

**Goal:** A working JS bridge script inside OmniFocus that completes the end-to-end IPC pipeline, with the IPC protocol modernized (clean JSON envelopes, `snapshot` operation name), and the full pipeline validated against live OmniFocus via UAT
**Requirements**: JS-BRIDGE-01, JS-BRIDGE-02, JS-BRIDGE-03, IPC-PROTO-01, IPC-PROTO-02, IPC-PROTO-03, RENAME-01, SIM-UPDATE-01, PKG-01, MAKEFILE-01
**Depends on:** Phase 8
**Plans:** 3/4 plans executed

Plans:
- [ ] 08.1-01-PLAN.md — Author JS bridge script + npm project + Vitest tests
- [ ] 08.1-02-PLAN.md — Rename dump_all to snapshot across entire codebase
- [ ] 08.1-03-PLAN.md — IPC protocol overhaul + bridge.js loading + simulator update
- [ ] 08.1-04-PLAN.md — Makefile unified test command + UAT checkpoint
