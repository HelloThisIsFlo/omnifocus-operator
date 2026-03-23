# Milestone v1.0 — Foundation: Project Summary

**Generated:** 2026-03-23
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**OmniFocus Operator** is a Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents.

- **Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am
- **Target users:** AI agents (via MCP protocol) operating on behalf of humans who use OmniFocus for task management
- **What v1.0 delivered:** A fully functional MCP server with a single `list_all` tool that returns the complete OmniFocus database as structured Pydantic data. Three bridge implementations (InMemory, Simulator, Real), file-based IPC engine, error-serving degraded mode, and 177+ tests
- **Tech stack:** Python 3.12, uv, Pydantic v2, MCP SDK (FastMCP), OmniJS bridge (JavaScript), SQLite3 (stdlib)
- **Platform:** macOS only (OmniFocus is a macOS application)
- **Runtime dependencies:** `mcp>=1.26.0` (single dep)

---

## 2. Architecture & Technical Decisions

### Core Architecture

The server uses a **three-layer architecture**: MCP Server -> Service Layer -> Repository. This clean separation means each layer can be tested independently, and swapping the bridge implementation requires zero code changes in MCP or service layers.

```
Agent (MCP client)
  |
MCP Server (FastMCP) — tool registration, structured output, stderr-only logging
  |
Service Layer (OperatorService) — business logic, snapshot orchestration
  |
Repository — snapshot caching, mtime freshness, dedup lock
  |
Bridge Protocol — pluggable: InMemoryBridge | SimulatorBridge | RealBridge
  |
File IPC Engine — atomic writes, async polling, timeout handling
  |
OmniFocus (via OmniJS bridge.js)
```

### Key Decisions

- **Dumb bridge, smart Python**
  - **Why:** OmniJS freezes the UI and has sharp edges — minimize time there. Bridge is a relay (~400 lines JS), all validation/logic lives in Python (~14,000 lines)
  - **Phase:** Foundational principle, established Phase 6-8

- **File-based IPC via OmniFocus sandbox**
  - **Why:** Benchmarked as most efficient approach within OmniFocus sandbox constraints. Atomic writes (`.tmp` -> `os.replace()`) prevent partial reads
  - **Phase:** Phase 6

- **Full snapshot in memory, no partial invalidation**
  - **Why:** Database is small (~1.5MB for ~2,400 tasks). Sub-millisecond filtering. Simplicity over complexity
  - **Phase:** Phase 4

- **Workflow-agnostic server**
  - **Why:** Server exposes primitives, not opinions. Workflow logic belongs in the agent
  - **Phase:** Foundational principle

- **Fail-fast on unknown enum values**
  - **Why:** Pydantic ValidationError with clear listing of valid values. Caught real data issues during UAT
  - **Phase:** Phase 8.2

- **Error-serving degraded mode**
  - **Why:** MCP servers are headless — crashes are invisible. Serve errors as actionable tool responses so the agent discovers the error on first call
  - **Phase:** Phase 9

- **Factory safety guard (SAFE-01)**
  - **Why:** `PYTEST_CURRENT_TEST` check blocks RealBridge instantiation during automated testing. Prevents accidental live database interaction from tests/CI
  - **Phase:** Phase 8

---

## 3. Phases Delivered

| Phase | Name | Status | Description |
|-------|------|--------|-------------|
| 1 | Project Scaffolding | Complete | Python project with uv, src layout, dev tooling, CI-ready config |
| 2 | Data Models | Complete | Pydantic models for all OmniFocus entities (Task, Project, Tag, Folder, Perspective) |
| 3 | Bridge Protocol & InMemoryBridge | Complete | Pluggable bridge abstraction + test-oriented in-memory implementation |
| 4 | Repository & Snapshot Management | Complete | In-memory snapshot with mtime freshness, dedup lock, cache pre-warming |
| 5 | Service Layer & MCP Server | Complete | Three-layer architecture wired up with `list_all` tool and DI via lifespan |
| 6 | File IPC Engine | Complete | Atomic file-based IPC with async I/O, dispatch protocol, timeout handling |
| 7 | SimulatorBridge & Mock Simulator | Complete | File IPC bridge + standalone simulator script for integration testing |
| 8 | RealBridge & E2E Validation | Complete | Production bridge with URL scheme trigger, safety guardrails |
| 8.1 | JS Bridge Script & IPC Overhaul | Complete | OmniJS bridge.js authored, IPC protocol modernized, full E2E pipeline validated |
| 8.2 | Model Alignment (BRIDGE-SPEC) | Complete | Per-entity status resolvers, RepetitionRule redesign, fail-fast enums |
| 9 | Error-Serving Degraded Mode | Complete | Fatal startup errors served as actionable tool responses |

