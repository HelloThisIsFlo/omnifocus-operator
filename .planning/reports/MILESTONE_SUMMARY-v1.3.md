# Milestone v1.3 — Read Tools

**Generated:** 2026-04-05
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

**OmniFocus Operator** is a Python MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge.

**Core value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

**What v1.3 added:** Gave agents the ability to query, filter, browse, and count OmniFocus entities. Before v1.3, agents could only fetch the entire database (`get_all`) or look up individual entities by ID. After v1.3, agents have 5 new list tools with 10+ filters, pagination, search, and intelligent "did you mean?" suggestions.

**Tech stack:** Python 3.12, uv, Pydantic v2, FastMCP v3 (`fastmcp>=3.1.1`), OmniJS bridge, SQLite3 (stdlib).

**At milestone end:** 11 MCP tools, 1,528 pytest tests, 26 Vitest tests, ~94% coverage.

---

## 2. Architecture & Technical Decisions

### Decisions Made in v1.3

- **Parameterized SQL builder as pure functions**
  - **Why:** Zero SQL injection surface, testable without database. Returns `SqlQuery(sql, params)` NamedTuple.
  - **Phase:** 34

- **Fetch-all + Python filter for small collections**
  - **Why:** Tags/folders/perspectives are small collections. SQL is overkill — full fetch + Python filtering is simpler and fast enough.
  - **Phase:** 35

- **Name-to-ID resolution at service boundary**
  - **Why:** Prevents SQL/in-memory drift. Resolution cascade (ID match → substring → fuzzy "did you mean?") runs once at service layer. RepoQuery is IDs-only.
  - **Phase:** 35.2

- **ValidationReformatterMiddleware for error formatting**
  - **Why:** Catches Pydantic ValidationError and reformats to agent-friendly ToolError. Consistent error surface across all 11 tools.
  - **Phase:** 36.1

