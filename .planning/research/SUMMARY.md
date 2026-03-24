# Project Research Summary

**Project:** OmniFocus Operator v1.2.2 — FastMCP v3 Migration
**Domain:** MCP server dependency migration (bundled SDK -> standalone framework)
**Researched:** 2026-03-24
**Confidence:** HIGH

## Executive Summary

This milestone is a focused dependency swap, not a feature build. The migration replaces the bundled FastMCP 1.0 (shipped inside `mcp>=1.26.0`) with standalone `fastmcp>=3.1,<4` — the actively maintained project now backed by Prefect. The three-layer architecture (MCP Server / Service / Repository) is completely unaffected. All changes are contained in 3 production files (`pyproject.toml`, `server.py`, `__main__.py`) and 4 test files. The primary win beyond maintenance alignment is protocol-level logging: `await ctx.info()` / `await ctx.warning()` send messages directly to the MCP client (Claude Desktop), replacing the current file-based `~/Library/Logs/` workaround that agents can never see.

The recommended execution order is strict: dependency swap first, then import + Context type changes, then lifespan context accessor updates, then full test suite validation, then logging enhancement, then manual UAT. This sequence isolates each failure mode. The biggest risk is conflating these steps — particularly mixing test infrastructure changes (which involve a different return-type contract from `fastmcp.Client` vs `ClientSession`) into the same commit as the import swap.

The transitive dependency footprint grows (from ~12 to ~30+ packages), and the README "Dependencies 1" badge becomes misleading. This is a real tradeoff with no mitigation — fastmcp is the community standard (70% of MCP servers), and the gains justify accepting it. The badge should be updated or removed.

## Key Findings

### Recommended Stack

Single dependency swap: `mcp>=1.26.0` -> `fastmcp>=3.1,<4`. The `mcp` package remains available as a transitive dependency, so `mcp.types.ToolAnnotations`, `mcp.client.session.ClientSession`, and `mcp.shared.message.SessionMessage` all continue to work with no import changes. Floor at `>=3.1` (not `>=3.0`) because v3.0.0 had known bugs: middleware state surviving to tool handlers, decorator overload types. Cap at `<4` for semver safety.

**Core technologies:**
- `fastmcp>=3.1,<4`: MCP server framework — standalone project, actively maintained by Prefect, 1M+ downloads/day, protocol-level logging
- `mcp>=1.24.0` (transitive via fastmcp): types and low-level SDK — `ToolAnnotations`, `ClientSession`, `SessionMessage` remain importable with no changes

### Expected Features

**Must have (table stakes for this milestone):**
- Dep swap in `pyproject.toml` — the foundation; nothing else moves without this
- Import changes: `from fastmcp import FastMCP, Context` in `server.py` and 4 test files
- Context type simplification: `Context[Any, Any, Any]` -> `Context` (non-generic in v3)
- Lifespan context accessor: `ctx.request_context.lifespan_context["service"]` -> `ctx.lifespan_context["service"]` across all 6 tool handlers
- Protocol-level logging: `await ctx.info()` / `await ctx.warning()` in tool handlers (agent-visible)
- All 6 existing tools behaviorally identical — 697 tests must pass

**Should have (differentiators unlocked by migration, adopt in this milestone):**
- `ctx.lifespan_context` direct property shorthand (cleaner, two-path fallback)
- Dual logging strategy: FileHandler for lifecycle events + `ctx` methods for agent-visible messages
- ToolAnnotations as dict (`{"readOnlyHint": True}`) — reduces coupling to `mcp.types`

**Defer (future milestones):**
- Middleware framework (v1.6 production hardening)
- Dependency injection via `Depends()` (when DI simplifies code)
- `fastmcp.Client` test infrastructure refactor (DX improvement, separate milestone)
- Tool timeouts `@mcp.tool(timeout=30.0)` (v1.6)
- HTTP/SSE transport (out of scope, stdio-only design)

### Architecture Approach

