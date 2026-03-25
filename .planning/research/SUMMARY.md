# Research Summary: FastMCP v3 Migration (v1.2.2)

**Domain:** Infrastructure migration -- MCP SDK swap with DX improvements
**Researched:** 2026-03-25
**Overall confidence:** HIGH -- spike experiments verified all features, imports confirmed live against fastmcp 3.1.1

## Executive Summary

The migration from `mcp.server.fastmcp` to standalone `fastmcp>=3` is a clean infrastructure upgrade that touches only the MCP layer. The three-layer architecture (MCP -> Service -> Repository) holds perfectly -- no changes penetrate below the server boundary. The migration is justified by two concrete DX wins: test client simplification (~70 lines of plumbing deleted, replaced by 3-line `Client(server)` pattern) and automatic middleware (removes manual `log_tool_call()` from 6 tool handlers).

The spike proved that logging improvements (stderr + file dual handlers) are SDK-independent -- they work identically on the old `mcp` SDK. The original migration driver ("stderr is hijacked") was a misdiagnosis. However, logging rework is still in scope because the current setup is based on that misdiagnosis and needs correction regardless.

Changes are confined to 7 files (1 new, 6 modified). No files are deleted. The service, contracts, repository, models, and bridge packages are completely unchanged. Test assertion migration is minimized by using `call_tool_mcp()` (returns raw `CallToolResult` matching current assertion shapes) instead of the new raising `call_tool()` variant.

## Key Findings

**Stack:** Swap `mcp>=1.26.0` to `fastmcp>=3`. `ToolAnnotations` stays at `mcp.types` (not re-exported by fastmcp).
**Architecture:** Changes confined to MCP layer. One new file (`middleware.py`). Service/repo/models untouched.
**Critical pitfall:** `Client.call_tool()` raises `ToolError` by default. Use `call_tool_mcp()` in tests to preserve existing assertion shapes.

## Implications for Roadmap

Based on research, suggested phase structure:

1. **Dependency Swap + Imports** - Foundation. Must land first before any v3 feature.
   - Addresses: pyproject.toml swap, all import changes, lifespan_context shortcut
   - Avoids: mixing import changes with behavioral changes

2. **Test Client Migration** - Biggest diff but safest (no server behavior change).
   - Addresses: ~160 lines of test plumbing deleted, Client fixture created
   - Avoids: debugging middleware issues with broken test infrastructure

3. **Middleware** - Server behavior change (logging moves from manual to automatic).
   - Addresses: log_tool_call() deletion, ToolLoggingMiddleware creation
   - Avoids: premature logging wiring (loggers set up in phase 4)

4. **Logging Rework** - Entrypoint change. Wires dual handlers + middleware destinations.
   - Addresses: stderr + file handlers, misdiagnosis comment removal
   - Avoids: nothing -- independent concern, logically last in the server stack

5. **Progress Reporting** - Additive. No deletions, no refactors.
   - Addresses: ctx.report_progress() in batch operations
   - Avoids: premature progress before core migration stable

6. **Documentation** - Final sweep.
   - Addresses: README, landing page dependency references

**Phase ordering rationale:**
- Phase 1 is the dependency foundation -- everything else imports from fastmcp
- Phase 2 before 3: tests must work before changing server behavior
- Phase 3 before 4: middleware creates the logging infrastructure that phase 4 wires
- Phase 5 is independent (just needs phase 1) but best deferred until core is stable
- Phase 6 is always last

**Research flags for phases:**
- Phase 2: Needs careful attention to `call_tool_mcp` vs `call_tool` choice. Recommendation is `call_tool_mcp` throughout.
- Phase 3: Reference implementation exists in spike experiments -- straightforward adaptation.
- Phase 4: Independent of FastMCP migration -- no research needed.
- Phase 5: Trivial addition. No research needed.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Imports verified live against fastmcp 3.1.1 |
| Architecture | HIGH | Spike covered all integration points, boundary analysis confirms isolation |
| Test migration | HIGH | `call_tool_mcp()` return type confirmed via source inspection |
| Middleware | HIGH | Reference implementation tested in spike experiment 05 |
| Logging | HIGH | SDK-independent, verified in spike experiments 02/03 |
| Progress | HIGH | Working demo in spike experiment 06 |

## Gaps to Address

- `_build_patched_server()` in test_server.py may still be needed for tests that use custom lifespan (degraded mode tests). Evaluate during phase 2 whether it can be replaced or must be adapted.
- Tests in `test_simulator_bridge.py` and `test_simulator_integration.py` have their own `_run_with_client` copies -- confirm these can use the shared `client` fixture or need inline `Client(server)` usage due to custom server setup.
