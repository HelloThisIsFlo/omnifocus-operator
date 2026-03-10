---
created: 2026-03-10T14:40:56.871Z
title: Migrate to FastMCP v3 standalone package
area: server
files:
  - src/omnifocus_operator/__main__.py
  - src/omnifocus_operator/server.py
---

## Problem

The project currently uses `mcp.server.fastmcp` (built into the official `mcp` SDK). This has several limitations discovered during development:

1. **Logging is broken**: `stdio_server()` hijacks stderr, making `logging.getLogger()` useless during tool execution. The proper fix is `ctx.info()` / `ctx.warning()` protocol-level logging, which works in both packages but the standalone FastMCP has better docs and patterns for this.
2. **Feature gap**: The standalone `fastmcp` package (gofastmcp.com) has evolved beyond the SDK's built-in copy — more features, better ergonomics, richer middleware/lifecycle support.
3. **Documentation**: gofastmcp.com is comprehensive and well-maintained; the built-in `mcp.server.fastmcp` has minimal docs.

Target: **FastMCP v3** (standalone `fastmcp` package from PyPI).

## Solution

- Replace `from mcp.server.fastmcp import Context, FastMCP` with `from fastmcp import FastMCP, Context`
- Add `fastmcp>=3` to dependencies (replaces implicit use via `mcp` SDK)
- Migrate logging from file-based `logging.FileHandler` workaround to `ctx.info()` / `ctx.warning()` protocol-level logging
- Review FastMCP v3 migration guide for any API changes (lifespan, tool registration, settings)
- Update tests that import from `mcp.server.fastmcp`
- Current file-based logging (`~/Library/Logs/omnifocus-operator.log`) is a temporary workaround until this migration
- Update "single runtime dependency" messaging in README.md and landing page (docs site) — currently advertises `mcp>=1.26.0` as the only dep; after migration the dep becomes `fastmcp>=3`