- **Description centralization in agent_messages/**
  - **Why:** All 60 agent-visible Field(description=) strings and class docstrings use constants from `descriptions.py`. AST enforcement prevents drift.
  - **Phase:** 36.3

- **Literal/Annotated reserved for contract models**
  - **Why:** Clean taxonomy boundary. Core models use plain types; schema-level constraints only at contract boundary. AST enforcement test prevents regression.
  - **Phase:** 36.4

- **Cross-path equivalence as hard requirement**
  - **Why:** 32 parametrized tests prove SQL and bridge paths return identical results. Mandatory for any new filter. Caught real divergence during development.
  - **Phase:** 36

- **DEFAULT_LIST_LIMIT=50 on all list tools**
  - **Why:** Prevents unbounded responses (1.8M chars for full DB). Agent can override with `limit=None`.
  - **Phase:** 37

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 34 | Contracts and Query Foundation | Complete | Typed query models, ListResult container, SQL builder, protocol extensions |
| 35 | SQL Repository | Complete | HybridRepository list methods with filtered SQL for all 5 entity types |
| 35.1 | Contract Boundary Split | Complete | Read-side RepoQuery/RepoResult split with per-use-case packages |
| 35.2 | Uniform Name/ID Resolution | Complete | Service-layer resolution cascade with "did you mean?" warnings |
| 36 | Service Orchestration + Cross-Path | Complete | Validation, defaults, duration parsing, 32 cross-path equivalence tests |
| 36.1 | Write Tool Schema Migration | Complete | Rich inputSchema via typed params, ValidationReformatterMiddleware |
| 36.2 | Agent-Facing Documentation Sweep | Complete | Model/tool docstrings cleaned of implementation leakage |
| 36.3 | Description Centralization | Complete | 60 constants in descriptions.py with AST enforcement |
| 36.4 | Type Constraint Boundary | Complete | Literal/Annotated reserved for contracts, AST enforcement |
| 37 | Server Registration and Integration | Complete | 5 list MCP tools wired end-to-end with search on all entity types |
| 37.1 | Ghost Task Fix | Complete | Fixed effectiveCompletionDate availability mappers and SQL clauses |
| 38 | List Tool Param Docs | Complete | Collaborative phrasing session — Field descriptions and tool docstrings refined |

---

## 4. Requirements Coverage

**80/80 requirements satisfied.** All checkboxes green.

### By Category

- ✅ **Task Querying** (TASK-01..11, skip 05): 10/10 — inbox, flagged, project, tags, estimated time, availability, search, pagination, AND logic, default exclusion
- ✅ **Project Querying** (PROJ-01..07, skip 03): 6/6 — availability filter, folder filter, review due within, flagged, pagination
- ✅ **Entity Browsing** (BROWSE-01..03): 3/3 — tags, folders, perspectives with status filter
- ✅ **Entity Search** (SRCH-01..04): 4/4 — substring search on all 5 entity types
- ✅ **Write Tool Schema** (WRIT-01..11): 11/11 — rich inputSchema, agent-friendly validation errors, canary test
- ✅ **Agent-Facing Docs** (DOC-01..14): 14/14 — no implementation leakage, behavioral guidance only
- ✅ **Description Centralization** (DESC-01..08): 8/8 — 60 constants, AST enforcement, 2KB byte limit
- ✅ **Type Constraint Boundary** (TYPE-01..07): 7/7 — Literal/Annotated reserved for contracts, AST enforcement
- ✅ **Read Tool Registration** (RTOOL-01..03): 3/3 — typed query params, camelCase aliases, middleware coverage
- ✅ **Query Infrastructure** (INFRA-01..16): 16/16 — parameterized SQL, cross-path equivalence, name resolution, pagination
- ✅ **Ghost Task Fix** (D-01..06): 6/6 — effective date columns in mappers and SQL

### Audit Verdict

**tech_debt** — all requirements met, no critical blockers, 7 accumulated items across 4 phases (all process artifacts/Nyquist gaps, no code issues).

### Deferred

- **TASK-05** (has_children filter): No clear agent use case — deferred indefinitely
- **Date filtering** (DATE-01..05): Deferred to v1.3.2
- **Count tools**: Redundant — `total_count` in ListResult suffices

---

## 5. Key Decisions Log

| # | Decision | Phase | Rationale |
|---|----------|-------|-----------|
| 1 | Parameterized SQL builder | 34 | Zero injection, testable pure functions |
| 2 | Fetch-all + Python filter for small collections | 35 | Tags/folders too small to justify SQL queries |
| 3 | Per-use-case package structure (`contracts/use_cases/{verb}/`) | 35.1 | Clean contract boundary per domain operation |
| 4 | Resolution cascade at service boundary | 35.2 | ID match → substring → "did you mean?" — all 5 tools get it free |
| 5 | Cross-path equivalence as hard requirement | 36 | 32 tests catch SQL/bridge divergence automatically |
| 6 | ValidationReformatterMiddleware | 36.1 | Uniform agent-friendly errors across all tools |
| 7 | Approved verbatim text for tool docstrings | 36.2 | Prevents implementation leakage into agent-facing docs |
| 8 | `descriptions.py` with AST enforcement | 36.3 | Single source of truth for all 60 agent-visible strings |
| 9 | Literal/Annotated boundary with AST enforcement | 36.4 | Clean type taxonomy: contracts constrain, core models don't |
| 10 | DEFAULT_LIST_LIMIT=50 | 37 | Protect agent context windows from 1.8M char dumps |
| 11 | `ReviewDueFilter` as first value object filter | 36 | Pattern for domain-specific filter parsing |

---

## 6. Tech Debt & Deferred Items

### Tech Debt (from Milestone Audit)

- **Phase 34:** VALIDATION.md nyquist_compliant: false — validation gaps not closed
- **Phase 35.2:** VALIDATION.md nyquist_compliant: false — validation gaps not closed
- **Phase 36.3:** No VALIDATION.md — Nyquist validation never run; DESC-07/DESC-08 checkboxes not updated (code correct)
- **Phase 38:** No VERIFICATION.md — collaborative session, no formal pipeline; list_tasks hierarchy explanation deferred to v1.3.1

### Lessons from Retrospective

- Original 4-phase roadmap was too coarse — became 12 phases with 7 insertions. Future milestones should plan for architectural cleanup phases upfront.
- Automated enforcement > manual checklists — AST tests self-maintain; traceability table checkboxes drift.
- Collaborative sessions work for documentation — formal pipelines add overhead for phrasing work.

### Deferred to Future Milestones

- Date-based filtering (v1.3.2)
- Fuzzy search (v1.4.1)
- Field selection, task deletion, notes append (v1.4)
- list_tasks hierarchy explanation (parent vs project) — v1.3.1

---

## 7. Getting Started

- **Run the project:** `uv sync && uv run omnifocus-operator`
- **Run tests:** `uv run pytest` (1,528 tests, ~94% coverage)
- **Key directories:**
  - `src/omnifocus_operator/` — main package
  - `src/omnifocus_operator/service/` — orchestrator, resolver, domain logic, payload builder
  - `src/omnifocus_operator/contracts/use_cases/` — per-use-case packages (list/, add/, edit/)
  - `src/omnifocus_operator/agent_messages/` — errors, warnings, descriptions
  - `src/omnifocus_operator/models/` — core Pydantic models
  - `tests/doubles/` — InMemoryBridge, StubBridge, SimulatorBridge
  - `bridge/` — OmniJS bridge script
- **Where to look first:**
  - `src/omnifocus_operator/server.py` — MCP tool registration (11 tools)
  - `src/omnifocus_operator/service/__init__.py` — service orchestrator
  - `src/omnifocus_operator/repository/hybrid_repository.py` — SQL + bridge read path
  - `docs/architecture.md` — full architecture documentation
  - `docs/model-taxonomy.md` — model naming and placement conventions

---

## Stats

- **Timeline:** 2026-03-29 → 2026-04-05 (7 days)
- **Phases:** 12/12 complete
- **Plans:** 26 executed
- **Commits:** 409 (in milestone), 1,595 cumulative
- **Files changed:** 343 (+49,835 / -2,268) total; 92 code files (+9,796 / -1,533)
- **Test growth:** 1,139 → 1,528 pytest tests (+389)
- **Requirements:** 80/80 satisfied
- **Contributors:** Flo Kempenich
