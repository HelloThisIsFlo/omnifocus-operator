# Phase 29: Dependency Swap & Imports - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Switch the server dependency from `mcp>=1.26.0` to `fastmcp>=3.1.1`. Migrate all `mcp.server.fastmcp` imports to `fastmcp`. Add progress reporting to batch write tools. Update docs to reflect the new dependency.

</domain>

<decisions>
## Implementation Decisions

### Import migration
- **D-01:** `from mcp.server.fastmcp import FastMCP, Context` → `from fastmcp import FastMCP, Context` (src/ only — test imports are Phase 30)
- **D-02:** `ToolAnnotations` — use the idiomatic FastMCP v3 import, not `from mcp.types`. Researcher should verify where `fastmcp` exports it (`from fastmcp import ToolAnnotations` or `from fastmcp.types import ...`)
- **D-03:** `ctx.request_context.lifespan_context` → `ctx.lifespan_context` shorthand wherever it appears
- **D-09:** Philosophy: implement as if built from scratch with `fastmcp>=3`. No `mcp.*` imports should remain in src/ if `fastmcp` provides an equivalent. This is not a minimal-impact migration — the code should look native to FastMCP v3.

### Dependency declaration
- **D-04:** `pyproject.toml` replaces `mcp>=1.26.0` with `fastmcp>=3.1.1` — `mcp` remains available as a transitive dependency

### Progress reporting
- **D-05:** Add `ctx.report_progress(progress=i, total=total)` to `add_tasks` and `edit_tasks` — even though batch limit is currently 1, add it now as scaffolding for when the limit lifts
- **D-06:** Report at the MCP handler level (in `server.py`), not inside the service pipeline — keeps the MCP concern out of the service layer

### Documentation
- **D-07:** Update README.md and landing page to reflect `fastmcp>=3.1.1` as the dependency (currently says `mcp>=1.26.0`)
- **D-08:** "Single runtime dependency" messaging stays accurate — just the name changes

### Claude's Discretion
- Exact placement of `report_progress` calls within the handler (before/after validation, etc.)
- Whether to add a `log_tool_call` for progress events or keep it minimal

</decisions>

<specifics>
## Specific Ideas

No specific requirements — the spike experiments provide reference implementations for every change.

</specifics>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spike findings (primary reference)
- `.research/deep-dives/fastmcp-spike/FINDINGS.md` — Go/no-go decision, import patterns, what changes vs what stays
- `.research/deep-dives/fastmcp-spike/experiments/01_import.py` — Import migration reference
- `.research/deep-dives/fastmcp-spike/experiments/06_progress.py` — Progress reporting reference implementation

### Current implementation
- `src/omnifocus_operator/server.py` — All tool handlers, import statements, `ToolAnnotations` usage, `ctx.request_context.lifespan_context` calls
- `src/omnifocus_operator/__main__.py` — Server entry point

### Requirements
- `.planning/REQUIREMENTS.md` — DEP-01..04, PROG-01..02, DOC-01..02

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Spike experiment files serve as copy-paste reference implementations

### Established Patterns
- Method Object pattern (`_AddTasksPipeline`, `_EditTasksPipeline`) — progress reporting should NOT penetrate into these; stay at handler level
- `log_tool_call()` utility in `server.py` — can optionally log progress events too

### Integration Points
- `server.py` lines 14-17: import block to migrate
- `server.py` lines 209, 277: `ctx.request_context.lifespan_context` → `ctx.lifespan_context`
- `pyproject.toml` dependencies section

</code_context>

<deferred>
## Deferred Ideas

- Lifting the batch limit on `add_tasks`/`edit_tasks` — separate concern, different milestone
- Test client migration from `mcp.client.session` — Phase 30
- `ctx.info()` / `ctx.warning()` protocol-level logging — Phase 31

</deferred>

---

*Phase: 29-dependency-swap-imports*
*Context gathered: 2026-03-26*
