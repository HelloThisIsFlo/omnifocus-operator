---
phase: 05-service-layer-and-mcp-server
verified: 2026-03-02T12:50:00Z
status: passed
score: 12/12 must-haves verified
re_verification: false
---

# Phase 5: Service Layer and MCP Server — Verification Report

**Phase Goal:** Service layer and MCP server — OperatorService thin passthrough, FastMCP server with lifespan DI, list_all tool, stderr logging, entry point
**Verified:** 2026-03-02T12:50:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | OperatorService.get_all_data() delegates to repository.get_snapshot() and returns a DatabaseSnapshot | VERIFIED | `_service.py` line 37: `return await self._repository.get_snapshot()`. Test `test_get_all_data_delegates_to_repository` confirms `bridge.call_count == 1` after one call. |
| 2 | ConstantMtimeSource always returns 0 (no cache invalidation) for InMemoryBridge usage | VERIFIED | `_mtime.py` line 54: `return 0`. Tests `test_always_returns_zero` and `test_satisfies_mtime_protocol` both pass. |
| 3 | Bridge factory creates InMemoryBridge for 'inmemory', raises NotImplementedError for 'simulator' and 'real' with clear messages | VERIFIED | `_factory.py` match/case: "inmemory" returns `InMemoryBridge`, "simulator" raises with "Phase 7", "real" raises with "Phase 8" and "OMNIFOCUS_BRIDGE=inmemory". Four factory tests pass. |
| 4 | Bridge factory raises ValueError for unknown bridge types | VERIFIED | `_factory.py` default case: `raise ValueError(f"Unknown bridge type: {bridge_type!r}. Use: inmemory, simulator, real")`. `test_unknown_raises_value_error` passes. |
| 5 | list_all tool returns the full DatabaseSnapshot as structured Pydantic data via MCP protocol | VERIFIED | `_server.py` line 89: `return await service.get_all_data()`. In-process test confirms `structuredContent` has all 5 keys: tasks, projects, tags, folders, perspectives. |
| 6 | list_all tool has readOnlyHint=true and idempotentHint=true annotations | VERIFIED | `_server.py` line 78: `ToolAnnotations(readOnlyHint=True, idempotentHint=True)`. Tests `test_list_all_has_read_only_hint` and `test_list_all_has_idempotent_hint` pass via live MCP protocol call. |
| 7 | list_all tool exposes outputSchema derived from DatabaseSnapshot JSON schema with camelCase field names | VERIFIED | `DatabaseSnapshot` imported at runtime (not TYPE_CHECKING, with noqa: TC001) so FastMCP's `get_type_hints()` resolves the return annotation. Test `test_output_schema_uses_camelcase` confirms `dueDate` and `effectiveFlagged` in `$defs.Task.properties`. |
| 8 | Server logs to stderr only — stdout is reserved for MCP protocol traffic | VERIFIED | `__main__.py` line 16: `sys.stdout = sys.stderr`. `logging.basicConfig(stream=sys.stderr)`. Tests `test_stdout_redirected_to_stderr` and `test_logging_goes_to_stderr` pass. |
| 9 | Three-layer architecture is wired: MCP tool -> OperatorService -> OmniFocusRepository | VERIFIED | `_server.py` lifespan wires: `create_bridge` -> `OmniFocusRepository` -> `OperatorService` -> `yield {"service": service}`. Tool body retrieves service from `lifespan_context["service"]`. End-to-end test `test_list_all_returns_data_through_all_layers` passes. |
| 10 | Bridge is selected via OMNIFOCUS_BRIDGE env var, defaulting to 'real' | VERIFIED | `_server.py` line 45: `os.environ.get("OMNIFOCUS_BRIDGE", "real")`. Tests use `monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")`. |
| 11 | Running with default 'real' bridge fails with clear error since RealBridge doesn't exist yet | VERIFIED | `create_bridge("real")` raises `NotImplementedError("RealBridge not yet implemented (Phase 8)...")`. Test `test_default_real_bridge_fails_at_startup` confirms ExceptionGroup contains NotImplementedError. |
| 12 | Running with OMNIFOCUS_BRIDGE=inmemory works end-to-end | VERIFIED | `test_inmemory_bridge_via_env_var` sets env var and confirms `structuredContent` is not None through full MCP protocol path. |