The migration is architecturally clean — service, repository, bridge, contracts, models, and agent_messages layers have zero MCP imports and require no changes. All modifications are at the server boundary layer only. The pattern to follow is minimal import migration: change only `FastMCP` and `Context` imports, leave all `mcp.types` and `mcp.client.*` imports alone (they resolve through fastmcp's transitive `mcp` dependency). Adopt dual logging as a structural pattern: file-based `logging` for server infrastructure, `await ctx.info()/warning()` for agent-visible tool execution messages.

**Major components and their migration scope:**
1. `pyproject.toml` — dep swap only
2. `server.py` — imports, Context type, lifespan accessor, logging (most changes)
3. `__main__.py` — FileHandler kept for lifecycle; file-only tool logging removed or reduced
4. `tests/conftest.py` + 3 test files — FastMCP import only; test harness pattern deferred

### Critical Pitfalls

1. **`ctx.request_context.lifespan_context` accessor is fragile** — v3 adds a direct `ctx.lifespan_context` property with a two-path fallback to `server._lifespan_result`. Old path works in stdio but not guaranteed in all contexts. Replace all 6 occurrences atomically; grep for `request_context.lifespan_context` across the entire codebase.

2. **`Context[Any, Any, Any]` breaks mypy in v3** — Context is a non-generic dataclass in v3; subscripting it produces `[type-arg]` errors under strict mypy. Change all 6 tool handler signatures to plain `Context`. Remove unused `Any` imports if they were only needed for Context type params.

3. **Test infrastructure uses private `_mcp_server` attribute** — The `_ClientSessionProxy` + anyio streams + `_mcp_server.run()` pattern relies on a private API. v3 provides `fastmcp.Client(server)` as the official testing API, but with a different return type (`CallToolResult.data` vs `ClientSession.call_tool()`). Keep this change separate from the import swap. Current pattern still works in v3.1.1 but is a time bomb.

4. **Keeping both `mcp` and `fastmcp` in deps causes conflicts** — Replace (not add). Verify with `python -c "from fastmcp import FastMCP; from mcp.types import ToolAnnotations"` after sync.

5. **`ctx.info()` / `ctx.warning()` are async and only work inside tool handlers** — Missing `await` produces a silent coroutine warning, not an error. Lifespan startup/shutdown has no `ctx`. Do not remove FileHandler; add `ctx` calls alongside it, not instead.

## Implications for Roadmap

This is a single focused milestone. Within it, research reveals a mandatory execution sequence with three natural commit groupings:

### Phase 1: Core Dependency + Import Swap
**Rationale:** All subsequent changes depend on fastmcp being installed and importable. Must be the first commit and validated before anything else.
**Delivers:** fastmcp installed, all imports resolving, 697 tests passing
**Addresses:** Table stakes features (dep swap, import changes, Context type, lifespan accessor)
**Avoids:** Dependency conflict pitfall, mypy breakage pitfall

### Phase 2: Protocol-Level Logging Enhancement
**Rationale:** Requires Phase 1 complete. Independent of test infrastructure changes — keeps blast radius small.
**Delivers:** Agent-visible logging via `await ctx.info()` / `await ctx.warning()` in all 6 tool handlers
**Addresses:** The primary user-facing win of the milestone
**Avoids:** Logging async pitfall — always `await`, keep FileHandler for lifecycle events

### Phase 3: Manual UAT + Documentation
**Rationale:** Must follow code changes. Protocol-level logging is only verifiable via live Claude Desktop session. README dep badge is the final documentation touch.
**Delivers:** Confirmed live behavior, updated README badge
**Note:** Test infrastructure refactor (`fastmcp.Client`) deferred to future milestone

### Phase Ordering Rationale

- Phase 1 before everything: fastmcp cannot be imported until installed; import changes cannot be validated without the dep
- Phase 2 separate from Phase 1: mixing logging changes with import changes inflates diff and makes regression isolation harder
- Test harness refactor deferred: `fastmcp.Client` return type differs from `ClientSession`; mixing this into migration scope creates a second independent failure surface
- UAT last: manual testing only meaningful after all code changes are stable

### Research Flags

Phases with well-documented patterns (skip research-phase during planning):
- **Phase 1 (import swap):** Fully specified. Official docs, upgrade guide, and source code analysis give exact import paths and file list.
- **Phase 2 (logging):** Fully specified. `ctx.info/warning/debug/error` signatures are documented; dual-channel strategy is clear.
- **Phase 3 (UAT + docs):** Standard process.

Phases that may need deeper investigation:
- **Test infrastructure refactor (deferred):** When tackled in a future milestone, the `fastmcp.Client` return type difference and `_mcp_server` removal will need careful study of the new fixture contract.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Official docs, PyPI, GitHub source cross-verified. Dep versions confirmed from fastmcp pyproject.toml directly |
| Features | HIGH | Feature scope is narrow and mechanically specified. Import paths verified against v3.1.1 source |
| Architecture | HIGH | File-level change map verified against codebase analysis (317-line server.py, 6 handlers, 6 `ctx.request_context` usages counted) |
| Pitfalls | HIGH | Context source code read directly; GitHub issues cited for lifespan scope; upgrade guide is official |

**Overall confidence:** HIGH

### Gaps to Address

- **Test harness (`fastmcp.Client` migration):** Deliberately deferred. When tackled, need to verify how `CallToolResult.data` differs from existing `ClientSession.call_tool()` return and whether `_ClientSessionProxy` can be replaced cleanly.
- **`uv tree` audit post-migration:** Actual transitive dep list should be verified after `uv sync`. Research estimates ~30+ but exact set depends on fastmcp extras installed.
- **README badge decision:** "Dependencies 1" remains technically true (one direct dep) but misleading. Human judgment call on whether to update or remove.
- **Agent log visibility validation:** Need UAT to confirm `ctx.info()` messages actually appear in Claude Desktop's UI — not just technically sent but visually surfaced.

## Sources

### Primary (HIGH confidence)
- [FastMCP Official Docs](https://gofastmcp.com) — server, tools, context, lifespan, logging, testing
- [FastMCP Context API reference](https://gofastmcp.com/python-sdk/fastmcp-server-context) — `lifespan_context` property, method signatures
- [FastMCP Context source code](https://github.com/jlowin/fastmcp/blob/main/src/fastmcp/server/context.py) — `lifespan_context` two-path implementation
- [FastMCP PyPI](https://pypi.org/project/fastmcp/) — v3.1.1 latest, dependency list
- [FastMCP GitHub (pyproject.toml)](https://github.com/PrefectHQ/fastmcp) — `mcp>=1.24.0,<2.0` transitive dep confirmed
- [FastMCP Changelog](https://gofastmcp.com/changelog) — version history, 3.0.1 bug fixes documented
- [FastMCP Upgrade Guide](https://gofastmcp.com/getting-started/upgrading/from-mcp-sdk) — official import migration path
- [FastMCP Testing docs](https://gofastmcp.com/development/tests) — `Client(server)` in-memory pattern

### Secondary (MEDIUM confidence)
- [FastMCP 3.0 GA Announcement](https://www.jlowin.dev/blog/fastmcp-3-launch) — breaking changes overview, author blog
- [FastMCP 3.0 what's new](https://www.jlowin.dev/blog/fastmcp-3-whats-new) — new features, differentiators

### Tertiary (confirmed via GitHub issues)
- [Lifespan per-session issue #1115](https://github.com/jlowin/fastmcp/issues/1115) — lifespan scope confirmed by maintainer
- [mcp.types namespace issue #2166](https://github.com/PrefectHQ/fastmcp/issues/2166) — namespace shadowing edge case
- Codebase analysis: server.py (317 lines, 6 handlers), conftest.py (4 `_mcp_server` usages), 3 test files

---
*Research completed: 2026-03-24*
*Ready for roadmap: yes*
