# Phase 5: Service Layer and MCP Server - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A running MCP server with the `list_all` tool that returns the full structured database, wired with dependency injection so the bridge implementation is swappable at startup. Three-layer architecture: MCP Server -> Service Layer -> Repository. Requirements: ARCH-01, ARCH-02, TOOL-01, TOOL-02, TOOL-03, TOOL-04.

</domain>

<decisions>
## Implementation Decisions

### Service Layer Design
- Thin passthrough -- exists as an architectural seam for future phases (filtering, writes) but delegates directly to Repository in Phase 5
- Typed methods per operation: e.g., `get_all_data() -> DatabaseSnapshot`. Each future tool gets its own service method
- Named `OperatorService` -- the service is the core of the "Operator" product, not just OmniFocus data access. Distinct from `OmniFocusRepository` which is about data access
- Lives in a new `service/` package (`src/omnifocus_operator/service/`) consistent with bridge/, models/, repository/

### DI and Lifespan Wiring
- Bridge selected via environment variable `OMNIFOCUS_BRIDGE` (values: `inmemory`, `simulator`, `real`)
- Default bridge is `real` -- users should just start the server and have it work; inmemory/simulator are for development only
- Phase 5 shipping behavior: defaults to `real`, but since RealBridge doesn't exist yet, startup fails with a clear error message telling the user to set `OMNIFOCUS_BRIDGE=inmemory`. When RealBridge ships in Phase 8, the default "just works"
- Lifespan pre-warms the repository cache at startup via `repository.initialize()` -- first MCP call hits warm data, fail-fast if bridge is broken
- Server module lives in a new `server/` package (`src/omnifocus_operator/server/`) for FastMCP setup and lifespan wiring

### list_all Tool Output
- Returns the full `DatabaseSnapshot` Pydantic dump -- no truncation, no summary layer, no information loss
- Uses MCP structured output with `outputSchema` derived from DatabaseSnapshot's JSON Schema (TOOL-03)
- camelCase field names via Pydantic `by_alias=True` serialization -- matches MCP protocol conventions and standard JSON idiom
- Tool includes MCP annotations: `readOnlyHint: true`, `idempotentHint: true` (TOOL-02)

### Logging and stderr
- Default log level: INFO (startup, bridge selection, cache pre-warm, tool invocations)
- Configurable via `OMNIFOCUS_LOG_LEVEL` environment variable
- Redirect `sys.stdout` to `stderr` at startup as safety net against accidental print() corrupting MCP protocol traffic (TOOL-04)
- Log key events: startup, bridge type selected, cache pre-warm result, tool invocations

### Claude's Discretion
- Logging library choice -- stdlib logging vs structlog vs other. Researcher should evaluate what works best with the MCP SDK and the project's single-dependency philosophy
- Exact lifespan implementation pattern (FastMCP's context manager vs custom)
- Log message format and structure
- Error response format when tool invocation fails

</decisions>

<specifics>
## Specific Ideas

- `OperatorService` naming reflects that the service is the core of the "Operator" product, distinct from `OmniFocusRepository` which is about OmniFocus data access
- "Users shouldn't have to worry about inmemory or simulator when they start the MCP server. By default, you should just work with the real one." -- bridge selection is a dev concern, not a user concern
- Phase 5 startup with no RealBridge: fail honestly with a clear error rather than silently defaulting to InMemoryBridge

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusRepository`: has `get_snapshot() -> DatabaseSnapshot` and `initialize()` for pre-warming -- service layer wraps this directly
- `Bridge` protocol (`bridge/_protocol.py`): structural typing interface with `send_command(operation, params) -> response`
- `InMemoryBridge`: returns test data from memory -- available for Phase 5 dev/testing
- `DatabaseSnapshot`: Pydantic model with tasks, projects, tags, folders, perspectives -- source for structured output schema
- All models have camelCase aliases configured via `OmniFocusBaseModel` -- `by_alias=True` serialization is ready
- `models/__init__.py` handles forward reference resolution with `model_rebuild()` -- schema generation should work out of the box

### Established Patterns
- Package-per-concern: bridge/, models/, repository/ each have `__init__.py` with `__all__` re-exports
- Private modules with underscore prefix: `_protocol.py`, `_repository.py`, `_mtime.py`
- Protocol-based typing (structural subtyping, not inheritance)
- `TYPE_CHECKING` imports for ruff TC compliance
- `from __future__ import annotations` in all modules
- pytest-asyncio with `asyncio_mode = "auto"`, 10s timeout, coverage reporting

### Integration Points
- `__main__.py:main()` is the entry point -- currently raises NotImplementedError, needs to create and run the MCP server
- `pyproject.toml` script entry: `omnifocus-operator = "omnifocus_operator.__main__:main"`
- Runtime dependency `mcp>=1.26.0` provides `mcp.server.fastmcp.FastMCP`
- `MtimeSource` protocol in repository -- lifespan needs to provide a concrete implementation (or mock for InMemoryBridge)

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 05-service-layer-and-mcp-server*
*Context gathered: 2026-03-02*