**Score:** 12/12 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/service/__init__.py` | Public re-exports for service package; exports OperatorService | VERIFIED | Exports `OperatorService` from `_service`; `__all__ = ["OperatorService"]` |
| `src/omnifocus_operator/service/_service.py` | OperatorService thin passthrough to repository | VERIFIED | `class OperatorService` with `__init__(self, repository)` storing `self._repository`; `async def get_all_data()` returns `await self._repository.get_snapshot()` |
| `src/omnifocus_operator/repository/_mtime.py` | ConstantMtimeSource added alongside MtimeSource and FileMtimeSource | VERIFIED | All three classes present; `@runtime_checkable` added to `MtimeSource` protocol |
| `src/omnifocus_operator/bridge/_factory.py` | create_bridge factory function with match/case routing | VERIFIED | match/case for all four cases; empty-collection dict for inmemory |
| `src/omnifocus_operator/server/__init__.py` | Public re-exports for server package; exports create_server | VERIFIED | Exports `create_server` from `_server`; `__all__ = ["create_server"]` |
| `src/omnifocus_operator/server/_server.py` | FastMCP server setup, lifespan, tool registration | VERIFIED | `app_lifespan`, `_register_tools`, `create_server` all present and substantive |
| `src/omnifocus_operator/__main__.py` | Entry point: stdout redirect, logging config, server.run() | VERIFIED | `sys.stdout = sys.stderr`, `logging.basicConfig(stream=sys.stderr)`, `server.run(transport="stdio")` |
| `tests/test_service.py` | Unit tests for OperatorService, ConstantMtimeSource, bridge factory | VERIFIED | 10 tests covering all three units; all pass |
| `tests/test_server.py` | In-process MCP integration tests for ARCH-01/02, TOOL-01/02/03/04 | VERIFIED | 11 tests across 6 test classes; all pass using anyio memory streams |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `server/_server.py` | `service/_service.py` | lifespan creates OperatorService; tools access via `ctx.request_context.lifespan_context["service"]` | WIRED | Line 59: `service = OperatorService(repository=repository)`. Line 88: `ctx.request_context.lifespan_context["service"]` |
| `server/_server.py` | `bridge/_factory.py` | lifespan calls `create_bridge(bridge_type)` | WIRED | Line 41: `from omnifocus_operator.bridge import create_bridge`. Line 48: `bridge = create_bridge(bridge_type)` |
| `__main__.py` | `server/_server.py` | imports `create_server` and calls `server.run(transport='stdio')` | WIRED | Line 28: `from omnifocus_operator.server import create_server`. Lines 30-31: `server = create_server(); server.run(transport="stdio")` |
| `service/_service.py` | `repository/_repository.py` | constructor injection of OmniFocusRepository; `self._repository` | WIRED | Line 27: `def __init__(self, repository: OmniFocusRepository)`. Line 37: `return await self._repository.get_snapshot()` |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| ARCH-01 | 05-01, 05-02 | Server uses three-layer architecture (MCP Server -> Service Layer -> Repository) | SATISFIED | `_server.py` wires tool -> `OperatorService` -> `OmniFocusRepository`. End-to-end test `TestARCH01ThreeLayerArchitecture` passes. |
| ARCH-02 | 05-01, 05-02 | Bridge implementation injected at startup — no code changes to switch bridges | SATISFIED | `OMNIFOCUS_BRIDGE` env var selects bridge type in lifespan; `create_bridge()` factory isolates bridge-creation concern. `TestARCH02BridgeInjection` passes. |
| TOOL-01 | 05-02 | `list_all` tool returns full structured database as typed Pydantic data | SATISFIED | `list_all` returns `DatabaseSnapshot` (Pydantic model). `structuredContent` contains all 5 entity collections. `TestTOOL01ListAllStructuredOutput` passes. |
| TOOL-02 | 05-02 | Tool includes MCP annotations (`readOnlyHint`, `idempotentHint`) | SATISFIED | `ToolAnnotations(readOnlyHint=True, idempotentHint=True)` passed to `@mcp.tool()`. `TestTOOL02Annotations` verifies via live MCP tool listing. |
| TOOL-03 | 05-02 | Tool exposes structured output schema from Pydantic models | SATISFIED | `DatabaseSnapshot` is a runtime import so FastMCP auto-generates `outputSchema` via `get_type_hints()`. Schema has camelCase `$defs.Task.properties`. `TestTOOL03OutputSchema` passes. |
| TOOL-04 | 05-02 | Server logs to stderr only | SATISFIED | `sys.stdout = sys.stderr` in `main()`; `logging.basicConfig(stream=sys.stderr)`. `TestTOOL04StderrOnly` verifies both redirect and logger. |

No orphaned requirements: REQUIREMENTS.md maps exactly ARCH-01, ARCH-02, TOOL-01, TOOL-02, TOOL-03, TOOL-04 to Phase 5. All six are satisfied.

---

### Anti-Patterns Found

No blockers or warnings. Scan of phase files:

- No `TODO`, `FIXME`, `XXX`, `HACK`, or `PLACEHOLDER` comments in any phase-created file
- No `return null`, `return {}`, `return []` stubs
- No empty `console.log`-only handlers
- One intentional `# noqa: TC001` comment in `_server.py` line 24 — this is correct and necessary (documented reason: FastMCP needs `DatabaseSnapshot` in the module namespace for `get_type_hints()` at tool registration time)
- `__main__.py` has `# type: ignore[assignment]` on the `sys.stdout = sys.stderr` line — correct and expected

---

### Human Verification Required

None. All behaviors are automated-testable via in-process MCP client/server communication. The complete end-to-end path (MCP protocol -> FastMCP -> lifespan DI -> OperatorService -> OmniFocusRepository -> InMemoryBridge) is exercised programmatically by `tests/test_server.py`.

---

## Verification Summary

Phase 5 goal is fully achieved. All 12 observable truths are verified against the actual codebase. Key findings:

**Plan 01 (Service Layer Foundations):** `OperatorService` is a genuine thin passthrough — 1-line implementation delegates directly to `self._repository.get_snapshot()`. `ConstantMtimeSource` correctly returns 0. Bridge factory uses match/case with all four cases handled, including `OMNIFOCUS_BRIDGE=inmemory` hint in the "real" error message. `MtimeSource` was correctly upgraded to `@runtime_checkable` to support isinstance checks.

**Plan 02 (MCP Server):** The three-layer wiring is complete and tested end-to-end via anyio memory streams. The key design decision to keep `DatabaseSnapshot` as a runtime import (with `noqa: TC001`) is correct — without it FastMCP's `get_type_hints()` cannot resolve the return annotation and `outputSchema` would not be generated. The `_register_tools()` separation enables the patched-lifespan testing pattern used in `test_list_all_structured_content_is_camelcase`. All 6 phase requirements (ARCH-01, ARCH-02, TOOL-01 through TOOL-04) are satisfied and covered by passing tests.

**Test results:** 106 total tests passing, 95.82% coverage, ruff clean, mypy clean.

---

_Verified: 2026-03-02T12:50:00Z_
_Verifier: Claude (gsd-verifier)_