**Build order followed dependency graph bottom-up:** models -> bridge -> repo -> service -> MCP -> IPC -> simulator -> real. Each phase built on tested foundations from the previous phase.

**Inserted phases:** 8.1 and 8.2 were urgent insertions discovered during UAT. Phase 8.1 addressed the missing bridge.js script; Phase 8.2 aligned models with empirically-verified BRIDGE-SPEC from 27 OmniJS audit scripts.

---

## 4. Requirements Coverage

All **35 v1 requirements** satisfied. Verified via 2-source cross-reference (VERIFICATION.md + REQUIREMENTS.md).

### Safety (2/2)
- SAFE-01: No automated test/CI/agent touches RealBridge
- SAFE-02: RealBridge interaction is manual UAT only

### Architecture (3/3)
- ARCH-01: Three-layer architecture (MCP -> Service -> Repository)
- ARCH-02: Bridge injected at startup, zero code changes to switch
- ARCH-03: uv + src/ layout + Python 3.12

### Data Models (7/7)
- MODL-01 through MODL-06: All entity models (Task, Project, Tag, Folder, Perspective, DatabaseSnapshot)
- MODL-07: Shared base config with camelCase aliases + populate_by_name

### Bridge (4/4)
- BRDG-01: Bridge protocol (`send_command`)
- BRDG-02: InMemoryBridge for unit testing
- BRDG-03: SimulatorBridge (file IPC without URL trigger)
- BRDG-04: RealBridge (file IPC + `omnifocus:///omnijs-run` URL scheme)

### Snapshot (6/6)
- SNAP-01 through SNAP-06: Full snapshot loading, caching, mtime freshness, atomic replacement, dedup lock, lazy population

### File IPC (6/6)
- IPC-01 through IPC-06: Atomic writes, async I/O, UUID dispatch, configurable directory, 10s timeout, orphan sweep

### MCP Tool (4/4)
- TOOL-01 through TOOL-04: `list_all` with structured output, MCP annotations, Pydantic schema, stderr-only logging

### Testing (3/3)
- TEST-01: Mock simulator as standalone script
- TEST-02: Full pipeline testable via InMemoryBridge
- TEST-03: pytest + pytest-asyncio test suite per layer

### Error Handling (7/7)
- ERR-01 through ERR-07: ErrorOperatorService, lifespan catch, actionable tool responses, traceback logging, degraded mode warnings

### Audit Verdict

**Status:** TECH DEBT (all requirements satisfied, minor process debt)
- Requirements: 35/35
- Integration: 35/35
- E2E Flows: 4/4
- Nyquist: 11/11 phases compliant

---

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-1 | Three-layer architecture | 5 | Clear separation of concerns; service layer thin in v1.0 but reserves space for filtering in future |
| D-2 | Dumb bridge, smart Python | 6-8 | OmniJS freezes UI; minimize JS complexity, maximize testable Python |
| D-3 | File-based IPC with atomic writes | 6 | Most efficient within OmniFocus sandbox; `.tmp` + `os.replace()` prevents partial reads |
| D-4 | Full snapshot in memory | 4 | Database small (~1.5MB); sub-ms filtering; simplicity over partial invalidation |
| D-5 | camelCase serialization aliases | 2 | Match bridge script output shape; `populate_by_name` for test ergonomics |
| D-6 | TYPE_CHECKING + model_rebuild | 2 | Resolve ruff TC + Pydantic compatibility for forward references |
| D-7 | Factory safety guard (PYTEST_CURRENT_TEST) | 8 | Prevent accidental RealBridge use in automated tests |
| D-8 | SimulatorBridge inherits RealBridge | 7 | Override only `_trigger_omnifocus`; share IPC mechanics |
| D-9 | bridge.js loaded via importlib.resources | 8.1 | One-time load at `__init__`; no filesystem path coupling |
| D-10 | Fail-fast on unknown enums | 8.2 | Pydantic ValidationError catches real data issues at bridge boundary |
| D-11 | Per-entity status resolvers in bridge.js | 8.2 | Tasks, projects, and tags have different status semantics |
| D-12 | RepetitionRule redesign (4 fields) | 8.2 | Match empirically-verified BRIDGE-SPEC from 27 OmniJS audit scripts |
| D-13 | Error-serving degraded mode | 9 | MCP servers are headless; crashes invisible; serve errors as tool responses |
| D-14 | Lazy cache population | 4 | No eager startup hydration; first tool call triggers bridge dump |
| D-15 | Dispatch string format `<uuid>::::<operation>` | 6 | UUID4 request IDs for file naming; reject invalid UUIDs |
| D-16 | Decimal phase insertion (8.1, 8.2) | 8.1, 8.2 | Clean pattern for handling discoveries mid-milestone without disrupting roadmap |

