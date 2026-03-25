# Technology Stack

**Project:** OmniFocus Operator v1.2.2 -- FastMCP v3 Migration
**Researched:** 2026-03-25

## Recommended Stack

### Core Dependency Change

| Technology | Version | Purpose | Why |
|------------|---------|---------|-----|
| `fastmcp` | >=3 (tested: 3.1.1) | MCP server framework + test client | Replaces `mcp.server.fastmcp` with standalone package. Gains: Client test helper, Middleware system, progress reporting, lifespan shortcut |
| `mcp` | (transitive) | Protocol types (`ToolAnnotations`, `CallToolResult`) | Still needed -- fastmcp depends on it. `ToolAnnotations` is NOT re-exported by fastmcp |

### What Stays Unchanged

| Technology | Version | Purpose | Notes |
|------------|---------|---------|-------|
| Python | 3.12+ | Runtime | No change |
| Pydantic | v2 | Models, validation | No change |
| sqlite3 | stdlib | Read cache | No change |
| uv | latest | Package manager | No change |

### New Import Paths

| Before | After | Notes |
|--------|-------|-------|
| `from mcp.server.fastmcp import FastMCP, Context` | `from fastmcp import FastMCP, Context` | Core framework |
| `from mcp.types import ToolAnnotations` | `from mcp.types import ToolAnnotations` | **Unchanged** -- not re-exported |
| (new) | `from fastmcp import Client` | Test client |
| (new) | `from fastmcp.server.middleware import Middleware, MiddlewareContext` | Middleware base |

### Dev Dependencies

| Library | Version | Purpose | Change |
|---------|---------|---------|--------|
| pytest | >=9.0.2 | Test framework | No change |
| pytest-asyncio | >=1.3.0 | Async test support | No change |
| anyio | (was implicit) | Memory streams for test plumbing | **REMOVED** -- no longer needed, Client handles transport |

## Alternatives Considered

| Category | Recommended | Alternative | Why Not |
|----------|-------------|-------------|---------|
| Test client | `Client(server)` from fastmcp | Keep `_ClientSessionProxy` | 70 lines of plumbing vs 3 lines. No contest. |
| Middleware | FastMCP `Middleware` class | Keep manual `log_tool_call()` | 6 call sites + function vs automatic. Middleware is the pattern. |
| Logging | `StreamHandler(stderr)` + `FileHandler` | `ctx.info()` / `ctx.warning()` | Dead end -- no major client renders protocol log messages |
| DI pattern | Keep lifespan (`ctx.lifespan_context`) | `Depends()` decorator | Lifespan = per-app singleton. `Depends()` = per-request. Our service is a singleton. |
| Test method | `call_tool_mcp()` | `call_tool()` (raising) | Preserves existing assertion shapes. Raising variant doubles the diff. |

## Installation

```bash
# Production dependency change
# pyproject.toml:
# - "mcp>=1.26.0"
# + "fastmcp>=3"

uv sync
```

```bash
# Remove spike dependency group (no longer needed)
# pyproject.toml: delete [dependency-groups] spike section
```

## Dependency Impact

- **Before:** 1 runtime dependency (`mcp>=1.26.0`)
- **After:** 1 runtime dependency (`fastmcp>=3`)
- **Transitive:** fastmcp brings `mcp`, `httpx`, `pydantic`, `rich`, `uvicorn`, `websockets`, and others. Heavier transitive tree, but only `fastmcp` is the direct dependency.
- **Messaging:** "Single runtime dependency" badge/claim remains accurate. Just a different single dependency.
- **Note:** fastmcp's transitive dependencies include things like `uvicorn` and `websockets` that aren't needed for stdio transport. This is fastmcp's packaging choice, not ours. No action needed.

## Sources

- Import verification: tested live against fastmcp 3.1.1 (installed in spike group)
- `ToolAnnotations` not re-exported: confirmed via `from fastmcp import ToolAnnotations` -> ImportError
- `Client`, `Middleware`, `MiddlewareContext` import paths: confirmed via live import test
- Spike findings: `.research/deep-dives/fastmcp-spike/FINDINGS.md`
