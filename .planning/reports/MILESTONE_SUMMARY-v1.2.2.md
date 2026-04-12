# Milestone v1.2.2 — Project Summary

**Generated:** 2026-04-12
**Purpose:** Team onboarding and project review

---

## 1. Project Overview

OmniFocus Operator is a Python MCP server exposing OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge. Agent-first design with educational warnings, typed models, and patch semantics.

**v1.2.2 focus:** Migrate from `mcp>=1.26.0` to standalone `fastmcp>=3.1.1` — infrastructure upgrade with no new tools or behavioral changes. Three phases executed in a single day.

**State at v1.2.2 ship:**
- 6 MCP tools: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`
- 708 pytest tests, 26 Vitest tests, ~98% coverage
- Tech stack: Python 3.12, uv, Pydantic v2, FastMCP v3, SQLite3 (stdlib)

---

## 2. Architecture & Technical Decisions

- **FastMCP v3 standalone package:** Migrated from `mcp.server.fastmcp` to `fastmcp>=3.1.1`. Native imports, `ctx.lifespan_context` shorthand, `Client(server)` test pattern
  - **Why:** FastMCP v3 is a standalone package with cleaner API, simpler test infrastructure, and built-in middleware support
  - **Phase:** 29 (dependency swap), 30 (test client), 31 (middleware)

- **ToolLoggingMiddleware via cross-cutting concern:** FastMCP `Middleware` base class with injected logger. Zero per-tool wiring needed — new tools get logging automatically
  - **Why:** Eliminated 6 manual `log_tool_call()` call sites. Adding a new tool requires zero logging boilerplate
  - **Phase:** 31

- **Dual-handler logging:** `StreamHandler(stderr)` for Claude Desktop visibility + 5MB `RotatingFileHandler` for persistent debugging. `__name__` convention across all 10 modules
  - **Why:** Claude Desktop reads stderr; Claude Code swallows stderr during tool calls (anthropics/claude-code#29035). Both handlers ensure observability in all contexts
  - **Phase:** 31

- **Client(server) test fixture:** 10-line async fixture replacing 65-line `_ClientSessionProxy`. `pytest.raises(ToolError)` as idiomatic error assertion
  - **Why:** FastMCP v3's `Client` wraps the entire connection lifecycle. Eliminates `anyio`, `ClientSession`, `SessionMessage` imports from test code
  - **Phase:** 30

- **ToolAnnotations stays at mcp.types:** FastMCP v3 doesn't re-export `ToolAnnotations`. Intentional residual `from mcp.types import ToolAnnotations` with TODO
  - **Why:** No alternative available — documented with TODO for revisit when fastmcp re-exports
  - **Phase:** 29

---

## 3. Phases Delivered

| Phase | Name | Status | One-Liner |
|-------|------|--------|-----------|
| 29 | Dependency Swap & Imports | Complete | Swapped mcp>=1.26.0 for fastmcp>=3.1.1, migrated all src/ imports, added progress reporting scaffolding |
| 30 | Test Client Migration | Complete | Replaced 65-line _ClientSessionProxy with 10-line Client(server) fixture, migrated 40+ tests |
| 31 | Middleware & Logging | Complete | ToolLoggingMiddleware replaces manual logging, dual-handler stderr + rotating file across 10 modules |

---

## 4. Requirements Coverage

All 21 requirements satisfied. Audit score: 21/21.

### Dependency Migration
- ✅ **DEP-01**: Server runs on `fastmcp>=3.1.1` with all 6 tools functional
- ✅ **DEP-02**: All imports migrated from `mcp.server.fastmcp` to `fastmcp`
- ✅ **DEP-03**: `ctx.lifespan_context` shorthand replaces old pattern
- ✅ **DEP-04**: `pyproject.toml` declares `fastmcp>=3.1.1` replacing `mcp>=1.26.0`

### Test Infrastructure
- ✅ **TEST-01**: `_ClientSessionProxy` class deleted from conftest.py
- ✅ **TEST-02**: `run_with_client` helper deleted from test_server.py
- ✅ **TEST-03**: All server tests use `async with Client(server) as client` pattern
- ✅ **TEST-04**: Error assertions use `pytest.raises(ToolError)` instead of `is_error` boolean checks
- ✅ **TEST-05**: All existing tests pass with new test client

### Middleware
- ✅ **MW-01**: `ToolLoggingMiddleware` logs tool entry, exit (with timing), and errors automatically
- ✅ **MW-02**: `log_tool_call()` function and all 6 call sites deleted from server.py
- ✅ **MW-03**: Middleware fires for every tool call without manual wiring

### Logging
- ✅ **LOG-01**: `StreamHandler(stderr)` active for Claude Desktop log visibility
- ✅ **LOG-02**: `RotatingFileHandler(~/Library/Logs/omnifocus-operator.log)` active for persistent debugging
- ✅ **LOG-03**: Logger hierarchy uses `omnifocus_operator.*` namespace
- ✅ **LOG-04**: stderr hijacking misdiagnosis comment removed from `__main__.py`
- ✅ **LOG-05**: `ctx.info()` / `ctx.warning()` not used anywhere

### Progress
- ✅ **PROG-01**: `add_tasks` reports progress via `ctx.report_progress()` during batch processing
- ✅ **PROG-02**: `edit_tasks` reports progress via `ctx.report_progress()` during batch processing

### Documentation
- ✅ **DOC-01**: README reflects `fastmcp>=3.1.1` as runtime dependency
- ✅ **DOC-02**: Landing page reflects new dependency and unchanged tool count

**Milestone Audit:** PASSED — 21/21 requirements, 3/3 phases verified, 3/3 E2E flows complete, Nyquist-compliant on all phases.

---

## 5. Key Decisions Log

| ID | Decision | Phase | Rationale |
|----|----------|-------|-----------|
| D-09 | Implement as if built from scratch with fastmcp>=3 — no minimal-impact migration | 29 | Code should look native to FastMCP v3. Applies to all phases |
| D-02 | ToolLoggingMiddleware receives server's logger via injection | 31 | All MCP-layer logs stay under `omnifocus_operator` namespace |
| D-06 | Keep response-shape `logger.debug()` lines in handlers | 31 | Middleware can't see response content (task counts, names, warning flags) |
| D-03 | `pytest.raises(ToolError, match="...")` replaces `isError` checks | 30 | One-liner pattern, Pythonic, matches team feedback preference |
| D-04 | Delete `isError is not True` success guards entirely | 30 | No exception = success. Content assertions on the next line catch regressions |
| D-08 | Root logger with `propagate=False`, dual handlers | 31 | Single config point; children inherit via propagation |
| D-12 | Delete emoji startup banner from `__main__.py` | 31 | FastMCP's own startup banner is sufficient |

---

## 6. Tech Debt & Deferred Items

### Tech Debt
- **Intentional residual:** `from mcp.types import ToolAnnotations` in server.py — fastmcp doesn't re-export this type. Documented with TODO, revisit when fastmcp adds the export
- **Documentation artifact:** REQUIREMENTS.md checkboxes unchecked for DEP-01..04, PROG-01..02, DOC-01..02 despite all being code-verified (trivial)
- **SUMMARY frontmatter gaps:** DEP-01..04, TEST-01, TEST-04 missing from `requirements_completed` frontmatter (trivial)

### Deferred Items
- **Elicitation** (`ctx.elicit()`) — Claude Desktop doesn't support it; revisit when it does
- **`Depends()` DI pattern** — Lifespan pattern works; `Depends()` solves a different lifecycle problem
- **Background tasks** (`@mcp.tool(task=True)`) — No use case in current tool set
- **`get_logger()` from FastMCP** — Wrong namespace (`fastmcp.*`), no logger name in output

### Retrospective Lessons
- **Spike-first approach is essential for migrations** — 8 experiments eliminated all unknowns, compressed 6 planned phases to 3
- **Infrastructure migrations can be fast** — 3 phases, 6 plans, single day of execution when research is thorough
- **Phase consolidation from spike findings** — original 6-phase plan was over-planned; spike evidence compressed to 3 phases with better boundaries

---

## 7. Getting Started

- **Run the project:** `uv run omnifocus-operator` (starts MCP server on stdio)
- **Run tests:** `uv run pytest` (708 tests, ~98% coverage)
- **Key directories:**
  - `src/omnifocus_operator/` — Server, service, repository, bridge, middleware
  - `src/omnifocus_operator/server.py` — All 6 MCP tool handlers + middleware wiring
  - `src/omnifocus_operator/middleware.py` — ToolLoggingMiddleware (cross-cutting logging)
  - `src/omnifocus_operator/__main__.py` — Entry point + dual-handler logging setup
  - `tests/conftest.py` — Fixture chain: bridge → repo → service → server → client
  - `tests/test_server.py` — 55 server-level tests using Client(server) pattern
  - `tests/test_middleware.py` — 11 middleware + logging setup tests
- **Where to look first:** `server.py` (tool handlers), `middleware.py` (automatic logging), `conftest.py:client` fixture (test pattern)

---

## Stats

- **Timeline:** 2026-03-23 → 2026-03-26 (3 days, research + planning + execution)
- **Execution:** All 6 plans executed in ~24 minutes total compute time
- **Phases:** 3/3 complete
- **Plans:** 6/6 complete
- **Commits:** 98 (including docs, validation, archival)
- **Files changed:** 167 (+17,192 / -2,652)
- **Contributors:** Flo Kempenich
- **Tests:** 697 → 708 (+11 middleware tests)
- **Coverage:** ~98%