---

## 6. Tech Debt & Deferred Items

### Tech Debt (from Milestone Audit)

| Item | Severity | Notes |
|------|----------|-------|
| Phase 08 missing VERIFICATION.md | Low | UAT evidence exists (6/6 passed), just not in standard format |
| Phase 08.1 missing VERIFICATION.md | Low | UAT evidence exists (4/4 passed), just not in standard format |
| Plan 08.1-04 never executed | Low | Makefile unified test + UAT checkpoint — deemed unnecessary |
| SUMMARY.md missing `requirements_completed` frontmatter | Low | 3rd cross-reference source unavailable for audit |

### Deferred Items (carried to future milestones)

- Add retry logic for OmniFocus bridge timeouts (-> v1.6)
- Investigate macOS App Nap impact on OmniFocus responsiveness (-> v1.6)
- Make UAT folder discoverable for verification agents
- Investigate `replace: []` bug in production

### Key Lessons (from Retrospective)

1. **Research before building pays off massively** — 27 OmniJS audit scripts meant zero model surprises during implementation
2. **Decimal phase insertion is a clean pattern** for handling discoveries mid-milestone
3. **Don't plan "nice-to-have" plans** (08.1-04) — only plan what's needed to satisfy requirements
4. **Convention decisions should wait until patterns emerge** — the `_` prefix decision was reversed after seeing the full codebase
5. **Bottom-up dependency ordering** (models -> bridge -> repo -> service) meant each phase built on solid, tested foundations

---

## 7. Getting Started

### Run the project

```bash
git clone https://github.com/HelloThisIsFlo/omnifocus-operator.git
cd omnifocus-operator
uv sync
```

### Run tests

```bash
uv run pytest                    # All tests
uv run pytest -x                 # Stop on first failure
uv run mypy src/                 # Type checking
uv run ruff check                # Linting
```

### Key directories

```
src/omnifocus_operator/
  __main__.py          # Entry point — just create_server + run
  server.py            # MCP server with lifespan DI
  service/             # Service layer (orchestrator, domain, resolve, payload, validate)
  repository/          # Repository protocol + implementations
  bridge/              # Bridge protocol + implementations (real.py, simulator.py)
  contracts/           # Pydantic models (read, command, bridge payloads)
  agent_messages/      # All agent-facing strings (warnings, errors, guidance)
  ipc/                 # File IPC engine (atomic writes, polling, orphan sweep)

tests/
  doubles/             # Test doubles (InMemoryBridge, StubBridge, etc.)
  test_models.py       # Model round-trip tests
  test_bridge*.py      # Bridge protocol tests
  test_repository*.py  # Repository tests
  test_service*.py     # Service layer tests
  test_server.py       # MCP server integration tests

bridge-js/             # OmniJS bridge script (JavaScript + Vitest tests)
uat/                   # Manual UAT scripts (NEVER run by CI/agents)
```

### Where to look first

1. `src/omnifocus_operator/server.py` — MCP tool registration and lifespan DI
2. `src/omnifocus_operator/service/orchestrator.py` — Service layer orchestration
3. `src/omnifocus_operator/contracts/` — All Pydantic models
4. `src/omnifocus_operator/bridge/real.py` — Production bridge (file IPC + URL scheme)
5. `CLAUDE.md` — Project conventions and safety rules

### Safety rules (critical)

- **SAFE-01:** No automated test/CI/agent may touch `RealBridge`. All automated testing uses InMemoryBridge or StubBridge
- **SAFE-02:** RealBridge interaction is manual UAT only. UAT scripts in `uat/` are excluded from pytest and CI

---

## Stats

- **Timeline:** 2026-02-21 -> 2026-03-07 (14 days)
- **Phases:** 11 / 11 complete
- **Plans executed:** 22
- **Commits:** 235
- **Files changed:** 264 (+48,443 insertions)
- **Contributors:** Flo Kempenich
- **Test suite:** 177+ pytest tests (~98% coverage), 26 Vitest tests
- **Average plan execution:** ~4 minutes
